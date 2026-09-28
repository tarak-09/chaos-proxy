import asyncio
import logging
import random
import time
from typing import Optional

from .faults import FaultConfig

logger = logging.getLogger(__name__)

class ConnectionDropper(Exception):
    pass

class ProxyServer:
    def __init__(self, local_host: str, local_port: int, remote_host: str, remote_port: int, fault_config: FaultConfig):
        self.local_host = local_host
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.fault_config = fault_config
        self.server: Optional[asyncio.AbstractServer] = None

    async def start(self):
        self.server = await asyncio.start_server(
            self.handle_client, self.local_host, self.local_port
        )
        addrs = ', '.join(str(sockets.getsockname()) for sockets in self.server.sockets)
        logger.info(f"Proxying {addrs} -> {self.remote_host}:{self.remote_port}")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Server stopped.")

    async def serve_forever(self):
        if not self.server:
            raise RuntimeError("Server not started")
        async with self.server:
            await self.server.serve_forever()

    async def handle_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        peer = client_writer.get_extra_info('peername')
        logger.info(f"New connection from {peer}")
        try:
            remote_reader, remote_writer = await asyncio.open_connection(
                self.remote_host, self.remote_port
            )
        except Exception as e:
            logger.error(f"Failed to connect to remote {self.remote_host}:{self.remote_port}: {e}")
            client_writer.close()
            return

        async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, direction: str):
            queue = asyncio.Queue()
            
            # State for throttling
            start_time = time.monotonic()
            bytes_transferred = 0

            async def read_loop():
                try:
                    while not reader.at_eof():
                        data = await reader.read(8192)
                        if not data:
                            break
                        await queue.put((time.monotonic(), data))
                except Exception as e:
                    logger.debug(f"{direction} read loop error: {e}")
                finally:
                    await queue.put(None)

            async def write_loop():
                nonlocal bytes_transferred
                try:
                    while True:
                        item = await queue.get()
                        if item is None:
                            break
                        
                        arrival_time, data = item
                        
                        # Apply connection drop
                        if self.fault_config.drop_probability > 0:
                            if random.random() < self.fault_config.drop_probability:
                                logger.info(f"Simulating connection drop for {peer}")
                                raise ConnectionDropper("Dropped")

                        # Apply latency
                        latency = self.fault_config.latency_ms
                        if self.fault_config.latency_jitter_ms > 0:
                            latency += random.uniform(-self.fault_config.latency_jitter_ms, self.fault_config.latency_jitter_ms)
                        
                        if latency > 0:
                            latency_sec = max(0, latency) / 1000.0
                            target_time = arrival_time + latency_sec
                            now = time.monotonic()
                            if target_time > now:
                                await asyncio.sleep(target_time - now)

                        # Apply bandwidth throttling
                        if self.fault_config.throttle_bytes_per_sec > 0:
                            bytes_transferred += len(data)
                            expected_time = bytes_transferred / self.fault_config.throttle_bytes_per_sec
                            elapsed = time.monotonic() - start_time
                            if expected_time > elapsed:
                                await asyncio.sleep(expected_time - elapsed)

                        writer.write(data)
                        await writer.drain()
                except ConnectionDropper:
                    pass
                except Exception as e:
                    logger.debug(f"{direction} write loop error: {e}")
                finally:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass

            read_task = asyncio.create_task(read_loop())
            write_task = asyncio.create_task(write_loop())
            await asyncio.gather(read_task, write_task)

        client_to_remote = asyncio.create_task(pipe(client_reader, remote_writer, "client->remote"))
        remote_to_client = asyncio.create_task(pipe(remote_reader, client_writer, "remote->client"))
        
        await asyncio.gather(client_to_remote, remote_to_client)
        logger.info(f"Connection closed from {peer}")

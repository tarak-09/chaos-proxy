import asyncio
import time
import pytest
from faultproxy.faults import FaultConfig
from faultproxy.proxy import ProxyServer

async def echo_handler(reader, writer):
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    finally:
        writer.close()

@pytest.fixture
async def echo_server():
    server = await asyncio.start_server(echo_handler, '127.0.0.1', 0)
    await server.start_serving()
    host, port = server.sockets[0].getsockname()
    yield port
    server.close()
    await server.wait_closed()

@pytest.mark.asyncio
async def test_proxy_normal(echo_server):
    config = FaultConfig()
    proxy = ProxyServer('127.0.0.1', 0, '127.0.0.1', echo_server, config)
    await proxy.start()
    proxy_port = proxy.server.sockets[0].getsockname()[1]
    
    reader, writer = await asyncio.open_connection('127.0.0.1', proxy_port)
    
    msg = b"hello world"
    writer.write(msg)
    await writer.drain()
    
    resp = await reader.read(1024)
    assert resp == msg
    
    writer.close()
    await writer.wait_closed()
    await proxy.stop()

@pytest.mark.asyncio
async def test_proxy_latency(echo_server):
    config = FaultConfig(latency_ms=100.0) # 100ms each way? No, 100ms per direction, so 200ms RTT
    proxy = ProxyServer('127.0.0.1', 0, '127.0.0.1', echo_server, config)
    await proxy.start()
    proxy_port = proxy.server.sockets[0].getsockname()[1]
    
    reader, writer = await asyncio.open_connection('127.0.0.1', proxy_port)
    
    start_time = time.monotonic()
    msg = b"latency test"
    writer.write(msg)
    await writer.drain()
    
    resp = await reader.read(1024)
    end_time = time.monotonic()
    
    assert resp == msg
    # At least 200ms latency, allow some margin
    assert (end_time - start_time) >= 0.15
    
    writer.close()
    await writer.wait_closed()
    await proxy.stop()

@pytest.mark.asyncio
async def test_proxy_throttling(echo_server):
    config = FaultConfig(throttle_bytes_per_sec=1000) # 1KB/s per direction
    proxy = ProxyServer('127.0.0.1', 0, '127.0.0.1', echo_server, config)
    await proxy.start()
    proxy_port = proxy.server.sockets[0].getsockname()[1]
    
    reader, writer = await asyncio.open_connection('127.0.0.1', proxy_port)
    
    payload = b"x" * 2000 # 2KB data
    start_time = time.monotonic()
    writer.write(payload)
    await writer.drain()
    
    # Needs to read back 2KB. At 1KB/s, it should take at least 2 seconds (or 4s total if both directions are throttled)
    resp = await reader.readexactly(2000)
    end_time = time.monotonic()
    
    assert len(resp) == 2000
    assert (end_time - start_time) >= 1.5 # Relaxed bound to prevent flakiness
    
    writer.close()
    await writer.wait_closed()
    await proxy.stop()

@pytest.mark.asyncio
async def test_proxy_drop(echo_server):
    config = FaultConfig(drop_probability=1.0) # 100% drop
    proxy = ProxyServer('127.0.0.1', 0, '127.0.0.1', echo_server, config)
    await proxy.start()
    proxy_port = proxy.server.sockets[0].getsockname()[1]
    
    reader, writer = await asyncio.open_connection('127.0.0.1', proxy_port)
    
    writer.write(b"should drop")
    await writer.drain()
    
    # Should get EOF or ConnectionResetError
    resp = await reader.read(1024)
    assert resp == b"" # EOF
    
    writer.close()
    await writer.wait_closed()
    await proxy.stop()

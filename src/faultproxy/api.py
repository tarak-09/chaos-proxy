import logging
from aiohttp import web
import dataclasses
from .faults import FaultConfig

logger = logging.getLogger(__name__)

class ManagementAPI:
    def __init__(self, fault_config: FaultConfig, host: str = "127.0.0.1", port: int = 8080):
        self.fault_config = fault_config
        self.host = host
        self.port = port
        self.app = web.Application()
        self.app.add_routes([
            web.get('/config', self.get_config),
            web.get('/', self.get_config),
            web.put('/config', self.update_config),
            web.post('/config', self.update_config),
        ])
        self.runner = None
        self.site = None

    async def get_config(self, request):
        return web.json_response(dataclasses.asdict(self.fault_config))

    async def update_config(self, request):
        try:
            data = await request.json()
            
            # Create a copy to test validation
            temp_config = dataclasses.replace(self.fault_config)
            
            # Extract possible fields
            if 'latency_ms' in data:
                temp_config.latency_ms = float(data['latency_ms'])
            if 'latency_jitter_ms' in data:
                temp_config.latency_jitter_ms = float(data['latency_jitter_ms'])
            if 'drop_probability' in data:
                temp_config.drop_probability = float(data['drop_probability'])
            if 'throttle_bytes_per_sec' in data:
                temp_config.throttle_bytes_per_sec = int(data['throttle_bytes_per_sec'])
                
            # Re-validate
            temp_config.__post_init__()
            
            # Apply changes
            self.fault_config.latency_ms = temp_config.latency_ms
            self.fault_config.latency_jitter_ms = temp_config.latency_jitter_ms
            self.fault_config.drop_probability = temp_config.drop_probability
            self.fault_config.throttle_bytes_per_sec = temp_config.throttle_bytes_per_sec
            
            logger.info(f"Updated FaultConfig via API: {self.fault_config}")
            return web.json_response(dataclasses.asdict(self.fault_config))
            
        except ValueError as e:
            return web.json_response({'error': str(e)}, status=400)
        except Exception as e:
            return web.json_response({'error': f"Invalid JSON payload: {e}"}, status=400)

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        logger.info(f"Management API listening on {self.host}:{self.port}")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            logger.info("Management API stopped.")

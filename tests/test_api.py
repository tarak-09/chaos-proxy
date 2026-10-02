import asyncio
import pytest
import aiohttp
from faultproxy.faults import FaultConfig
from faultproxy.api import ManagementAPI

@pytest.fixture
async def api_server_port():
    config = FaultConfig(latency_ms=10.0, drop_probability=0.1)
    api = ManagementAPI(fault_config=config, host='127.0.0.1', port=0)
    await api.start()
    
    # Get assigned port
    port = api.site._server.sockets[0].getsockname()[1]
    
    yield port, config
    
    await api.stop()

@pytest.mark.asyncio
async def test_api_get_config(api_server_port):
    port, config = api_server_port
    url = f"http://127.0.0.1:{port}/config"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            assert response.status == 200
            data = await response.json()
            assert data['latency_ms'] == 10.0
            assert data['drop_probability'] == 0.1
            assert data['throttle_bytes_per_sec'] == 0

@pytest.mark.asyncio
async def test_api_update_config(api_server_port):
    port, config = api_server_port
    url = f"http://127.0.0.1:{port}/config"
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "latency_ms": 50.0,
            "drop_probability": 0.5
        }
        async with session.put(url, json=payload) as response:
            assert response.status == 200
            data = await response.json()
            assert data['latency_ms'] == 50.0
            assert data['drop_probability'] == 0.5
            
        # Verify the underlying config was updated
        assert config.latency_ms == 50.0
        assert config.drop_probability == 0.5

@pytest.mark.asyncio
async def test_api_update_config_validation(api_server_port):
    port, config = api_server_port
    url = f"http://127.0.0.1:{port}/config"
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "drop_probability": 2.0 # Invalid
        }
        async with session.put(url, json=payload) as response:
            assert response.status == 400
            data = await response.json()
            assert "error" in data
            
        # Verify it wasn't updated
        assert config.drop_probability == 0.1

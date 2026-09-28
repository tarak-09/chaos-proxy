import pytest
from faultproxy.faults import FaultConfig

def test_fault_config_defaults():
    config = FaultConfig()
    assert config.latency_ms == 0.0
    assert config.latency_jitter_ms == 0.0
    assert config.drop_probability == 0.0
    assert config.throttle_bytes_per_sec == 0

def test_fault_config_validation():
    with pytest.raises(ValueError, match="latency_ms"):
        FaultConfig(latency_ms=-1.0)
        
    with pytest.raises(ValueError, match="latency_jitter_ms"):
        FaultConfig(latency_jitter_ms=-1.0)
        
    with pytest.raises(ValueError, match="drop_probability"):
        FaultConfig(drop_probability=1.5)
        
    with pytest.raises(ValueError, match="drop_probability"):
        FaultConfig(drop_probability=-0.5)

    with pytest.raises(ValueError, match="throttle_bytes_per_sec"):
        FaultConfig(throttle_bytes_per_sec=-100)

import dataclasses

@dataclasses.dataclass
class FaultConfig:
    """Configuration for network faults."""
    latency_ms: float = 0.0
    latency_jitter_ms: float = 0.0
    drop_probability: float = 0.0
    throttle_bytes_per_sec: int = 0

    def __post_init__(self):
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")
        if self.latency_jitter_ms < 0:
            raise ValueError("latency_jitter_ms must be >= 0")
        if not (0.0 <= self.drop_probability <= 1.0):
            raise ValueError("drop_probability must be between 0.0 and 1.0")
        if self.throttle_bytes_per_sec < 0:
            raise ValueError("throttle_bytes_per_sec must be >= 0")

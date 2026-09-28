# FaultProxy

FaultProxy is an asynchronous TCP proxy built in Python that injects simulated network faults for local resilience testing. 

By intercepting bi-directional traffic using `asyncio` streams, FaultProxy allows developers to deliberately inject configurable latency, artificial jitter, randomized connection drops, and bandwidth throttling to observe how applications and retry policies handle degraded network environments.

## Features

- **Artificial Latency:** Inject static delay per chunk of data.
- **Latency Jitter:** Add randomness to latency to simulate variable network conditions.
- **Connection Drops:** Simulate unexpected TCP connection resets.
- **Bandwidth Throttling:** Limit throughput (bytes per second) to test slow connections.
- **High Performance:** Decoupled `asyncio.Queue` architecture ensures that latency injection does not incorrectly throttle throughput, maintaining accurate network fault simulations.

## Installation

This project uses `uv` for dependency management.

1. Ensure Python 3.10+ and `uv` are installed.
2. Clone this repository and sync dependencies:
   ```bash
   uv sync
   ```

## Usage

You can run the proxy using the installed script via `uv`:

```bash
uv run faultproxy -p <local_port> -R <remote_host> -P <remote_port> [fault_flags...]
```

### CLI Options

- `-l, --local-host`: Local host to bind the proxy (default: `127.0.0.1`)
- `-p, --local-port`: Local port to bind the proxy (required)
- `-R, --remote-host`: Remote host to forward traffic to (required)
- `-P, --remote-port`: Remote port to forward traffic to (required)
- `--latency`: Base latency to inject in milliseconds
- `--jitter`: Latency jitter in milliseconds (+/-)
- `--drop-prob`: Probability of dropping the connection (0.0 to 1.0)
- `--throttle`: Maximum bandwidth in bytes per second (0 for unlimited)
- `-v, --verbose`: Enable verbose logging

## Worked Examples

### 1. Simple Forwarding (No faults)
Forward local port 8080 to `example.com:80`.
```bash
uv run faultproxy -p 8080 -R example.com -P 80 -v
```
In another terminal:
```bash
curl -H "Host: example.com" http://127.0.0.1:8080/
```

### 2. Injecting Latency and Jitter
Simulate a slow connection with 200ms latency and 50ms of jitter.
```bash
uv run faultproxy -p 8080 -R example.com -P 80 --latency 200 --jitter 50
```

### 3. Throttling Bandwidth
Limit the bandwidth to ~10KB/s (10240 bytes/sec).
```bash
uv run faultproxy -p 8080 -R example.com -P 80 --throttle 10240
```

### 4. Simulating Connection Drops
Drop approximately 10% of network data chunks, causing premature connection closures.
```bash
uv run faultproxy -p 8080 -R example.com -P 80 --drop-prob 0.1
```

## Running Tests

The project includes a comprehensive test suite covering the CLI configuration parsing and the actual TCP proxy behavior with fault injection.

To run the tests:
```bash
uv run pytest tests/
```

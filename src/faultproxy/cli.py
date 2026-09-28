import argparse
import asyncio
import logging
import sys

from .faults import FaultConfig
from .proxy import ProxyServer

def parse_args():
    parser = argparse.ArgumentParser(
        description="TCP proxy that injects network faults for local resilience testing."
    )
    
    parser.add_argument("-l", "--local-host", type=str, default="127.0.0.1",
                        help="Local host to bind the proxy (default: 127.0.0.1)")
    parser.add_argument("-p", "--local-port", type=int, required=True,
                        help="Local port to bind the proxy")
    parser.add_argument("-R", "--remote-host", type=str, required=True,
                        help="Remote host to forward traffic to")
    parser.add_argument("-P", "--remote-port", type=int, required=True,
                        help="Remote port to forward traffic to")
    
    parser.add_argument("--latency", type=float, default=0.0,
                        help="Base latency to inject in milliseconds")
    parser.add_argument("--jitter", type=float, default=0.0,
                        help="Latency jitter in milliseconds (+/-)")
    parser.add_argument("--drop-prob", type=float, default=0.0,
                        help="Probability of dropping the connection (0.0 to 1.0)")
    parser.add_argument("--throttle", type=int, default=0,
                        help="Maximum bandwidth in bytes per second (0 for unlimited)")
    
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    return parser.parse_args()

async def async_main():
    args = parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    
    try:
        fault_config = FaultConfig(
            latency_ms=args.latency,
            latency_jitter_ms=args.jitter,
            drop_probability=args.drop_prob,
            throttle_bytes_per_sec=args.throttle
        )
    except ValueError as e:
        sys.stderr.write(f"Configuration error: {e}\n")
        sys.exit(1)
        
    server = ProxyServer(
        local_host=args.local_host,
        local_port=args.local_port,
        remote_host=args.remote_host,
        remote_port=args.remote_port,
        fault_config=fault_config
    )
    
    await server.start()
    try:
        await server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    finally:
        await server.stop()

def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()

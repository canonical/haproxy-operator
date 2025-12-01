#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Simple gRPC server for integration testing."""

import argparse
import signal
import sys
from concurrent import futures

import grpc


def handle_unary_unary(request, context):
    """Echo back the request."""
    return request


class GenericHandler(grpc.GenericRpcHandler):
    """Generic handler that echoes all requests."""

    def service(self, handler_call_details):
        """Service any RPC call by echoing the request."""
        return grpc.unary_unary_rpc_method_handler(
            handle_unary_unary,
            request_deserializer=lambda x: x,
            response_serializer=lambda x: x,
        )


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Simple gRPC echo server")
    parser.add_argument("--port", type=int, default=50051, help="Port to listen on")
    parser.add_argument("--tls", action="store_true", help="Enable TLS")
    parser.add_argument("--cert", type=str, help="Path to certificate file")
    parser.add_argument("--key", type=str, help="Path to private key file")
    return parser.parse_args()


def main():
    """Start the gRPC server."""
    args = parse_args()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    server.add_generic_rpc_handlers((GenericHandler(),))

    if args.tls:
        if not args.cert or not args.key:
            print("Error: --cert and --key required when --tls is enabled", file=sys.stderr)
            sys.exit(1)

        with open(args.key, "rb") as f:
            private_key = f.read()
        with open(args.cert, "rb") as f:
            certificate_chain = f.read()

        server_credentials = grpc.ssl_server_credentials(((private_key, certificate_chain),))
        server.add_secure_port(f"[::]:{args.port}", server_credentials)
        print(f"gRPC server started with TLS on port {args.port}", flush=True)
    else:
        server.add_insecure_port(f"[::]:{args.port}")
        print(f"gRPC server started on port {args.port}", flush=True)

    server.start()

    def shutdown(signum, frame):
        print("Shutting down gRPC server...", flush=True)
        server.stop(0)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    server.wait_for_termination()


if __name__ == "__main__":
    main()

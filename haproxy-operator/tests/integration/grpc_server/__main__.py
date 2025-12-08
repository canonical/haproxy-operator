#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.


"""Simple gRPC server for integration testing."""

import argparse
import logging
import signal
import sys
from concurrent import futures

from . import echo_pb2, echo_pb2_grpc
import grpc
from grpc_reflection.v1alpha import reflection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class EchoService(echo_pb2_grpc.EchoServiceServicer):
    """gRPC Echo Service implementation."""

    def Echo(self, request, context):  # noqa: N802 (invalid-function-name)
        return echo_pb2.EchoResponse(message=request.message)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Simple gRPC echo server")
    parser.add_argument("--port", type=int, default=50051, help="Port to listen on")
    parser.add_argument("--tls", action="store_true", help="Enable TLS")
    parser.add_argument("--cert", type=str, help="Path to certificate file")
    parser.add_argument("--key", type=str, help="Path to private key file")

    args = parser.parse_args()
    if args.tls and not (args.cert and args.key):
        logging.error("--cert and --key required when --tls is enabled")
        sys.exit(1)

    return args


def main():
    args = parse_args()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Register Echo Service
    echo_pb2_grpc.add_EchoServiceServicer_to_server(EchoService(), server)

    # Enable reflection
    service_names = (
        echo_pb2.DESCRIPTOR.services_by_name["EchoService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    address = f"[::]:{args.port}"

    if args.tls:
        with open(args.key, "rb") as f:
            private_key = f.read()
        with open(args.cert, "rb") as f:
            certificate_chain = f.read()

        server_credentials = grpc.ssl_server_credentials(((private_key, certificate_chain),))
        server.add_secure_port(address, server_credentials)
        logging.info("gRPC Echo server started with TLS on port %d", args.port)
    else:
        server.add_insecure_port(address)
        logging.info("gRPC Echo server started on port %d", args.port)

    server.start()

    # Graceful shutdown on SIGTERM/SIGINT
    def shutdown(signum, frame):
        logging.info("Shutting down gRPC server...")
        server.stop(0)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    server.wait_for_termination()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3


"""Simple gRPC server for integration testing."""

import argparse
import logging
import signal
import sys
from concurrent import futures

import grpc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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

    args = parser.parse_args()
    if args.tls and not (args.cert and args.key):
        logging.error("--cert and --key required when --tls is enabled")
        sys.exit(1)
    return args


def main():
    """Start the gRPC server."""
    args = parse_args()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    server.add_generic_rpc_handlers((GenericHandler(),))

    if args.tls:
        with open(args.key, "rb") as f:
            private_key = f.read()
        with open(args.cert, "rb") as f:
            certificate_chain = f.read()

        server_credentials = grpc.ssl_server_credentials(((private_key, certificate_chain),))
        server.add_secure_port(f"[::]:{args.port}", server_credentials)
        logging.info("gRPC server started with TLS on port %d", args.port)
    else:
        server.add_insecure_port(f"[::]:{args.port}")
        logging.info("gRPC server started on port %d", args.port)

    server.start()

    def shutdown(signum, frame):
        logging.info("Shutting down gRPC server...")
        server.stop(0)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    server.wait_for_termination()


if __name__ == "__main__":
    main()

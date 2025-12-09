# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Makefile for generating gRPC stubs from echo.proto
# Useful for if echo.proto file is modified.

.PHONY: stubs clean

stubs:
	python3 -m grpc_tools.protoc \
	  --proto_path=. \
	  --python_out=. \
	  --grpc_python_out=. \
	  echo.proto
	sed -i 's/^import echo_pb2 as echo__pb2/from . import echo_pb2 as echo__pb2/' echo_pb2_grpc.py

clean:
	rm -f echo_pb2.py echo_pb2_grpc.py

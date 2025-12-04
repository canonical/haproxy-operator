.PHONY: stubs clean

stubs:
	python3 -m grpc_tools.protoc \
	  --proto_path=. \
	  --python_out=. \
	  --grpc_python_out=. \
	  echo.proto

clean:
	rm -f echo_pb2.py echo_pb2_grpc.py

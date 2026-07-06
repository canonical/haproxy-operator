(reference_grpc_support)=

# gRPC support

The HAProxy operator provides **automatic** gRPC support for frontends and backends using HTTPS on port 443.
A custom gRPC frontend port can be configured using the `external_grpc_port` option in the `haproxy-route` relation.

## Limitations

- Only when using HTTPS (the relation will be considered invalid if protocol is set to `http` in the `haproxy-route` relation)

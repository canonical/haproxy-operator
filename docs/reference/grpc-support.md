# gRPC support

The HAProxy operator provides **automatic** gRPC-over-HTTPS support for frontends and backends.

## Limitations

- Exposed only on port 443
- Only gRPC-over-TLS is supported (TLS encryption required)

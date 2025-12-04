# gRPC support

The HAProxy operator provides **automatic** gRPC-over-HTTPS support for frontends and backends.

## Limitations

- Exposed only on port 443
- Requires TLS (HTTPS)
- gRPC over clear-text (gRPC-C) is not supported

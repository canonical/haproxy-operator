(reference_http2_support)=

# HTTP/2 support

The HAProxy operator provides **automatic** HTTP/2 support for frontends and backends using HTTPS.
Application-Layer Protocol Negotiation (ALPN) is used to negotiate HTTP/2 connections, falling back to HTTP/1.1.

## Protocol independence

Frontend and backend connections negotiate HTTP versions independently and can thus use different HTTP versions.
HAProxy handles protocol conversion transparently.

## Limitations

- HTTP/2 requires TLS (HTTPS)
- HTTP/2 over clear-text (h2c) is not supported

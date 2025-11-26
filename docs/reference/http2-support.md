# HTTP/2 support

The HAProxy operator provides **automatic** HTTP/2 support for backends using HTTPS, and for frontends.
Application-Layer Protocol Negotiation (ALPN) is used to negotiate HTTP/2 connections, falling back to HTTP/1.1.

## Protocol independence

Frontend and backend connections negotiate HTTP versions independently.
The frontend and backend can use different HTTP versions.
HAProxy handles protocol conversion transparently.

## Limitations

- HTTP/2 requires TLS (HTTPS)
- HTTP/2 over clear-text (h2c) is not supported

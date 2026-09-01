---
myst:
  html_meta:
    "description lang=en": "How the HAProxy charm provides FTP support."
---

(reference_ftp_support)=

# FTP support

The HAProxy operator supports passive FTP through Layer-4 TCP load balancing via the `haproxy-route-tcp` relation.

For a complete working example, see {ref}`How to load balance an FTP server <how_to_loadbalancing_for_an_ftp_server>`.

## How it works

Passive FTP uses a control port a range of data ports. The operator needs to setup a dedicated frontend for the control port and another dedicated frontend for the data ports.

## FTPS and SFTP

**FTPS** (FTP over TLS) is supported through the same `haproxy-route-tcp` relation
with `tls_terminate=True`, which terminates TLS at the frontend, in which case
the backend receives plain FTP traffic.

**SFTP** runs over SSH and is independent of FTP. It can be proxied as a plain
TCP passthrough on the chosen port (this requires `enforce_tls=False` and `tls_terminate=False`). Note that
frontend port 22 is reserved for the Juju machine's SSH daemon, so a different
frontend port must be chosen (for example, frontend port 2222 to backend port 22).

## Limitations

- The FTP server must run in passive mode with a fixed passive port range.
- Active-mode FTP is not supported.
- No FTP-specific health checks are available (generic TCP send/expect checks can be used).

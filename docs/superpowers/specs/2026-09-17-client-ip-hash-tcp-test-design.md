# Client IP Hash TCP Test

## Goal

Extend `haproxy-operator/tests/integration/test_config.py` so the client-IP
hashing test verifies both HTTP and plain TCP access logs without relying on
TLS configuration.

## Design

- Add a test fixture path that provides HAProxy configured with its external
  hostname but without the self-signed certificate relation.
- Configure `client-ip-hash-salt` using the existing granted secret fixture and
  wait until HAProxy is active and idle.
- Execute `curl 127.0.0.1` inside the HAProxy unit using Juju 4-compatible
  `juju.exec`, then assert that the uppercase SHA-256 hash of
  `127.0.0.1 + LOG_HASH_SALT` appears in the HAProxy journal.
- Relate the existing TCP requirer with plain TCP settings, disabling TLS
  enforcement and TLS termination, and wait until the relation is ready.
- Execute `printf 'ping\\n' | nc 127.0.0.1 4444` inside the HAProxy unit and
  assert that the journal contains the hash followed by `:4444`.
- Use journal polling where needed because the access-log entry may arrive
  asynchronously.

## Scope

Only the integration test and the minimum supporting fixture changes are in
scope. Existing TLS-based integration fixtures and unrelated tests remain
unchanged.

## Verification

Run the focused test through the repository's tox integration environment in
the active Juju 4 multipass VM, using the freshly packed HAProxy charm. The
test must pass for both HTTP and TCP assertions.

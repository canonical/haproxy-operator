# Client IP Hash TCP Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the client-IP hashing integration test to verify both HTTP and plain TCP logs on Juju 4.

**Architecture:** Add a no-TLS HAProxy configuration fixture and a no-TLS TCP requirer RPC method. The test will configure the hash secret, issue HTTP and TCP requests from the HAProxy unit with `juju.exec`, and poll journald for the expected hash fields.

**Tech Stack:** Python, pytest, Jubilant, Juju 4, HAProxy, Any Charm TCP requirer, tox.

---

### Task 1: Add no-TLS test fixtures

**Files:**
- Modify: `haproxy-operator/tests/integration/conftest.py:103-140,335-350,353-384`
- Modify: `haproxy-operator/tests/integration/haproxy_route_tcp_requirer.py:83-96`

- [ ] **Step 1: Add a no-TLS configured application fixture**

Create a module-scoped fixture after `configured_application_with_tls_base` that configures the existing `application` with `external-hostname` but does not deploy or relate `self-signed-certificates`:

```python
@pytest.fixture(scope="module", name="configured_application_without_tls")
def configured_application_without_tls_fixture(application: str, juju: jubilant.Juju) -> str:
    """Configure HAProxy without adding a TLS provider relation."""
    juju.config(application, {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG})
    juju.wait(lambda status: all_active_and_idle(status, application), timeout=JUJU_WAIT_TIMEOUT)
    return application
```

- [ ] **Step 2: Add a no-TLS secret fixture**

Add a fixture alongside `log_hash_secret` that grants the same secret data to the no-TLS application and resets/removes it during teardown:

```python
@pytest.fixture(name="log_hash_secret_without_tls")
def log_hash_secret_without_tls_fixture(
    configured_application_without_tls: str,
    juju: jubilant.Juju,
):
    """Provide a granted log hash secret to HAProxy without TLS setup."""
    secret_uri = juju.add_secret(
        f"haproxy-log-hash-{uuid.uuid4().hex}",
        {"salt": LOG_HASH_SALT},
    )
    juju.grant_secret(secret_uri, configured_application_without_tls)
    yield secret_uri
    juju.cli("config", configured_application_without_tls, "--reset", "client-ip-hash-salt")
    juju.wait(lambda status: all_active_and_idle(status, configured_application_without_tls))
    juju.remove_secret(secret_uri)
```

- [ ] **Step 3: Add a plain TCP update method to the Any Charm source**

Add this method after `update_relation` in `haproxy_route_tcp_requirer.py`. It must omit `sni` and explicitly disable both TLS options:

```python
    def update_relation_plain_tcp(self):
        """Provide a plain TCP frontend and backend."""
        self._haproxy_route_tcp.provide_haproxy_route_tcp_requirements(
            port=4444,
            backend_port=4000,
            enforce_tls=False,
            tls_terminate=False,
            check_type=TCPHealthCheckType.GENERIC,
            check_interval=60,
            check_rise=3,
            check_fall=3,
            check_send="ping\r\n",
            check_expect="pong",
        )
```

- [ ] **Step 4: Add a plain TCP relation fixture**

Add a fixture beside `haproxy_route_tcp_relation` that uses `configured_application_without_tls`, integrates the existing `any_charm_haproxy_route_tcp_requirer`, waits for both agents, invokes `update_relation_plain_tcp`, then waits for both applications to be active and idle. Return the requirer application name, matching the existing fixture's lifecycle.

- [ ] **Step 5: Run focused collection and static checks**

Run:

```bash
uv run --group integration pytest --collect-only tests/integration/test_config.py
ruff check tests/integration/conftest.py tests/integration/haproxy_route_tcp_requirer.py
```

Expected: collection succeeds and Ruff reports no errors.

- [ ] **Step 6: Commit the fixture changes**

```bash
git add haproxy-operator/tests/integration/conftest.py haproxy-operator/tests/integration/haproxy_route_tcp_requirer.py
git commit -m "test: add plain TCP hashing fixtures"
```

### Task 2: Extend the hashing test

**Files:**
- Modify: `haproxy-operator/tests/integration/test_config.py:14-37`

- [ ] **Step 1: Add TCP fixture dependencies and no-TLS application**

Change the test dependencies to `configured_application_without_tls`, `log_hash_secret_without_tls`, and the new plain TCP relation fixture. Keep the existing `juju` fixture.

- [ ] **Step 2: Assert the HTTP hash**

Configure the secret and wait for HAProxy to become active and idle. Execute:

```python
juju.exec("curl -L 127.0.0.1", unit=unit)
expected_hash = hashlib.sha256(("127.0.0.1" + LOG_HASH_SALT).encode()).hexdigest().upper()
haproxy_logs = juju.exec("journalctl -u haproxy --no-pager -n 100", unit=unit).stdout
assert expected_hash in haproxy_logs
```

Use the non-TLS curl command requested by the test design.

- [ ] **Step 3: Establish the plain TCP relation and assert the TCP hash**

Request the plain TCP fixture, then execute:

```python
juju.exec("printf 'ping\\n' | nc 127.0.0.1 4444", unit=unit)
tcp_logs = juju.exec("journalctl -u haproxy --no-pager -n 100", unit=unit).stdout
assert f"{expected_hash}:4444" in tcp_logs
```

If journald delivery is asynchronous, poll `journalctl` with a bounded deadline rather than increasing a fixed sleep. The poll must separately require the HTTP hash and the `<hash>:4444` TCP field.

- [ ] **Step 4: Run the focused test locally before VM execution**

Run:

```bash
uv run --group integration pytest -q --collect-only tests/integration/test_config.py
```

Expected: one test is collected.

- [ ] **Step 5: Commit the test change**

```bash
git add haproxy-operator/tests/integration/test_config.py
git commit -m "test: verify client IP hashing over plain TCP"
```

### Task 3: Pack and run in the active Juju 4 VM

**Files:**
- Build artifact: `haproxy-operator/haproxy_amd64.charm`

- [ ] **Step 1: Pack the current charm on the host**

```bash
newgrp lxd <<'EOF'
cd /home/trung.thanh.phan@canonical.com/Canonical/haproxy-operator/.worktrees/update_test_config/haproxy-operator
charmcraft pack
EOF
```

- [ ] **Step 2: Run the focused test through tox in the active VM**

```bash
multipass exec dev -- bash -lc '
  export PATH="$HOME/.local/bin:$PATH"
  cd /home/trung.thanh.phan@canonical.com/Canonical/haproxy-operator/.worktrees/update_test_config/haproxy-operator
  tox -e integration -- tests/integration/test_config.py \
    --charm-file haproxy=haproxy_amd64.charm \
    --juju-model testing \
    --no-juju-teardown
'
```

Expected: the focused test passes on Juju 4. If it fails, inspect `juju status` and HAProxy journald output in the retained `testing-test-config` model, adjust only the test synchronization or command needed, repack if charm source changed, and rerun the same tox command.

- [ ] **Step 3: Clean up the retained test model**

```bash
multipass exec dev -- juju destroy-model testing-test-config --force --no-prompt --no-wait
```

- [ ] **Step 4: Verify the final worktree**

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intended source changes and the committed design/plan documentation remain.

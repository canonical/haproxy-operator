# HAProxy Operator — Copilot Instructions

## Repository layout

This is a **mono-repo** containing multiple independent Juju charms and related packages, each with its own `tox.toml`, `pyproject.toml`, and `uv.lock`:

| Directory | What it is |
|---|---|
| `haproxy-operator/` | Primary machine charm — manages HAProxy on VMs/bare metal |
| `haproxy-spoe-auth-operator/` | Machine charm — SPOE agent for authentication proxy |
| `haproxy-ddos-protection-configurator/` | Subordinate charm — DDoS protection configuration |
| `haproxy-route-policy-operator/` | Machine charm — route policy management |
| `haproxy-route-policy/` | Standalone Python package + snap for policy logic |
| `haproxy-spoe-auth-snap/` | Snap packaging for the SPOE auth workload |
| `terraform/` | Terraform modules for deploying the charm ecosystem |
| `tests/integration/` | Top-level cross-charm integration tests (run from repo root) |
| `docs/` | Sphinx/RTD documentation (Diátaxis structure) |

Each charm sub-directory is self-contained: always `cd` into the charm directory before running its `tox` commands.

## Build, test, and lint commands

All commands use **tox with the `uv-venv-lock-runner`** — no plain `pip install` needed.

### Per-charm (run inside the charm's directory, e.g. `cd haproxy-operator`)

```shell
tox                        # lint + unit + static + coverage-report (default envlist)
tox -e fmt                 # auto-fix formatting (ruff format + isort)
tox -e lint                # codespell + ruff check + mypy
tox -e unit                # unit tests with coverage
tox -e static              # bandit security analysis
tox -e integration         # integration tests (requires a live Juju model)

# Run a single unit test file or test function:
tox -e unit -- tests/unit/test_charm.py
tox -e unit -- tests/unit/test_charm.py::test_install
```

### Cross-charm integration tests (repo root)

```shell
tox -e integration         # runs tests/integration/ excluding per-charm test dirs
```

### Documentation (repo root)

```shell
cd docs && make run        # live preview
make spelling
make linkcheck
make vale
make lint-md
```

### Build a charm

```shell
cd haproxy-operator        # or any charm directory
charmcraft pack
```

## Architecture of `haproxy-operator`

The main charm follows a layered architecture:

1. **`src/charm.py` — `HAProxyCharm`**: The ops `CharmBase` subclass. Registers all event handlers, initialises relation libraries (ingress, TLS, SPOE, HA, COS, DDoS, route-policy). Decides which reconcile path to call based on `ProxyMode`.

2. **`src/state/` — immutable state objects**: Each module exposes a frozen `@dataclass` built from the ops model. They raise a subclass of `CharmStateValidationBaseError` on invalid data. The charm catches these to set blocked status. Key objects:
   - `CharmState` / `ProxyMode` — top-level state + routing mode enum (`HAPROXY_ROUTE`, `INGRESS`, `INGRESS_PER_UNIT`, `LEGACY`, `NOPROXY`, `INVALID`)
   - `TLSInformation`, `IngressRequirersInformation`, `IngressPerUnitRequirersInformation`
   - `HaproxyRouteRequirersInformation`, `SpoeAuthInformation`, `DDosProtection`, `HAInformation`

3. **`src/haproxy.py` — `HAProxyService`**: Manages the system HAProxy process — installs the apt package, writes `/etc/haproxy/haproxy.cfg` via Jinja2 templates, validates config with `haproxy -c`, reloads via systemd.

4. **`src/templates/` — Jinja2 config templates**: One template per proxy mode (`haproxy_ingress.cfg.j2`, `haproxy_ingress_per_unit.cfg.j2`, `haproxy_legacy.cfg.j2`, `haproxy_route.cfg.j2`, `haproxy_route_tcp.cfg.j2`, plus `haproxy_route_grpc.cfg.j2` and `spoe_auth.conf.j2`).

5. **`lib/charms/haproxy/`** — charm libraries **owned by this repo** (v0, v1, v2 subdirectories). These are published to Charmhub and consumed by requirer charms. They live in versioned directories and follow the Charmhub library lifecycle.

## Charm library ownership

`lib/charms/haproxy/` libraries are **owned here** (the charm name matches). All other `lib/charms/` directories (e.g. `traefik_k8s`, `tls_certificates_interface`) are **vendored** — do not modify them; they are auto-updated by `.github/workflows/auto_update_libs.yaml`. See `.github/instructions/charms-lib-updates.instructions.md` for the full review protocol.

## Key conventions

- **State validation pattern**: State modules raise typed exceptions (subclasses of `CharmStateValidationBaseError`). The charm catches them generically and sets `BlockedStatus`. Never raise raw `Exception` from state code.
- **Frozen dataclasses**: All state objects use `@dataclass(frozen=True)` with Pydantic validators. Use `pydantic.dataclasses.dataclass`, not `dataclasses.dataclass`.
- **ProxyMode enum**: The charm is in exactly one mode at a time. `charm.py` dispatches to `_reconcile_*` methods based on `ProxyMode`. Adding a new integration type requires a new `ProxyMode` value and a corresponding reconcile method.
- **Jinja2 templates**: HAProxy config is always rendered from `src/templates/`. Never build config strings in Python code.
- **Ruff line length**: 99 characters (`[tool.ruff] line-length = 99`).
- **Docstring convention**: Google-style (`pydocstyle.convention = "google"`). Required on all public symbols except test files.
- **Copyright header**: Every Python file must start with `# Copyright <year> Canonical Ltd.\n# See LICENSE file for licensing details.`
- **Commit signatures**: All commits must be cryptographically signed (GPG/SSH). Squash-merge policy on `main`.
- **Changelog**: Add an entry to `docs/changelog.md` for every feature, fix, or significant change.
- **Tests use `ops.testing` (Scenario)**: Unit tests build `ops.testing.State` objects and call `context.run(context.on.<event>(), state)`. The `scenario` library is also present; both styles exist.
- **Python 3.12** is the target version for all charms (`basepython = ["python3.12"]` in tox lint/unit envs).

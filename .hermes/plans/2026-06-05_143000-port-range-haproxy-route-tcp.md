# Port-Range Support for haproxy-route-tcp Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a `port-range` attribute to the `haproxy-route-tcp` interface that allows mapping a range of frontend ports 1-to-1 to the same backend ports (e.g., `port-range: "10500-10600"` means `:10512` on the frontend maps to `:10512` on the backend).

**Architecture:** Extend the `TcpRequirerApplicationData` pydantic model in the interface library to accept an optional `port_range` string field (format `"start-end"`). On the provider side, `HAProxyRouteTcpBackend` and `HAProxyRouteTcpFrontend` gain port-range awareness. The HAProxy config template renders a separate frontend+backend pair per port in the range (no server-level port, since frontend port == backend port in range mode). Port conflict checks cover every port in the range. The `open_ports` call in `charm.py` includes all ports from the range.

**Tech Stack:** Python, Pydantic, Jinja2 templates, ops framework

---

## Context & Requirements (from issue #525)

- A requirer can specify `port-range` (e.g. `"10500-10600"`) instead of a single `port`.
- Every port in that range is mapped 1-to-1: frontend `:10512` → backend `:10512`.
- Conflicts must be checked for the entire port range; if one port conflicts, the entire relation is invalid.
- When `port-range` is set, the `port` field on each server entry in the backend is removed (since the port is determined by the frontend bind).
- Every port in the range must be included in the `open_ports` call.
- `port` and `port-range` are mutually exclusive.
- The existing `backend_port` field still works when `port` is used; when `port-range` is used, `backend_port` is not applicable (the backend port equals the frontend port for each port in the range).

## Files Likely to Change

1. `haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py` — Interface library: add `port_range` to `TcpRequirerApplicationData`, `HaproxyRouteTcpRequirer.__init__`, `provide_haproxy_route_tcp_requirements`, helper methods, and provider-side `HaproxyRouteTcpRequirersData`.
2. `haproxy-operator/src/state/haproxy_route_tcp.py` — State model: add `port_range` to `HAProxyRouteTcpBackend` and `HAProxyRouteTcpFrontend`, update server generation logic.
3. `haproxy-operator/src/state/haproxy_route.py` — Update `parse_haproxy_route_tcp_requirers_data` to handle port-range, update `check_tcp_http_port_conflicts`.
4. `haproxy-operator/templates/haproxy_route_tcp.cfg.j2` — Template: render a frontend/backend pair per port in range; omit server port when port-range is active.
5. `haproxy-operator/src/charm.py` — Update `open_ports` to include all ports from ranges.
6. `haproxy-operator/tests/unit/test_haproxy_route_tcp_lib.py` — Library unit tests for `port_range`.
7. `haproxy-operator/tests/unit/test_state.py` — State unit tests for port-range frontends/backends.
8. `haproxy-operator/tests/unit/conftest.py` — Test fixture updates to support `port_range`.

---

### Task 1: Add `port_range` field to `TcpRequirerApplicationData` in the interface library

**Objective:** Extend the pydantic model to accept `port_range` as an optional string, validate it, and make it mutually exclusive with `port`.

**Files:**
- Modify: `haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py` (lines ~590-676, the `TcpRequirerApplicationData` class)

**Step 1: Write failing test**

Add test to `haproxy-operator/tests/unit/test_haproxy_route_tcp_lib.py`:

```python
def test_tcp_requirer_application_data_port_range():
    """Test that port_range can be set instead of port."""
    data = TcpRequirerApplicationData.from_dict({"port-range": "10500-10600"})
    assert data.port_range == "10500-10600"
    assert data.port is None

def test_tcp_requirer_application_data_port_and_port_range_exclusive():
    """Test that port and port_range are mutually exclusive."""
    with pytest.raises(DataValidationError):
        TcpRequirerApplicationData.from_dict({"port": 4000, "port-range": "10500-10600"})

def test_tcp_requirer_application_data_port_range_invalid_format():
    """Test that invalid port_range format is rejected."""
    with pytest.raises(DataValidationError):
        TcpRequirerApplicationData.from_dict({"port-range": "invalid"})

def test_tcp_requirer_application_data_port_range_ports_property():
    """Test the ports property expands the range."""
    data = TcpRequirerApplicationData.from_dict({"port-range": "10500-10502"})
    assert data.ports == [10500, 10501, 10502]
```

**Step 2: Run test to verify failure**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_haproxy_route_tcp_lib.py -k "test_tcp_requirer_application_data_port_range" -v`
Expected: FAIL — `port_range` attribute does not exist on model

**Step 3: Write minimal implementation**

In `haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py`, modify `TcpRequirerApplicationData`:

```python
import re

# Port range validation pattern: "start-end" where start < end, both valid ports
PORT_RANGE_PATTERN = re.compile(r"^(\d+)-(\d+)$")

def _validate_port_range(value: Optional[str]) -> Optional[str]:
    """Validate port_range string format and port validity.

    Args:
        value: The port range string (e.g. "10500-10600").

    Raises:
        ValueError: When the format is invalid or ports are out of range.

    Returns:
        The validated port range string.
    """
    if value is None:
        return value
    match = PORT_RANGE_PATTERN.match(value.strip())
    if not match:
        raise ValueError(f"Invalid port_range format: '{value}'. Expected 'start-end' (e.g. '10500-10600').")
    start, end = int(match.group(1)), int(match.group(2))
    if start >= end:
        raise ValueError(f"port_range start must be less than end: '{value}'.")
    if not (0 < start <= 65535 and 0 < end <= 65535):
        raise ValueError(f"port_range ports must be between 1 and 65535: '{value}'.")
    if end - start > 1000:
        raise ValueError(f"port_range too large (max 1001 ports): '{value}'.")
    return value
```

In the `TcpRequirerApplicationData` class, add the field and validators:

```python
    port: Optional[int] = Field(
        description="The port exposed on the provider. Mutually exclusive with port_range.",
        default=None,
        gt=0,
        le=65535,
    )
    port_range: Optional[Annotated[VALIDSTR, BeforeValidator(_validate_port_range)]] = Field(
        description=(
            "A range of ports to expose on the provider (e.g. '10500-10600'). "
            "Each port in the range maps 1-to-1 to the same port on the backend. "
            "Mutually exclusive with port."
        ),
        default=None,
    )
```

Add a computed property and update the existing `assign_default_backend_port` validator:

```python
    @property
    def ports(self) -> list[int]:
        """Expand port_range into a list of ports, or return [port] for single port.

        Returns:
            list[int]: List of all ports covered by this configuration.
        """
        if self.port_range:
            match = PORT_RANGE_PATTERN.match(self.port_range)
            start, end = int(match.group(1)), int(match.group(2))
            return list(range(start, end + 1))
        return [self.port] if self.port is not None else []

    @model_validator(mode="after")
    def check_port_or_port_range_set(self) -> "Self":
        """Ensure exactly one of port or port_range is set.

        Raises:
            ValueError: If both or neither are set.

        Returns:
            The validated model.
        """
        if self.port is not None and self.port_range is not None:
            raise ValueError("'port' and 'port_range' are mutually exclusive. Set one or the other.")
        if self.port is None and self.port_range is None:
            raise ValueError("Either 'port' or 'port_range' must be set.")
        return self
```

Update `assign_default_backend_port` to handle port_range:

```python
    @model_validator(mode="after")
    def assign_default_backend_port(self) -> "Self":
        """Assign a default value to backend_port if not set.

        The value is equal to the provider port. Not applicable when port_range is set.

        Returns:
            The model with backend_port default value applied.
        """
        if self.port_range is not None:
            # backend_port is not meaningful with port_range; each frontend port maps to the same backend port
            return self
        if self.backend_port is None and self.port is not None:
            self.backend_port = self.port
        return self
```

**Step 4: Run test to verify pass**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_haproxy_route_tcp_lib.py -k "test_tcp_requirer_application_data_port_range" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py haproxy-operator/tests/unit/test_haproxy_route_tcp_lib.py
git commit -m "feat(lib): add port_range field to TcpRequirerApplicationData"
```

---

### Task 2: Add `port_range` to `HaproxyRouteTcpRequirer` constructor, `provide_haproxy_route_tcp_requirements`, and helper methods

**Objective:** Expose `port_range` through the requirer's public API (constructor, provide method, configure helper).

**Files:**
- Modify: `haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py` (lines ~970-1210, `HaproxyRouteTcpRequirer` class)

**Step 1: Write failing test**

Add tests to `haproxy-operator/tests/unit/test_haproxy_route_tcp_lib.py`:

```python
def test_requirer_configure_port_range():
    """Test configure_port_range helper method."""
    requirer = HaproxyRouteTcpRequirer.__new__(HaproxyRouteTcpRequirer)
    requirer._application_data = {}
    result = requirer.configure_port_range("10500-10600")
    assert requirer._application_data["port_range"] == "10500-10600"
    assert result is requirer  # returns self for chaining
```

**Step 2: Run test to verify failure**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_haproxy_route_tcp_lib.py -k "test_requirer_configure_port_range" -v`
Expected: FAIL — `configure_port_range` method does not exist

**Step 3: Write minimal implementation**

In `HaproxyRouteTcpRequirer.__init__`, add `port_range: Optional[str] = None` parameter after `port`:

```python
    def __init__(
        self,
        charm: CharmBase,
        relation_name: str,
        *,
        port: Optional[int] = None,
        port_range: Optional[str] = None,
        ...
    ) -> None:
        """Initialize the HaproxyRouteRequirer.

        Args:
            ...
            port: The provider port. Mutually exclusive with port_range.
            port_range: A range of ports (e.g. '10500-10600') to expose on the provider.
                Each port maps 1-to-1 to the same port on the backend.
                Mutually exclusive with port.
            ...
        """
```

Pass `port_range` through to `_generate_application_data` and `self._application_data`.

Add `port_range: Optional[str] = None` to `provide_haproxy_route_tcp_requirements` as well.

Add `configure_port_range` helper method (chainable, like `configure_port`):

```python
    def configure_port_range(self, port_range: str) -> "Self":
        """Set the port range.

        Args:
            port_range: The port range to set (e.g. '10500-10600').

        Returns:
            Self: The HaproxyRouteTcpRequirer class.
        """
        self._application_data["port_range"] = port_range
        return self
```

Update `_generate_application_data` to include `port_range` in the constructed dict.

**Step 4: Run test to verify pass**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_haproxy_route_tcp_lib.py -k "test_requirer_configure_port_range" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py haproxy-operator/tests/unit/test_haproxy_route_tcp_lib.py
git commit -m "feat(lib): add port_range to HaproxyRouteTcpRequirer API"
```

---

### Task 3: Fix docstrings — replace "List of ports" with correct descriptions for `backend_port` and `sni`

**Objective:** Fix the misleading documentation identified in issue #403: `backend_port` is described as "List of ports the service is listening on" but is actually `Optional[int]`, and `sni` is described as "List of URL paths" but is a single string.

**Files:**
- Modify: `haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py` (multiple docstrings in `HaproxyRouteTcpRequirer.__init__` and `provide_haproxy_route_tcp_requirements`)

**Step 1: Identify all incorrect docstrings**

Search for all occurrences of:
- `"backend_port: List of ports the service is listening on."` → should be `"backend_port: The port the backend service is listening on. Defaults to the provider port."`
- `"sni: List of URL paths to route to this service."` → should be `"sni: Server name identification. Used to route traffic to the service."`

**Step 2: Apply fixes**

In `HaproxyRouteTcpRequirer.__init__` docstring (around line 1020):
```python
    backend_port: The port the backend service is listening on. Defaults to the provider port.
    sni: Server name identification. Used to route traffic to the service.
```

In `provide_haproxy_route_tcp_requirements` docstring (around line 1147):
```python
    backend_port: The port the backend service is listening on. Defaults to the provider port.
    sni: Server name identification. Used to route traffic to the service.
```

In the module-level getting-started docstring (around line 49):
```python
    backend_port=<optional>  # The port where the backend service is listening.
```
(This one is already correct, just verify.)

**Step 3: Run existing tests to verify nothing breaks**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_haproxy_route_tcp_lib.py -v`
Expected: PASS (docstring changes only)

**Step 4: Commit**

```bash
git add haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py
git commit -m "fix(docs): correct backend_port and sni descriptions in haproxy_route_tcp library"
```

---

### Task 4: Add `port_range` to `HAProxyRouteTcpBackend` state model

**Objective:** Make the provider-side state model aware of `port_range` so it can generate the correct HAProxy config.

**Files:**
- Modify: `haproxy-operator/src/state/haproxy_route_tcp.py`

**Step 1: Write failing test**

Add test to `haproxy-operator/tests/unit/test_state.py`:

```python
def test_haproxy_route_tcp_backend_port_range():
    """Test that a backend with port_range expands to multiple frontends."""
    requirer_data = haproxy_route_tcp_relation_data(port_range="10500-10502")
    backend = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(requirer_data)
    assert backend.application_data.port_range == "10500-10502"
    assert backend.application_data.ports == [10500, 10501, 10502]
```

**Step 2: Run test to verify failure**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_state.py -k "test_haproxy_route_tcp_backend_port_range" -v`
Expected: FAIL — `port_range` not accessible on `application_data` (needs Task 1 first)

**Step 3: Update state model**

In `haproxy-operator/src/state/haproxy_route_tcp.py`, update `HAProxyRouteTcpBackend`:

The backend inherits from `HaproxyRouteTcpRequirerData`, which contains `application_data: TcpRequirerApplicationData`. Since `TcpRequirerApplicationData` already has `port_range` after Task 1, the backend gets it for free.

The key change is in the `servers` property and `name` property. When `port_range` is set:
- Each port in the range gets its own frontend+backend in HAProxy.
- The `servers` property should NOT include a `port` field on server lines (the frontend port IS the backend port).
- The `name` property needs to be port-specific (e.g., `{application}_{port}`).

Add a new property:

```python
    @property
    def is_port_range(self) -> bool:
        """Check if this backend uses a port range.

        Returns:
            bool: True if port_range is set.
        """
        return self.application_data.port_range is not None
```

Modify `servers` to not set port when `is_port_range` is True (we'll handle this in the template):

```python
    @cached_property
    def servers(self) -> list[HaproxyRouteTcpServer]:
        """Get the list of backend servers for this TCP endpoint."""
        servers = []
        backend_addresses = self.application_data.hosts
        if not backend_addresses:
            backend_addresses = [unit_data.address for unit_data in self.units_data]

        for i, address in enumerate(backend_addresses):
            servers.append(
                HaproxyRouteTcpServer(
                    server_name=f"{self.application}-{i}",
                    port=cast(int, self.application_data.backend_port) if not self.is_port_range else 0,
                    address=address,
                    check=self.application_data.check,
                    maxconn=self.application_data.server_maxconn,
                    send_proxy=self.application_data.proxy_protocol,
                )
            )
        return servers
```

> Note: The `port=0` is a placeholder; the template will use the frontend port instead when `is_port_range` is True. Alternatively, we could make `port` optional on `HaproxyRouteTcpServer`, but that's a bigger refactor. The Jinja2 template will conditionally render the port.

**Step 4: Run test to verify pass**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_state.py -k "test_haproxy_route_tcp_backend_port_range" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add haproxy-operator/src/state/haproxy_route_tcp.py haproxy-operator/tests/unit/test_state.py
git commit -m "feat(state): add port_range awareness to HAProxyRouteTcpBackend"
```

---

### Task 5: Update `parse_haproxy_route_tcp_requirers_data` to expand port ranges into multiple frontends

**Objective:** When a requirer specifies `port-range`, each port in the range should produce its own frontend entry, allowing the same conflict-checking and config-rendering logic to apply.

**Files:**
- Modify: `haproxy-operator/src/state/haproxy_route.py` (lines ~785-805)

**Step 1: Write failing test**

Add test to `haproxy-operator/tests/unit/test_state.py`:

```python
def test_parse_haproxy_route_tcp_port_range_creates_multiple_frontends(
    haproxy_route_tcp_relation_data,
):
    """Test that a port-range requirer creates one frontend per port in range."""
    requirer_data = haproxy_route_tcp_relation_data(port_range="10500-10502")
    requirers_data = HaproxyRouteTcpRequirersData(requirers_data=[requirer_data])
    frontends = parse_haproxy_route_tcp_requirers_data(requirers_data)
    assert len(frontends) == 3  # 10500, 10501, 10502
    assert frontends[0].port == 10500
    assert frontends[1].port == 10501
    assert frontends[2].port == 10502
    for frontend in frontends:
        assert len(frontend.backends) == 1
        assert frontend.backends[0].is_port_range is True
```

**Step 2: Run test to verify failure**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_state.py -k "test_parse_haproxy_route_tcp_port_range_creates_multiple_frontends" -v`
Expected: FAIL — current code groups by `port` (int), `port_range` backends have `port=None`

**Step 3: Write implementation**

In `parse_haproxy_route_tcp_requirers_data`:

```python
def parse_haproxy_route_tcp_requirers_data(
    tcp_requirers: HaproxyRouteTcpRequirersData,
) -> list[HAProxyRouteTcpFrontend]:
    """Parse HAProxyRouteTcpFrontend data from requirers into frontend objects.

    Returns:
        list[HAProxyRouteTcpFrontend]: The parsed frontend data.
    """
    port_to_backends_mapping: dict[int, list[HAProxyRouteTcpBackend]] = defaultdict(list)
    for requirer in tcp_requirers.requirers_data:
        endpoint = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(requirer)
        # Expand port_range into individual ports, each becoming a separate frontend
        for port in endpoint.application_data.ports:
            port_to_backends_mapping[port].append(endpoint)
    tcp_frontends: list[HAProxyRouteTcpFrontend] = []
    for backends in port_to_backends_mapping.values():
        try:
            frontend = HAProxyRouteTcpFrontend.from_backends(backends)
            tcp_frontends.append(frontend)
        except HAProxyRouteTcpFrontendValidationError as exc:
            logger.error(f"Failed to parse TCP frontend: {exc}")
            continue
    return tcp_frontends
```

**Step 4: Run test to verify pass**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_state.py -k "test_parse_haproxy_route_tcp_port_range_creates_multiple_frontends" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add haproxy-operator/src/state/haproxy_route.py haproxy-operator/tests/unit/test_state.py
git commit -m "feat(state): expand port_range into individual frontends in parse function"
```

---

### Task 6: Update port conflict detection to cover all ports in a range

**Objective:** The `check_tcp_http_port_conflicts` validator in `HaproxyRouteRequirersInformation` must check every port in a range, not just the single `port` field.

**Files:**
- Modify: `haproxy-operator/src/state/haproxy_route.py` (lines ~614-666, the `check_tcp_http_port_conflicts` validator)

**Step 1: Write failing test**

Add test to `haproxy-operator/tests/unit/test_state.py`:

```python
def test_port_range_conflict_with_http_backends(
    haproxy_route_tcp_relation_data,
    haproxy_route_relation_data,
):
    """Test that a port range conflicting with HTTP ports (80/443) is detected."""
    # Create a TCP range that includes port 80
    tcp_data = haproxy_route_tcp_relation_data(port_range="79-81")
    http_data = haproxy_route_relation_data(service="http-service")
    info = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=...,
        haproxy_route_tcp=...,
        haproxy_route_policy=...,
        external_hostname="example.com",
        peers=[],
        ca_certs_configured=False,
    )
    # The entire TCP backend should be marked invalid due to port 80 conflict
    assert 0 in info.relation_ids_with_invalid_data_tcp
    assert 80 in info.ports_with_conflicts
```

**Step 2: Run test to verify failure**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_state.py -k "test_port_range_conflict_with_http_backends" -v`
Expected: FAIL or wrong behavior — current code only checks `frontend.port`, which for a range is the first port

**Step 3: Write implementation**

The current `check_tcp_http_port_conflicts` builds `tcp_ports = {frontend.port: frontend for frontend in self.tcp_frontends}`. Since Task 5 already expands port ranges into individual frontends, this mapping naturally covers every port in the range. The conflict detection logic should work as-is once frontends are expanded.

However, we need to ensure that when *one* port in a range conflicts, the *entire* relation (all ports from that range) is invalidated. The current logic marks the conflicting frontend's backend relation_ids as invalid. Since a single port-range relation generates multiple frontends sharing the same `relation_id`, all of them will be caught.

Verify this is the case by checking the `valid_tcp_frontends` method — it filters out frontends whose `port` is in `ports_with_conflicts`. This means individual conflicting-ports are filtered, but the remaining ports from the range would still be valid. Per the issue spec: "if one port in the range is conflicting then the entire backend will be considered invalid."

So we need to add: if any frontend from a port-range relation is invalid, mark all ports from that range as conflicting:

```python
    @model_validator(mode="after")
    def check_tcp_http_port_conflicts(self) -> Self:
        """Check for port conflicts between HTTP backends and TCP/gRPC backends."""
        # ... existing logic ...

        # NEW: If a port-range backend has any port in conflict,
        # mark ALL ports from that range as conflicting
        ports_to_invalidate = set()
        for port in self.ports_with_conflicts:
            for frontend in self.tcp_frontends:
                if frontend.port == port:
                    for backend in frontend.backends:
                        if backend.is_port_range:
                            # Mark all ports from this range as conflicting
                            for p in backend.application_data.ports:
                                ports_to_invalidate.add(p)
                            self.relation_ids_with_invalid_data_tcp.add(backend.relation_id)

        self.ports_with_conflicts.update(ports_to_invalidate)

        # Also add any newly-conflicting frontends' backends to the invalid set
        for frontend in self.tcp_frontends:
            if frontend.port in ports_to_invalidate:
                self.relation_ids_with_invalid_data_tcp.update(
                    backend.relation_id for backend in frontend.backends
                )

        if self.ports_with_conflicts:
            logger.warning(f"The following ports have conflicts: {self.ports_with_conflicts}")

        return self
```

**Step 4: Run test to verify pass**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_state.py -k "test_port_range_conflict" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add haproxy-operator/src/state/haproxy_route.py haproxy-operator/tests/unit/test_state.py
git commit -m "feat(state): extend port conflict detection to cover port ranges"
```

---

### Task 7: Update `conftest.py` test fixture to support `port_range`

**Objective:** The `haproxy_route_tcp_relation_data` fixture should accept `port_range` as a keyword argument.

**Files:**
- Modify: `haproxy-operator/tests/unit/conftest.py` (lines ~503-536)

**Step 1: Write failing test**

(Skipped — this is a fixture update that will be validated by the tests in Tasks 4-6.)

**Step 2: Implement**

In `conftest.py`, update `generate_requirer_data`:

```python
    def generate_requirer_data(
        *,
        relation_id: int = 0,
        **application_data: typing.Any,
    ) -> HaproxyRouteTcpRequirerData:
        """Generate haproxy-route-tcp relation data."""
        # If port_range is provided, remove default port to avoid mutual exclusivity error
        if "port_range" in application_data and "port" not in application_data:
            application_data.setdefault("port", None)
        return HaproxyRouteTcpRequirerData(
            relation_id=relation_id,
            application="tcp-route-requirer",
            application_data=typing.cast(
                TcpRequirerApplicationData,
                TcpRequirerApplicationData.from_dict(application_data),
            ),
            units_data=[
                typing.cast(
                    TcpRequirerUnitData,
                    TcpRequirerUnitData.from_dict({"address": "10.0.0.1"}),
                )
            ],
        )
```

**Step 3: Run existing tests to verify nothing breaks**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_state.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add haproxy-operator/tests/unit/conftest.py
git commit -m "test: update haproxy_route_tcp_relation_data fixture for port_range"
```

---

### Task 8: Update `haproxy_route_tcp.cfg.j2` template to handle port ranges

**Objective:** When `is_port_range` is True on a backend, the server lines should not include a port (the frontend port determines the backend port). Also, each frontend/backend pair for a port-range port should render correctly.

**Files:**
- Modify: `haproxy-operator/templates/haproxy_route_tcp.cfg.j2`

**Step 1: Understand the current rendering**

Currently, the `render_tcp_server` macro renders `server server_name address:port`. For port-range backends, the port on the server line should be the same as the frontend port (since it's 1-to-1 mapping). Since each frontend is expanded per-port (Task 5), the frontend already knows the port. The server just needs to use the frontend port instead of `server.port`.

**Step 2: Write failing test**

Add an integration-level template rendering test (or unit test verifying rendered output):

```python
def test_template_renders_port_range_backends_without_server_port():
    """Test that port-range backends render server lines using the frontend port."""
    # Create a port-range backend, render template, verify server lines use frontend port
    # This test should verify the rendered HAProxy config does not include
    # a separate backend_port on the server line when is_port_range is True.
```

**Step 3: Implement template changes**

Update `render_tcp_server` macro to accept an optional port override:

```jinja2
{% macro render_tcp_server(server, frontend_port=None) -%}
    server
{{ server.server_name }}
{{ server.address }}:{% if frontend_port %}{{ frontend_port }}{% else %}{{ server.port }}{% endif %}
{% if server.check %}
check
inter {{ server.check.interval }}s
rise {{ server.check.rise }}
fall {{ server.check.fall }}
{% endif %}
{% if server.maxconn %}
maxconn {{ server.maxconn }}
{% endif %}
{% if server.send_proxy %}
send-proxy
{% endif %}
{%- endmacro %}
```

In the backend rendering sections, pass the frontend port when the backend is a port-range backend:

```jinja2
{% for server in backend.servers %}
    {{ render_tcp_server(server, frontend_port=frontend.port if backend.is_port_range else None) | replace("\n", " ") }}
{% endfor %}
```

**Step 4: Run tests**

Run: `cd haproxy-operator && python -m pytest tests/unit/ -v`
Expected: PASS

**Step 5: Commit**

```bash
git add haproxy-operator/templates/haproxy_route_tcp.cfg.j2
git commit -m "feat(template): render server lines with frontend port for port-range backends"
```

---

### Task 9: Update `charm.py` to open all ports from port ranges

**Objective:** The `self.unit.set_ports(...)` call in the reconcile path must include every port from all port-range frontends.

**Files:**
- Modify: `haproxy-operator/src/charm.py` (lines ~417-429)

**Step 1: Understand current code**

Current code (around line 417):
```python
self.unit.set_ports(
    80,
    443,
    *(
        frontend.port
        for frontend in haproxy_route_requirers_information.valid_tcp_frontends()
    ),
    *(
        backend.application_data.external_grpc_port
        for backend in haproxy_route_requirers_information.valid_backends()
        if backend.application_data.external_grpc_port is not None
    ),
)
```

Since Task 5 already expands port ranges into individual frontends, `valid_tcp_frontends()` already returns one frontend per port in the range. The existing generator expression `frontend.port for frontend in ...` will naturally cover all ports.

**Step 2: Verify by reading the code**

No code change needed here — the expansion in Task 5 makes the existing generator cover all range ports. Just verify this with a test.

**Step 3: Write a test (integration or unit)**

Add to `tests/unit/test_charm.py` (or wherever charm unit tests live):

```python
def test_open_ports_includes_port_range():
    """Verify that set_ports is called with all ports from port-range frontends."""
    # This should be verified by checking that valid_tcp_frontends()
    # returns one frontend per port in the range, which the charm
    # then iterates over in set_ports.
```

**Step 4: Run tests**

Run: `cd haproxy-operator && python -m pytest tests/unit/ -v`
Expected: PASS

**Step 5: Commit** (if any code changes were needed)

```bash
git add haproxy-operator/src/charm.py
git commit -m "test: verify port-range ports are included in open_ports"
```

---

### Task 10: Update `HaproxyRouteTcpRequirersData` model for `port_range` support

**Objective:** The `HaproxyRouteTcpRequirersData` pydantic model (in the library) may need to be updated to handle `port_range` in its validation. Check if it groups by `port` and update accordingly.

**Files:**
- Modify: `haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py` (the `HaproxyRouteTcpRequirersData` class)

**Step 1: Read the `HaproxyRouteTcpRequirersData` class**

Search for this class in the library file and understand its structure. It's the model used by the provider to parse all requirers' data.

**Step 2: Check if any changes are needed**

The `HaproxyRouteTcpRequirersData` likely just contains a list of `HaproxyRouteTcpRequirerData` objects. Since `TcpRequirerApplicationData` already handles `port_range` validation (Task 1), the requirers data model should work as-is. Verify this.

**Step 3: Run tests**

Run: `cd haproxy-operator && python -m pytest tests/unit/ -v`
Expected: PASS

**Step 4: Commit** (only if changes were needed)

---

### Task 11: Bump LIBPATCH version

**Objective:** The interface library version must be bumped since we're adding a new field.

**Files:**
- Modify: `haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py` (line ~189, `LIBPATCH`)

**Step 1: Bump version**

Change `LIBPATCH = 4` to `LIBPATCH = 5`.

**Step 2: Run tests**

Run: `cd haproxy-operator && python -m pytest tests/unit/ -v`
Expected: PASS

**Step 3: Commit**

```bash
git add haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py
git commit -m "chore(lib): bump LIBPATCH to 5 for port_range feature"
```

---

### Task 12: Update module-level documentation in the library

**Objective:** Update the getting-started docstring at the top of `haproxy_route_tcp.py` to show `port_range` usage.

**Files:**
- Modify: `haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py` (lines ~1-156)

**Step 1: Add port_range usage example**

In the getting-started section, add an example:

```python
    # To use port-range instead of a single port:
    self.haproxy_route_tcp_requirer = HaproxyRouteTcpRequirer(
        self,
        relation_name="haproxy-route-tcp"
        port_range="10500-10600"  # Maps :10500-:10600 on frontend to :10500-:10600 on backend
    )
```

And update the chaining example:

```python
    self.haproxy_tcp_route_requirer = HaproxyRouteTcpRequirer(self, relation_name="") \
        .configure_port_range("10500-10600") \
        .configure_health_check(60, 5, 5) \
        .update_relation_data()
```

**Step 2: Run tests**

Run: `cd haproxy-operator && python -m pytest tests/unit/ -v`
Expected: PASS

**Step 3: Commit**

```bash
git add haproxy-operator/lib/charms/haproxy/v1/haproxy_route_tcp.py
git commit -m "docs(lib): add port_range usage examples to getting-started section"
```

---

### Task 13: Add `HaproxyRouteTcpBackend.name` support for port-range frontends

**Objective:** The backend `name` property currently uses `f"{self.application}_{self.application_data.port}"`. For port-range backends, `port` is None, so the name must use the frontend's port instead. Since frontends are expanded per-port (Task 5), the name needs to be parameterized.

**Files:**
- Modify: `haproxy-operator/src/state/haproxy_route_tcp.py`

**Step 1: Write failing test**

```python
def test_haproxy_route_tcp_backend_name_with_port_range():
    """Backend name must use the specific port, not the range."""
    requirer_data = haproxy_route_tcp_relation_data(port_range="10500-10502")
    backend = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(requirer_data)
    # name_for_port should return the correct name per port
    assert backend.name_for_port(10500) == "tcp-route-requirer_10500"
    assert backend.name_for_port(10501) == "tcp-route-requirer_10501"
```

**Step 2: Implement**

Add a `name_for_port` method to `HAProxyRouteTcpBackend`:

```python
    def name_for_port(self, port: int) -> str:
        """Get the unique name for this TCP endpoint for a specific port.

        Args:
            port: The frontend port.

        Returns:
            str: The endpoint name in format "{application}_{port}".
        """
        return f"{self.application}_{port}"
```

Update `name` property to use `ports[0]` when `port_range` is set:

```python
    @property
    def name(self) -> str:
        """Get the unique name for this TCP endpoint."""
        effective_port = self.application_data.ports[0] if self.is_port_range else self.application_data.port
        return f"{self.application}_{effective_port}"
```

**Step 3: Run test**

Run: `cd haproxy-operator && python -m pytest tests/unit/test_state.py -k "test_haproxy_route_tcp_backend_name_with_port_range" -v`
Expected: PASS

**Step 4: Commit**

```bash
git add haproxy-operator/src/state/haproxy_route_tcp.py haproxy-operator/tests/unit/test_state.py
git commit -m "feat(state): add name_for_port method for port-range backend naming"
```

---

### Task 14: Full test suite verification

**Objective:** Run the entire test suite to ensure nothing is broken.

**Step 1: Run all unit tests**

Run: `cd haproxy-operator && python -m pytest tests/unit/ -v`
Expected: ALL PASS

**Step 2: Run linting/type checks**

Run: `cd haproxy-operator && tox -e lint` (or whatever linting command is used)
Expected: PASS

**Step 3: Commit** (if any fixes were needed)

---

## Risks & Tradeoffs

1. **Backward compatibility:** `port_range` is a new optional field; existing charms using `port` continue to work unchanged. The `TcpRequirerApplicationData` validator enforces mutual exclusivity, so there's no ambiguity.

2. **LIBAPI bump consideration:** Since `port_range` is additive and `port` remains the default way to configure, this is a non-breaking change. LIBPATCH bump is sufficient. If we later decide to deprecate `port` in favor of `port_range`, that would require a LIBAPI major bump.

3. **Port range size:** The `_validate_port_range` function caps ranges at 1001 ports to prevent excessive resource consumption. This is an arbitrary limit that can be adjusted.

4. **Template complexity:** The Jinja2 template change is minimal — passing the frontend port to the server macro when the backend is a port-range backend. This avoids creating separate "port-range frontend/backend" concepts.

5. **SNI + port_range interaction:** When using SNI routing with port ranges, each port in the range gets its own frontend. SNI routing would apply per-frontend. This seems correct but should be documented.

## Open Questions

1. Should `backend_port` be allowed alongside `port_range`? The current design says no — when `port_range` is set, the backend port always equals the frontend port. If a user needs different backend ports, they should use multiple single-port relations.

2. Should the HAProxy config render a single frontend with multiple `bind` lines (one per port), or one frontend per port? The current design uses one frontend per port (cleaner separation, matches existing code structure). This could be changed to use `bind` ranges if HAProxy supports them.

3. Health checks in port-range mode: should the health check configuration apply to all ports in the range? The current design says yes — it's one backend configuration applied across all ports.

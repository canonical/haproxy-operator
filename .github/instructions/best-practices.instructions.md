---
description: 'Accumulated best practices extracted from LLM-authored PR reviews'
applyTo: '**'
---

# Best Practices

Lessons learned from reviewing LLM-authored pull requests in this repository.
Each rule is linked to the PR where the pattern was first observed.

<!-- Add new themes and rules below this line -->

## Relation Contracts

### Do
- Update both sides of a shared charm library and bump the library patch version in the same PR when relation data changes — *schema changes are only safe when publishers and consumers validate the same payload* ([PR #475](https://github.com/canonical/haproxy-operator/pull/475))

  ```python
  # Before review — the library validated proxied_endpoint as a full URL
  LIBPATCH = 5

  proxied_endpoint: str | None = Field(
      description=("URL for the proxied endpoint that's exposing the Django web UI."),
  )

  @field_validator("proxied_endpoint")
  def validate_proxied_endpoint(cls, value: str | None) -> str | None:
      """Validate that the proxied endpoint, if provided, is a valid URL."""
      if value is not None:
          try:
              TypeAdapter(HttpUrl).validate_python(value)
          except ValueError as exc:
              raise ValueError(f"Invalid proxied endpoint URL: {value}") from exc
      return value
  ```

  ```python
  # After review — both library copies accepted the hostname string the consumer needed
  LIBPATCH = 8

  def valid_domain(value: str) -> str:
      """Validate if value is a valid domain without wildcards."""
      if not bool(domain(value)):
          raise ValueError(f"Invalid domain: {value}")
      return value

  proxied_endpoint: Annotated[str, BeforeValidator(valid_domain)] | None = Field(
      description=("URL for the proxied endpoint that's exposing the Django web UI."),
  )
  ```

### Don't
- Don't force raw relation data through `HttpUrl` casts when the consumer only needs a hostname — *review simplified the interface to match the actual value used by the policy charm* ([PR #475](https://github.com/canonical/haproxy-operator/pull/475))

  ```python
  app_data = HaproxyRoutePolicyRequirerAppData(
      backend_requests=backend_requests,
      proxied_endpoint=cast(HttpUrl | None, proxied_endpoint),
  )
  ```

## Reconcile Flow

### Do
- Gate service-dependent refresh logic on service readiness before calling the policy API from `_reconcile` — *relation data can exist before the snap service is ready to answer requests* ([PR #475](https://github.com/canonical/haproxy-operator/pull/475))

  ```python
  # Before review — refresh happened unconditionally during reconcile
  self._fetch_and_refresh_backend_requests(
      haproxy_route_policy_information, haproxy_route_policy_requirer_data
  )
  if (proxied_endpoint := haproxy_route_policy_requirer_data.proxied_endpoint) and (
      host := proxied_endpoint.host
  ):
      allowed_hosts.append(host)
  ```

  ```python
  # After review — only refresh when the service is actually running
  if is_service_active():
      # We can only send requests to the policy API if the service is active.
      self._fetch_and_refresh_backend_requests(
          haproxy_route_policy_information, haproxy_route_policy_requirer_data
      )

  if proxied_endpoint := haproxy_route_policy_requirer_data.proxied_endpoint:
      allowed_hosts.append(proxied_endpoint)
  ```

- Publish relation data once, immediately after computing the backend state that feeds it — *keeping the write next to the source data makes ordering easier to reason about* ([PR #475](https://github.com/canonical/haproxy-operator/pull/475))

  ```python
  if self.unit.is_leader() and self.haproxy_route_policy.relation is not None:
      self.haproxy_route_policy.provide_haproxy_route_policy_requests(
          haproxy_route_requirers_information.backend_requests_for_policy,
          haproxy_route_requirers_information.policy_provider_backend.hostname
          if haproxy_route_requirers_information.policy_provider_backend
          else None,
      )
  ```

### Don't
- Don't scatter the same relation update across multiple points in the HAProxy reconcile path — *the earlier version published policy requests again later in `_configure_haproxy_route`, hiding the real source of truth* ([PR #475](https://github.com/canonical/haproxy-operator/pull/475))

  ```python
  if self.unit.is_leader():
      self.haproxy_route_policy.provide_haproxy_route_policy_requests(
          haproxy_route_requirers_information.backend_requests_for_policy
      )
      self._publish_haproxy_route_proxied_endpoints(haproxy_route_requirers_information)
      self._publish_haproxy_route_tcp_proxied_endpoints(
          haproxy_route_requirers_information, ha_information
      )
  ```

## Validation Tests

### Do
- Update unit tests to assert the reviewed relation payload shape when a schema changes — *tests should lock in the hostname contract that the reviewed library now publishes* ([PR #475](https://github.com/canonical/haproxy-operator/pull/475))

  ```python
  request = HaproxyRoutePolicyBackendRequest(**VALID_BACKEND_REQUEST)
  app_data = HaproxyRoutePolicyRequirerAppData(
      backend_requests=[request], proxied_endpoint="example.com"
  )
  ```

- Rewrite existing tests to assert the reviewed contract, checking `relation_ids_with_invalid_data` instead of expecting an exception — *the merged behavior excludes only invalid relations rather than failing model construction outright* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # Before review — what the LLM originally tested
  with pytest.raises(DataValidationError):
      HaproxyRouteRequirersData(
          requirers_data=[requirer_data1, requirer_data2], relation_ids_with_invalid_data=set()
      )
  ```

  ```python
  # After review — what the test became
  data = HaproxyRouteRequirersData(
      requirers_data=[requirer_data1, requirer_data2], relation_ids_with_invalid_data=set()
  )

  assert data.relation_ids_with_invalid_data == {1, 2}
  ```

- Add mixed duplicate-and-unique test data so coverage proves only conflicting relations are filtered out — *this protects against regressions that would discard valid requirers together with invalid ones* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # After review — new coverage added in the PR
  requirer_data_1 = haproxy_route_relation_data(
      "duplicate-service",
      relation_id=1,
  )
  requirer_data_2 = haproxy_route_relation_data(
      "duplicate-service",
      relation_id=2,
  )
  requirer_data_3 = haproxy_route_relation_data(
      "unique-service",
      relation_id=3,
  )

  data = HaproxyRouteRequirersData(
      requirers_data=[requirer_data_1, requirer_data_2, requirer_data_3],
      relation_ids_with_invalid_data=set(),
  )

  assert data.relation_ids_with_invalid_data == {1, 2}
  ```

### Don't
- Don't keep tests coupled to a richer URL type than the relation contract actually uses — *the original test encoded an unnecessary `HttpUrl` cast and full URL* ([PR #475](https://github.com/canonical/haproxy-operator/pull/475))

  ```python
  request = HaproxyRoutePolicyBackendRequest(**VALID_BACKEND_REQUEST)
  app_data = HaproxyRoutePolicyRequirerAppData(
      backend_requests=[request], proxied_endpoint=cast(HttpUrl, "https://example.com")
  )

- Don't stop at an exception-only test for duplicate relation data — *it never verifies the real requirement that valid relations must continue through validation while only the conflicting ones are excluded* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # Before review — what the LLM originally tested
  with pytest.raises(DataValidationError):
      HaproxyRouteRequirersData(
          requirers_data=[requirer_data1, requirer_data2], relation_ids_with_invalid_data=set()
      )

## Testing Cross-Charm Changes

### Do
- Add integration coverage that exercises the full multi-charm flow, including the requirer relation, the database relation, and a real policy API request — *cross-charm features need end-to-end proof, not just relation wiring* ([PR #475](https://github.com/canonical/haproxy-operator/pull/475))

  ```python
  any_charm_haproxy_route_deployer(HAPROXY_ROUTE_REQUIRER_NAME)
  lxd_juju.integrate(f"{haproxy_route_policy}:database", f"{postgresql}:database")
  lxd_juju.integrate(
      f"{HAPROXY_ROUTE_REQUIRER_NAME}:require-haproxy-route", configured_application_with_tls
  )
  ...
  response = requests.get(
      f"https://{str(haproxy_unit_ip)}/api/v1/requests",
      headers={"Host": TEST_HOSTNAME},
      auth=("admin", admin_credentials["password"]),
      verify=False,
  )
  ```

### Don't
- Don't stop an integration test after wiring relations and waiting for `all_active` — *that only proves deployment reached steady state, not that HAProxy and the policy service exchanged the reviewed data correctly* ([PR #475](https://github.com/canonical/haproxy-operator/pull/475))

  ```python
  lxd_juju.integrate(
      f"{configured_application_with_tls}:haproxy-route",
      any_charm_haproxy_route_deployer,
  )
  lxd_juju.integrate(
      f"{configured_application_with_tls}:haproxy-route-policy",
      haproxy_route_policy,
  )
  ...
  lxd_juju.wait(jubilant.all_active)
  ```

## Validation and Error Handling

### Do
- Make uniqueness validators follow the library's soft-fail contract by recording invalid relation IDs instead of raising from the validator itself — *this preserves partial processing and matches the existing invalid-data accumulator pattern used by sibling validators* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # Before review — what the LLM originally wrote
  services = [
      requirer_data.application_data.service for requirer_data in self.requirers_data
  ]
  if len(services) != len(set(services)):
      raise DataValidationError("Services declaration by requirers must be unique.")
  ```

  ```python
  # After review — what the code became
  relation_ids_per_service: dict[str, list[int]] = defaultdict(list[int])
  for requirer_data in self.requirers_data:
      relation_ids_per_service[requirer_data.application_data.service].append(
          requirer_data.relation_id
      )

  self.relation_ids_with_invalid_data.update(
      *[
          set(relation_ids)
          for relation_ids in relation_ids_per_service.values()
          if len(relation_ids) > 1
      ]
  )
  ```

- Update validator docstrings when validation changes from hard-fail to soft-fail — *the public contract needs to explain that duplicate relations are tracked and filtered rather than crashing validation* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # Before review — what the LLM originally documented
  """Check that requirers define unique services.

  Raises:
      DataValidationError: When requirers declared duplicate services.

  Returns:
      The validated model.
  """
  ```

  ```python
  # After review — what the docstring became
  """Check that requirers define unique services.
  If multiple requirers declare the same service name,
  their relation ids are added to relation_ids_with_invalid_data.

  Returns:
      The validated model.
  """
  ```

### Don't
- Don't raise a new `DataValidationError` from a deep model validator when analogous validators already report invalid relations through `relation_ids_with_invalid_data` — *that introduces a failure mode that diverges from the surrounding library contract* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # Before review — what the LLM originally wrote
  if len(services) != len(set(services)):
      raise DataValidationError("Services declaration by requirers must be unique.")
  ```

---
description: 'Accumulated best practices extracted from LLM-authored PR reviews'
applyTo: '**'
---

# Best Practices

Lessons learned from reviewing LLM-authored pull requests in this repository.
Each rule is linked to the PR where the pattern was first observed.

<!-- Add new themes and rules below this line -->

## Error handling and defensive coding

### Do
- Mark duplicate relation payloads as invalid instead of raising from model validators — *this prevents one bad relation from crashing charm reconciliation* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # Before review
  services = [
      requirer_data.application_data.service for requirer_data in self.requirers_data
  ]
  if len(services) != len(set(services)):
      raise DataValidationError("Services declaration by requirers must be unique.")

  # After review
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

- Keep duplicate-detection implementation consistent across validators — *shared shape reduces maintenance drift and edge-case mismatches* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # After review — check_external_grpc_port_unique uses the same grouped-set update style
  self.relation_ids_with_invalid_data.update(
      *[
          set(relation_ids)
          for relation_ids in relation_ids_per_port.values()
          if len(relation_ids) > 1
      ]
  )
  ```

### Don't
- Don't raise `DataValidationError` for duplicate-service detection when invalid relation tracking is available — *exception-based validation here causes avoidable control-flow failure* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # Before review
  if len(services) != len(set(services)):
      raise DataValidationError("Services declaration by requirers must be unique.")
  ```

## Charm library versioning

### Do
- Increment `LIBPATCH` when published library behavior changes — *consumers need a version bump to pull the fix safely* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # Before review
  LIBPATCH = 1

  # After review
  LIBPATCH = 2
  ```

### Don't
- Don't ship validator behavior changes under the same patch version — *downstream projects may miss critical fixes during lib sync* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # Before review
  LIBPATCH = 1
  ```

## Testing coverage hygiene

### Do
- Add tests for validation behavior changes — *in this PR, test files had no `base -> first` diff, so `first -> final` test changes are treated as late-added coverage rather than reviewer-refined test patterns* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # After review — evidence that tests were added later in the PR
  def test_check_services_unique(
      haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
  ) -> None:
      ...
      assert data.relation_ids_with_invalid_data == {1, 2}
  ```

### Don't
- Don't forget to add tests when changing validator logic — *missing early test coverage obscures regressions during review* ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  # After review — tests were introduced only later in the PR
  data = HaproxyRouteRequirersData(
      requirers_data=[requirer_data1, requirer_data2], relation_ids_with_invalid_data=set()
  )
  assert data.relation_ids_with_invalid_data == {1, 2}
  ```

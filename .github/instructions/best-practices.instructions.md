---
description: 'Accumulated best practices extracted from LLM-authored PR reviews'
applyTo: '**'
---

# Best Practices

Lessons learned from reviewing LLM-authored pull requests in this repository.
Each rule is linked to the PR where the pattern was first observed.

<!-- Add new themes and rules below this line -->

## Handling Jinja2 templates

Keep rendering logic in charm-state dataclasses or helper builders so templates stay declarative.
State properties that produce ACL conditions should return bare condition strings; the template is responsible for wrapping them in `acl` directive syntax.

### Do
- Compute derived values in charm-state dataclasses or helper builders before rendering ([PR #452](https://github.com/canonical/haproxy-operator/pull/452))

  ```python
  @dataclass(frozen=True)
  class CharmState:
      enable_hsts: bool

  spop_port = 443 if enable_hsts else 80
  ```

  ```jinja2
  server:
    addr: 0.0.0.0:{{ spop_port }}
  ```

- Use properties that return either an empty string or a ready-to-concatenate config string — this removes `{% if %}` blocks from the Jinja2 server line entirely ([PR #452](https://github.com/canonical/haproxy-operator/pull/452))

  ```python
  @property
  def server_health_check_configuration(self) -> str:
      if self.check is None:
          return ""
      return f" check inter {self.check.interval}s rise {self.check.rise} fall {self.check.fall}"

  @property
  def https_backend_server_configuration(self) -> str:
      if self.application_data.protocol != "https":
          return ""
      return f" ssl ca-file {HAPROXY_CAS_FILE!s} alpn h2,http/1.1 check-alpn h2,http/1.1"
  ```

  ```jinja2
  server {{ server.server_name }} {{ server.address }}:{{ server.port }}{{ server.server_health_check_configuration }}{{ backend.https_backend_server_configuration }}
  ```

## Error handling and defensive coding

Treat duplicate relation payloads as invalid state and keep duplicate checks in the same grouped-set shape across validators.

### Do
- Mark duplicate relation payloads invalid with grouped-set tracking ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  services = [
      requirer_data.application_data.service for requirer_data in self.requirers_data
  ]
  if len(services) != len(set(services)):
      raise DataValidationError("Services declaration by requirers must be unique.")

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

- Reuse the same grouped-set update shape in each validator ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  self.relation_ids_with_invalid_data.update(
      *[
          set(relation_ids)
          for relation_ids in relation_ids_per_port.values()
          if len(relation_ids) > 1
      ]
  )
  ```

### Don't
- Raise `DataValidationError` for duplicate-service detection ([PR #500](https://github.com/canonical/haproxy-operator/pull/500))

  ```python
  if len(services) != len(set(services)):
      raise DataValidationError("Services declaration by requirers must be unique.")
  ```

## Charm library versioning

Bump `LIBPATCH` when published library behavior changes.

## Testing coverage hygiene

Add tests when validator logic changes so the new behavior is exercised before merge.

When the PR review thread explains a broader design choice, treat that comment thread as part of the
evidence for the rule, not just the diff.

## Module ownership of constants

Constants that are semantically part of the charm state (e.g. file paths consumed by state properties) belong in the relevant state module, not in the service or render layer.

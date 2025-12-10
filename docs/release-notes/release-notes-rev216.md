(release_notes_release_notes_rev216)=

# HAProxy release notes – 2.8/stable, revision 216

These release notes cover new features and changes in HAProxy for revisions
148-216 between the dates of 2025-04-30 and 2025-08-20.

Main features:

* Added the `ingress-per-unit` relation.
* Added new field to the requirer application databag.

Main bug fixes:

* Fixed a typo in the cookie fetch method in the load-balancing algorithm ([PR](https://github.com/canonical/haproxy-operator/pull/179)).
* Fixed an ambiguous endpoint in an integration test ([PR](https://github.com/canonical/haproxy-operator/pull/129)).

See our [Release policy and schedule](landing-page.md).

## Requirements and compatibility

The charm operates HAProxy v2.8.

The table below shows the required or supported versions of the software necessary to operate the charm.

| Software                | Required version |
|-------------------------|------------------|
| Juju                    | 3.x              |
| Terraform               | 1.6              |
| Terraform Juju provider | 0.19             |
| Ubuntu                  | 24.04            |

## Updates

The following major and minor features were added in this release.

### Add consistent hashing support

Consistent hashing reduce redistribution of clients to another backend server when server is added/removed. On HAProxy it will add 
```
hash-type consistent
```
to the configuration.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/171)


### Allow customization to configure port for HTTP check

You can now customize the port used for `http-check`.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/119)


### Added hosts attribute to requirer data

You can now override the unit IP addresses used to generate server entries in the HAProxy configuration.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/149)


### Validated requirer relation data object

Validation is now done on both the requirer and provider side to check
for invalid characters. On the requirer an exception will be raised
while on the provider the related service will be ignored.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/118)


### Updated integration tests

The integration tests now only run one unit to save CI time.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/131)


### Updated certifications handling

The charm now requests a new certification for each subdomain during initialization.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/150)


### Refactored source code and tests

Several changes to the source code, integration tests, and unit tests.
The reconcile function was broken into smaller modules, mode validation is
now performed in a state in the charm class, some tests were migrated to jubilant,
and other tests were moved to different directories.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/158)


### Added a new relation

Added the `ingress-per-unit` relation to support reaching each
unit separately for a Vault deployed behind an ingress.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/153)
* [Related issue](https://github.com/canonical/haproxy-operator/issues/88)


### Added new field to the requirer application databag

The requirer application databag now has a "protocol" field to
support HTTPS upstream servers.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/164)


### Added `http-server-close` support

Added the `http-server-close` argument to the HAProxy configuration.
When this argument is set, it closes the connection after the request.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/175)


### Enforce health check fields to all be set

To avoid any issue with partial health checks configuration, all related fields
must be set for the configuration to be valid.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/170)


### Added first scenario test

Added the first scenario test which starts the transition process from Harness to Scenario.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/108)


### Rendered `retry` configuration in template and remove `retry_interval` attribute

The `retry_interval` attribute has been removed since there's no way to configure that in HAProxy.
To configure the time between 2 retries we can use `timeout.connect`.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/166)


### Added terraform charm and product module

You can now deploy HAProxy with high-availability support through Terraform. The module can be found under https://github.com/canonical/haproxy-operator/tree/main/terraform/product.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/98)

## Breaking changes

The following backwards-incompatible changes are included in this release.

### Updated library to add more attributes

The `subdomain` attribute has been replaced with the `hostname`
and `additional_hostnames` attribute. The charm now sends an
empty list as the `proxied_endpoints` when the requirer data
is ignored.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/152)

## Bug fixes

* Added missing new lines in haproxy-route j2 template and added missing `unit_address` in `provide_haproxy_route_requirements` helper method ([PR](https://github.com/canonical/haproxy-operator/pull/128)).
* Pinned the HAProxy version and prevented automatic updates ([PR](https://github.com/canonical/haproxy-operator/pull/136)).
* Disabled sending host headers in `httpchk` so the charm doesn't refuse to proxy incoming requests ([PR](https://github.com/canonical/haproxy-operator/pull/111)).
* Added checks before reloading the HAProxy service and set the charm to waiting if the validation fails ([PR](https://github.com/canonical/haproxy-operator/pull/122)).
* Fixed a typo in the cookie fetch method in the load-balancing algorithm ([PR](https://github.com/canonical/haproxy-operator/pull/179)).
* Added a new dependency to fix the linting step ([PR](https://github.com/canonical/haproxy-operator/pull/105)).
* Added "s" suffix to timeout entries ([PR](https://github.com/canonical/haproxy-operator/pull/162)).
* Fixed Jinja2 handling of newlines to prevent invalid configuration generation ([PR](https://github.com/canonical/haproxy-operator/pull/139)).
* Mitigated bug in Terraform provider by setting subordinate charm units to `1` ([PR](https://github.com/canonical/haproxy-operator/pull/135)).
* Fixed an ambiguous endpoint in an integration test ([PR](https://github.com/canonical/haproxy-operator/pull/129)).


## Known issues

* [Addressing Protocol Mismatch Between SSL Termination and HTTPS-Required Backends](https://github.com/canonical/haproxy-operator/issues/70)
* [Add an action to get proxied endpoints](https://github.com/canonical/haproxy-operator/issues/80)

## Thanks to our contributors

[Thanhphan1147](https://github.com/Thanhphan1147), [dimaqq](https://github.com/dimaqq), [yhaliaw](https://github.com/yhaliaw), [erinecon](https://github.com/erinecon), [swetha1654](https://github.com/swetha1654), [javierdelapuente](https://github.com/javierdelapuente), [alithethird](https://github.com/alithethird), [arturo-seijas](https://github.com/arturo-seijas)
(release_notes_release_notes_0003)=

# HAProxy release notes – 2.8/stable

These release notes cover new features and changes in HAProxy for revisions
293-314.

Main features:

* Implemented custom external port for gRPC in haproxy-route relation.

See our {ref}`Release policy and schedule <release_notes_index>`.

## Requirements and compatibility

The charm operates HAProxy 2.8.

The table below shows the required or supported versions of the software necessary to operate the charm.

| Software                | Required version |
|-------------------------|------------------|
| Juju                    | 3.x              |
| Terraform               | 1.6              |
| Terraform Juju provider | 1.1              |
| Ubuntu                  | 24.04            |

## Updates

The following major and minor features were added in this release.

### Added basic DDoS protection mechanisms

Added sensible security defaults to prevent basic DDoS attacks.
By default, basic DDoS protection mechanisms are enabled, including
`http-request`, `http-keep-alive` and client timeouts, automatic dropping of connections
with invalid, empty, or missing host headers.
A new configuration option `ddos-protection` has been added to enable basic DDoS protections
if needed.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/300)

### Added terraform modules for the HAProxy DDoS Protection configurator charm

Now the HAProxy DDoS Protection configurator charm has Terraform modules in the `charm` and `product` directories.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/328)

### Added Terraform module for `haproxy-spoe-auth` charm and product

The `terraform/charm` directory has been refactored so the modules are under a subdirectory, one per charm.
The `haproxy-spoe-auth` charm now has a Terraform module, and
the Terraform product module has been updated to include the options to protect hostnames and
have the option to deploy the `oauth-external-idp-integrator` if the configuration
is given.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/316)

### Added the provider side of the `ddos-protection` interface

Now the `ddos-protection` interface has a provider side with
validation in the interface provider to ensure that the limit policy is not set when the
rate limits are not set.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/318)

### Added documentation for `haproxy-spoe-auth`

Now the documentation contains a how-to guide and reference page on using HAProxy as a forward
authentication proxy with OpenID Connect.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/315)
* {ref}`reference_spoe-auth_support`
* {ref}`how_to_protect_hostname_spoe_auth`

### Added path rewrite support for gRPC backends

Added support for path rewriting in gRPC backends. This support is used in the same way as path rewrites for HTTP backends, by specifying the `path_rewrite_expressions` in the `haproxy-route` relation.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/329)

### Added header rewrite support for gRPC backends

Added support for header rewriting in gRPC backends. This support is used in the same way as header rewrites for HTTP backends, by specifying the 'header_rewrite_expressions' in the `haproxy-route` relation.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/324)

### Added the `ddos-protection` interface

Introduced a new interface `ddos-protection` to configure DDoS protection features
in HAProxy.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/302)

### Implemented custom external port for gRPC in `haproxy-route` relation

Added support for custom external port for gRPC services using the configuration option `external_grpc_port`.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/287)

## Bug fixes

* Added missing settings from haproxy-route-tcp relation template ([PR](https://github.com/canonical/haproxy-operator/pull/325)).
* Removed extra slash in `_get_backend_proxied_endpoints` function in `charm.py` ([PR](https://github.com/canonical/haproxy-operator/pull/299), [related issue](https://github.com/canonical/haproxy-operator/issues/285)).

## Known issues

* [Support wildcards in hostname for haproxy-route and haproxy-route-tcp.](https://github.com/canonical/haproxy-operator/issues/360)
* [HAProxy raises TLSNotReadyError despite valid topology](https://github.com/canonical/haproxy-operator/issues/362)
* [Expose HAProxy unit IPs and their availability via the relation data](https://github.com/canonical/haproxy-operator/issues/365)
* [Share single certificate between units in HA deployment](https://github.com/canonical/haproxy-operator/issues/366)

## Thanks to our contributors

[`skatsaounis`](https://github.com/skatsaounis), [`swetha1654`](https://github.com/swetha1654), [`javierdelapuente`](https://github.com/javierdelapuente), [`alexdlukens`](https://github.com/alexdlukens), [`f-atwi`](https://github.com/f-atwi)

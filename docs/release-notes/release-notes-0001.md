<!-- Remember to update this file for your charm!! -->
(release_notes_release_notes_0001)=

# HAProxy release notes – 2.8/stable

These release notes cover new features and changes in HAProxy for revisions
217-283 between the dates of 2025-08-21 and 2025-12-08.

Main features:

1. Support for TCP is added via the new `haproxy-route-tcp` relation.
2. Support for downstream HTTPS is added together with the `certificate_transfer` relation.
3. The product's terraform module now supports keepalived as an alternative option to hacluster for high-availability.
4. Removed the restriction on header rewrite expressions in the `haproxy-route` relation ( previously HAProxy's reserved characters were forbidden )
5. Added HTTP/2 support over HTTPS for backend communication. Note that this requires the backend to set `protocol=HTTPS` and the use of the `certificate_transfer` relation is also required.
6. Requirers can now request for backends to be made available via HTTP using the new `allow_http` attribute of the `haproxy-route` relation.

Main bug fixes:

* Fixed handling of `haproxy-route-tcp` requirer data.

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

### Added `get-proxied-endpoints` action

Now the charm has a new action, `get-proxied-endpoints`, that
gets the endpoints proxied by HAProxy.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/214)
* [Related documentation](https://charmhub.io/haproxy/actions?channel=2.8/edge#get-proxied-endpoints)
* [Related issue](https://github.com/canonical/haproxy-operator/issues/80)

### Updates to the HAProxy apt package

* Unpinned the HAProxy APT package version [(PR)](https://github.com/canonical/haproxy-operator/pull/276).
* To fix an issue where the `install` hook was failing,
  the charm now uses `2.8.5-1ubuntu3.4` of the HAProxy apt package [(PR)](https://github.com/canonical/haproxy-operator/pull/209).

### Get network information from relation endpoint binding

So that the charm will work with Juju spaces, now the charm
gets its network information from the relation endpoint binding.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/223)


### Added `haproxy-spoe-auth` snap

Now the repository contains a snap package running a
Stream Processing Offload Engine (SPOE) agent for the charm.
The SPOE agent works with HAProxy to act as an authentication
proxy for both LDAP and OIDC.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/224)


### Added http-server-close support

Added the `http-server-close` argument to the HAProxy configuration.
When this argument is set, it closes the connection after the request.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/175)


### Remove `haproxy_route` restriction for expressions

Currently some valid characters are not allowed for expressions in the
`haproxy_route` relation. Now only the newline character is restricted.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/257)


### Updated Terraform module to support keepalived

The Terraform module was updated to provide support for keepalived, and
validation rules were added to ensure mutual exclusivity between the two options.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/243)


### Added `rsyslog` configuration when HAProxy is installed

Now the `rsyslog` configuration is added when the HAProxy package
is installed, setting the logging destination to the Unix socket.      

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/187)


### Documented release policy and schedule for the `haproxy-operator` monorepo

Add documentation for the release policy and schedule covering
both the `haproxy` and `haproxy-spoe-auth` charms in the monorepo.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/272)
* {ref}`Related documentation <release_notes_index>`


### Added HTTPS backend support for HAProxy routing

Enable HAProxy to route traffic to HTTPS backends with certificate handling and validation.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/172)


### Allow enabling http for haproxy route backend

Add a new `allow_http attribute` to allow disabling mandatory HTTPS redirection for backends.
Add logic to build the required ACL and rendering logic in the Jinja2 template.

Relevant links:
* [PR](https://github.com/canonical/haproxy-operator/pull/230)


### Run renovate only twice a month

Run renovate only twice a month except for vulnerability alerts.
Also use allNonMajor.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/262)


### Added SPOE Auth interface library

Add the `charms.haproxy.v0.spoe_auth` library to enable SPOE authentication integration.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/229)


### Added HTTP/2 support to HAProxy

Added HTTP/2 support in the HAProxy charm for both frontend and backend connections.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/249)


### Updated TCP ports behavior after updating HAProxy configuration

After the HAProxy configuration is updated, the requested TCP ports
are opened.    

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/188)


### Added HAProxy SPOE Auth Charm

Added a new charm for HAProxy SPOE authentication.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/232)


### Migrated the Python project to use `uv` and `ruff`

Now the repository uses `uv`, `tox-uv`, and `ruff` for building,
testing and linting.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/225)

## Bug fixes

* Fixed handling of `haproxy-route-tcp` requirer data ([PR](https://github.com/canonical/haproxy-operator/pull/215)).
* Fixed a typo in the cookie fetch method in the load-balancing algorithm ([PR](https://github.com/canonical/haproxy-operator/pull/179)).

## Known issues

* [Allow a port component in the haproxy-route hostname and additional-hostnames attribute](https://github.com/canonical/haproxy-operator/issues/288)
* [Return apex domain endpoint when no paths defined](https://github.com/canonical/haproxy-operator/issues/285)
* [Match host header as domain, not as string](https://github.com/canonical/haproxy-operator/issues/245)

## Thanks to our contributors

[`f-atwi`](https://github.com/f-atwi), [`yhaliaw`](https://github.com/yhaliaw), [`Thanhphan1147`](https://github.com/Thanhphan1147), [`gregory-schiano`](https://github.com/gregory-schiano), [`javierdelapuente`](https://github.com/javierdelapuente), [`swetha1654`](https://github.com/swetha1654), [`alithethird`](https://github.com/alithethird), [`dimaqq`](https://github.com/dimaqq), [`weiiwang01`](https://github.com/weiiwang01), [`erinecon`](https://github.com/erinecon)

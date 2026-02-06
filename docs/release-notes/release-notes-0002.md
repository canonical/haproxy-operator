(release_notes_release_notes_0002)=

# HAProxy release notes – 2.8/stable

These release notes cover new features and changes in HAProxy for revisions
284-290.

Main features:

* Implemented spoe-auth relation in HAProxy.

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

### Implemented spoe-auth relation

The `spoe-auth` relation has been implemented in HAProxy.
Now the charm provides support for authenticating hostnames using
[HAProxy SPOE Authentication](https://github.com/criteo/haproxy-spoe-auth)
with OpenID Connect.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/279)

Related documentation:

* {ref}`SPOE authentication support <reference_spoe-auth_support>`

### Created HAProxy DDoS Protection Configurator charm

Now the code base contains the HAProxy DDoS Protection Configurator charm. This charm 
serves as a configurator for HAProxy to provide DDoS protection capabilities.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/284)

Related documentation:

* {ref}`how_to_enable_ddos_protection`

## Bug fixes

No bug fixes in this release.

## Known issues

* [[haproxy-route] Match host header as domain, not as string](https://github.com/canonical/haproxy-operator/issues/245)
* [Peers discarded in HAProxy due to invalid configuration](https://github.com/canonical/haproxy-operator/issues/326)

## Thanks to our contributors

[`javierdelapuente`](https://github.com/javierdelapuente), [`swetha1654`](https://github.com/swetha1654)

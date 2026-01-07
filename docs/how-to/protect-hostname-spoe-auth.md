(how_to_protect_hostname_spoe_auth)=

<!-- vale Canonical.007-Headings-sentence-case = NO -->

# How to protect a hostname using OpenID Connect

<!-- vale Canonical.007-Headings-sentence-case = YES -->

This guide will show you how to protect a hostname using forward authentication proxy with OpenID Connect.

The protected hostname is provided through the `haproxy-route` relation.

## Deploy and configure the `haproxy` charm

Deploy the `haproxy` and `self-signed-certificates` charms. Please refer to the {ref}`Tutorial <tutorial_getting_started>` for a more detailed explanation.

```sh
juju deploy haproxy --channel=2.8/edge --base=ubuntu@24.04
juju deploy self-signed-certificates cert
juju integrate haproxy:certificates cert
```

## Deploy and integrate the `ingress-configurator` charm

To specify the protected hostname, use the `haproxy-route` relation. In this guide
we use the `ingress-configurator` charm, which serves as an adapter between
the `ingress` and `haproxy-route` relations or as an integrator.

```sh
juju deploy ingress-configurator --channel=edge --config hostname=protected.internal --config backend-addresses=<backend-address>
juju integrate ingress-configurator:haproxy-route haproxy
```

By default, `haproxy` serves the `protected.internal` hostname without forward authentication proxy.

## Deploy and integrate the `haproxy-spoe-auth` charm

The `haproxy-spoe-auth` charm provides the SPOE agent for the OpenID Connect authentication.
Deploy and integrate it with `haproxy`:

```sh
juju deploy haproxy-spoe-auth --channel=edge
juju integrate haproxy-spoe-auth haproxy
```

## Configure the hostname in the `haproxy-spoe-auth` charm

The hostname to protect is specified as a configuration option in the
`haproxy-spoe-auth` charm:

```sh
juju config haproxy-spoe-auth hostname=protected.internal
```

<!-- vale Canonical.007-Headings-sentence-case = NO -->

## Integrate the `haproxy-spoe-auth` charm with an OpenID Connect using the `oauth` interface

<!-- vale Canonical.007-Headings-sentence-case = YES -->

The `oauth` interface is used to configure the OIDC Provider credentials.

The `oauth` interface is provided by the [Canonical Identity Platform](https://charmhub.io/topics/canonical-identity-platform)
or by the [`oauth-external-idp-integrator` charm](https://charmhub.io/oauth-external-idp-integrator).

With a deployed and configured `oauth-external-idp-integrator` charm, you can integrate it with `haproxy-spoe-auth` with:

```sh
juju integrate haproxy-spoe-auth oauth-external-idp-integrator
```

At this point, the hostname `protected.internal` is protected with OpenID Connect and requires authentication.

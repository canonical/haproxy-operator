(how_to_protect_hostname_spoe_auth)=

# How to protect a hostname using OpenID Connect

This guide will show you how to protect a hostname using forward authentication proxy with OpenID Connect.

The protected hostname is provided through the `haproxy-route` relation.

## Deploy and configure the `haproxy` charm

Deploy the `haproxy` and `self-signed-certificates` charms. Please refer to the {ref}`Tutorial <getting_started>` for a more detailed explanation.

```sh
juju deploy haproxy --channel=2.8/edge --base=ubuntu@24.04
juju deploy self-signed-certificates cert
juju integrate haproxy:certificates cert
```

## Deploy and integrate the ingress configurator charm

```sh
juju deploy ingress-configurator --channel=edge --config hostname=protected.internal --config backend-addresses=<backend-address>
juju integrate ingress-configurator:haproxy-route haproxy
```

By default, `haproxy` serves the `protected.internal` hostname without forward authentication proxy.

## Deploy and integrate the haproxy-spoe-auth charm

```sh
juju deploy haproxy-spoe-auth --channel=edge
juju integrate haproxy-spoe-auth haproxy
```

## Configure the hostname to protect

```sh
juju config haproxy-spoe-auth hostname=protected.internal
```

## Integrate the haproxy-spoe-auth charm with an OpenID using the `oauth` interface

The `oauth` interface is used to configure the OIDC Provider credentials.

The `oauth` interface is provided by the [Canonical Identity Platform](https://charmhub.io/topics/canonical-identity-platform)
or by the [`oauth-external-idp-integrator` charm](https://charmhub.io/oauth-external-idp-integrator).

With a deployed and configured `oauth-external-idp-integrator` charm, you can integrate it with `haproxy-spoe-auth` with:

```sh
juju integrate haproxy-spoe-auth oauth-external-idp-integrator
```

At this point, the hostname `protected.internal` is protected with OpenID Connect and requires authentication.

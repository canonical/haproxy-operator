(how_to_enable_ddos_protection)=

# Enable DDoS protection

This guide walks you through enabling DDoS protection for your HAProxy deployment using the [HAProxy DDoS Protection Configurator charm](https://github.com/canonical/haproxy-operator/tree/main/haproxy-ddos-protection-configurator). This charm provides advanced rate limiting, connection blocking, timeout customization and more to help protect your services against distributed denial-of-service attacks.

## Deploy and configure the `haproxy` charm

Deploy the `haproxy` and `self-signed-certificates` charms. Please refer to the {ref}`Tutorial <tutorial_getting_started>` for a more detailed explanation.

```sh
juju deploy haproxy --channel=2.8/edge
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

## Deploy and integrate the `haproxy-ddos-protection-configurator` charm

Deploy the DDoS protection configurator charm and integrate it with your existing HAProxy deployment:

```
juju deploy haproxy-ddos-protection-configurator
juju integrate haproxy haproxy-ddos-protection-configurator
```

## Configure DDoS protection settings

The configurator charm provides several configuration options to customize the protection level 
according to your needs. For a full list of all the configurations, refer to the HAProxy DDoS 
Protection configurator's [Charmhub](https://charmhub.io/haproxy-ddos-protection-configurator/configurations) documentation.

### Example configuration

Here's a example command to configure the `haproxy-ddos-protection-configurator` charm:

```
juju config haproxy-ddos-protection-configurator \
    rate-limit-requests-per-minute=2000 \
    rate-limit-connections-per-minute=1000 \
    concurrent-connections-limit=200 \
    error-rate-per-minute=100 \
    limit-policy="deny 503" \
    ip-allow-list="10.0.0.0/8,172.16.0.0/12" \
    http-request-timeout=30 \
    http-keepalive-timeout=60 \
    client-timeout=50 \
    deny-paths="/admin,/env"
```

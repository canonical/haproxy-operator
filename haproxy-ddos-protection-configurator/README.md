# Overview

A [Juju](https://juju.is/) [subordinate](https://documentation.ubuntu.com/juju/3.6/reference/charm/#subordinate-charm) 
[charm](https://juju.is/docs/olm/charmed-operators) that serves as a configurator for HAProxy 
to provide DDoS protection capabilities.

HAProxy is a TCP/HTTP reverse proxy which is particularly suited for high availability environments.
Since the HAProxy charm currently has many configuration options, this configurator charm aims to 
simplify the deployment of HAProxy with DDoS by separating the DDoS configuration from the main 
HAProxy charm.

Like any Juju charm, this charm supports one-line deployment, configuration, integration, scaling, 
and more.

For information about how to deploy, integrate, and manage this charm, see the 
Official [HAProxy operator documentation](https://charmhub.io/haproxy).


# Usage

Deploy the HAProxy charm and integrate it with a certificate provider charm
```
juju deploy haproxy --channel=2.8/edge
juju config haproxy external-hostname="fqdn.example"

juju deploy self-signed-certificates
juju integrate haproxy self-signed-certificates:certificates
```

Deploy the HAProxy DDoS protection configurator charm and integrate it with HAProxy:
```
juju deploy haproxy-ddos-protection-configurator
juju integrate haproxy haproxy-ddos-protection-configurator
```

# HAProxy project information

- [HAProxy Homepage](http://haproxy.1wt.eu/)
- [HAProxy mailing list](http://haproxy.1wt.eu/#tact)

## Project and community

The HAProxy Operator is a member of the Ubuntu family. It's an
open source project that warmly welcomes community projects, contributions,
suggestions, fixes and constructive feedback.
* [Code of conduct](https://ubuntu.com/community/code-of-conduct)
* [Get support](https://discourse.charmhub.io/)
* [Join our online chat](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
* [Contribute](https://charmhub.io/chrony/docs/contributing)
* [Roadmap](https://charmhub.io/haproxy/docs/roadmap)
Thinking about using the HAProxy charm for your next project? [Get in touch](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)!

---

For further details,
[see the charm's detailed documentation](https://charmhub.io/haproxy/docs).

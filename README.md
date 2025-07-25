This is the repository for the new HAProxy charm supporting HAProxy v2.8 and published in the [2.8/edge](https://charmhub.io/haproxy?channel=2.8/edge) channel. For the legacy charm in the [latest/edge](https://charmhub.io/haproxy?channel=latest/edge) channel please refer to the [legacy/main](https://github.com/canonical/haproxy-operator/tree/legacy/main) branch.

# Overview

A Juju charm that deploys and manages HAProxy on machine. HAProxy is a TCP/HTTP reverse proxy which is particularly suited for high availability environments. It features connection persistence through HTTP cookies, load balancing, header addition, modification, deletion both ways. It has request blocking capabilities and provides interface to display server status.

# Usage

Deploy the HAProxy charm and integrate it with a certificate provider charm
```
juju deploy haproxy --channel=2.8/edge
juju deploy self-signed-certificates
juju integrate haproxy self-signed-certificates
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
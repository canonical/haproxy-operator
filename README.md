# Overview

This charm provides means to deploy and operate haproxy - a reliable, high performance TCP and HTTP load balancer.

# Deploying

```
juju deploy <haproxy-charm-dir> -n 3
```

# TCP Load-balancing

This charm exposes an interface to provide TCP load-balancing for a backend application.

For example, [charm-cockroachdb](https://github.com/dshcherb/charm-cockroachdb) can expose its units for clients
to access them through the load-balancer.

# High Availability

Multiple units of haproxy can be used to provide load-balancer high-availability for
client access through a load-balancer.

Adding a virtual IP via keepalived is currently a work in progress.

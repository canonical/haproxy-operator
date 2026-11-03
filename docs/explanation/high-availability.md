(explanation_high_availability)=

# High availability

High availability (HA) is a characteristic of a system that aims to ensure an agreed level of operational performance, usually uptime, for a higher than normal period. In this document we discuss the high availability configuration supported by the HAProxy charm.

## Active/active

An active-active configuration consists of two or more HAProxy units that reply to incoming requests at the same time. Increasing the number of HAProxy charm units can be done either during deployment with the `-n` flag or by using the `juju add-unit` command:

```
juju add-unit haproxy -n 2
```

To configure a single entrypoint for all HAProxy charm units, we can employ a variety of methods, which includes but not limited to:

* Using a floating IP address
* DNS round-robin
* Using a load balancer

```{note}
Configuration of the entrypoint for the active-active configuration is outside of the scope of responsibility for the HAProxy charm.
```

### DNS round-robin

DNS round-robin provides a single entrypoint for all HAProxy charm units with no overhead, shifting the responsibility to the DNS server for load balancing purposes. However, most DNS solutions lack health checks of unhealthy hosts, as well as requiring configuration changes every time there’s a change in the number of HAProxy charm units or their IP addresses.

### Load balancing

Most of the time a load balancer will be configured with a health check monitor and a floating IP to ensure availability of backend hosts as well as retain control of the assigned external IP address. For an example using Octavia, see the [OpenStack documentation](https://docs.openstack.org/octavia/stein/user/guides/basic-cookbook.html#basic-lb-with-hm-and-fip).

```{note}
Sticky session should be configured explicitly at the load balancer level.
```

## Active/passive

An active-passive configuration consists of two or more nodes. In this configuration, only one unit is considered "active" at any given time. All other units are considered "passive", meaning they don't reply to incoming requests. The single entrypoint for all HAProxy charm units exists in the form of a virtual IP address. The `keepalived` subordinate charm is responsible for managing this virtual IP address, attaching it to the "active" HAProxy unit and moving it to a "passive" unit when the "active" unit goes down.

See {ref}`how_to_configure_high_availability` for a guide to this configuration.

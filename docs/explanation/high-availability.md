# High availability
High availability (HA) is a characteristic of a system that aims to ensure an agreed level of operational performance, usually uptime, for a higher than normal period. In this document we will discuss different possible configurations for high availability supported by the `hacluster` subordinate charm.

# Active/active
An active-active configuration consists of two or more HAProxy units that reply to incoming requests at the same time. Increasing the number of HAProxy charm units can be done either during deployment with the `-n` flag or by using the `juju add-unit` command: 
```
juju add-unit haproxy -n 2
```

To configure a single entrypoint for all HAProxy charm units, we can employ a variety of methods, which includes but not limited to:
* Using a floating IP address
* DNS round-robin
* Using a load balancer

> **_NOTE:_**: Configuration of the entrypoint for the active-active configuration is outside of the scope of responsibility for the HAProxy charm.

## DNS round-robin
DNS round-robin provides a single entrypoint for all HAProxy charm units with no overhead, shifting the responsibility to the DNS server for load balancing purposes. However, most DNS solutions lack health checks of unhealthy hosts, as well as requiring configuration changes every time there’s a change in the number of HAProxy charm units or their IP addresses.

## Load balancing
Most of the time a load balancer will be configured with a health check monitor and a floating IP to ensure availability of backend hosts as well as retain control of the assigned external IP address. For an example using Octavia, see the [OpenStack documentation](https://docs.openstack.org/octavia/stein/user/guides/basic-cookbook.html#basic-lb-with-hm-and-fip).

> **_NOTE:_**: Sticky session should be configured explicitly at the load balancer level.

# Active/passive
An active-passive configuration consists of two or more nodes. In this configuration, only one unit is considered "active" at any given time. All other units are considered "passive" meaning they don't reply to incoming requests. The single entrypoint for all HAProxy charm units exists in the form of a virtual IP address. The `hacluster` subordinate charm is responsible for managing this virtual IP address, attaching it to the "active" HAProxy unit and moving it to a "passive" unit when the "active" unit goes down.

By default it is required to have at least three HAProxy units when using the `hacluster` subordinate charm to maintain a quorum. However, this number can be configured. See the next section on active/passive cluster configuration for more details.

## Active/passive cluster configuration
The `hacluster` charm provide operators with configuration options to fine-tune the cluster's behavior. Below are some key settings for HAProxy.

### Cluster count configuration
The [`cluster_count`](https://opendev.org/openstack/charm-hacluster/src/commit/2449932bf7c618fda4fa412228a133688db13b02/config.yaml#L125) configuration adjusts the number of peer units required to bootstrap cluster services.

### Quorum policy configuration
The [`no_quorum_policy`](https://opendev.org/openstack/charm-hacluster/src/commit/2449932bf7c618fda4fa412228a133688db13b02/config.yaml#L221) configuration determines the quorum policy. Allowed values are:

* ignore: continue all resource management.
* freeze: continue resource management, but don’t recover resources from nodes not in the affected partition.
* stop: stop all resources in the affected cluster partition.
* suicide: fence all nodes in the affected cluster partition.

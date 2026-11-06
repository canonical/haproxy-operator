(how_to_configure_high_availability)=

# Configure high-availability

High availability (HA) allows the HAProxy charm to continue to function even if some units fail, while maintaining the same address across all units. This guide walks you through how to configure HA with the help of the `keepalived` subordinate charm.

## Scale the HAProxy charm to three units

Deploy the HAProxy charm with three units.

```
juju deploy haproxy --channel=3.2/edge -n 3
```

## Deploy and integrate the `keepalived` subordinate charm

Deploy the subordinate charm and integrate it with the HAProxy charm. Because `keepalived` is a subordinate charm, Juju deploys it alongside each HAProxy unit.

```
juju deploy keepalived --channel=latest/edge
juju integrate haproxy:juju-info keepalived:juju-info
```

## Configure a virtual IP

A virtual IP is shared between all HAProxy units and serves as the single entrypoint to all requirer applications. To add a virtual IP to the HAProxy deployment, use a free IP address from the network of the HAProxy units. This example takes the first available address on the LXD subnet.

```
VIP="$(echo "${HAPROXY_IP}" | awk -F'.' '{print $1,$2,$3,2}' OFS='.')"
juju config keepalived virtual_ip="${VIP}/24" port=80
```

Test our configuration by sending a request to the `$VIP`. You should see that the request is properly handled by HAProxy.

```
curl "${VIP}"
```

If successful, HAProxy will reply with `Default page for the haproxy operator.`.

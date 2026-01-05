(how_to_configure_high_availability)=

# Configure high-availability

High availability (HA) allows the HAProxy charm to continue to function even if some units fails, while maintaining the same address across all units. This guide walks you through how to configure HA with the help of the `hacluster` subordinate charm.

## Scale the HAProxy charm to three units

We'll start by scaling the HAProxy charm to three units as it's the minimum required by the `hacluster` charm.

```
juju add-unit haproxy -n 3
```

## Deploy and integrate the `hacluster` subordinate charm

Deploy the subordinate charm, and specify `--base=ubuntu@24.04` so that the charm is deployed with a base matching the HAProxy charm.

```
juju deploy hacluster --channel=2.4/edge --base=ubuntu@24.04
juju integrate hacluster haproxy
```

## Configure a virtual IP (vip)

A virtual IP is shared between all HAProxy units and serves as the single entrypoint to all requirer applications. To add a virtual IP to the HAProxy charm we take a free IP address from the network of the HAProxy units. In this example we take the first available address on the LXD subnet.

```
VIP="$(echo "${HAPROXY_IP}" | awk -F'.' '{print $1,$2,$3,2}' OFS='.')"
juju config haproxy vip=$VIP
```

Performing the same request as before, let's replace `$HAPROXY_IP` with `$VIP`. We should see that the request is properly routed to the requirer.

```
curl -H "Host: $HAPROXY_HOSTNAME" "${VIP}" -L --insecure --resolve "$HAPROXY_HOSTNAME:443:$VIP"
```

If successful, the terminal will respond with `ok!`.

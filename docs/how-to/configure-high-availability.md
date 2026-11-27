(how_to_configure_high_availability)=

# Configure high-availability

High availability (HA) allows the HAProxy charm to continue to function even if some units fail, while maintaining the same address across all units. The charm installs `keepalived` on each unit to support active-passive high availability.

## Scale the HAProxy charm to three units

Deploy the HAProxy charm with three units.

```
juju deploy haproxy --channel=3.2/edge -n 3
```

```{note}
Virtual IP management is not yet implemented. This guide will be updated once
the charm can configure the virtual IP directly.
```

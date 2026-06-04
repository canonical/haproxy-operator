(explanation_charm_architecture)=

# Charm architecture

HAProxy is a TCP/HTTP reverse proxy which is particularly suited for high availability environments. It features connection persistence through HTTP cookies, load balancing, header addition, modification, deletion both ways. It has request blocking capabilities and provides interface to display server status.

The HAProxy charm repository is a collection of charms and snaps that manages the deployment and operation of HAProxy:
1. `haproxy`: A machine charm managing HAproxy. See the [haproxy README](haproxy-operator/README.md) for more information.
2. `haproxy-spoe-auth-operator`: A machine charm deploying an SPOE agent that serves as an authentication proxy. See the [haproxy-spoe-auth-operator README](haproxy-spoe-auth-operator/README.md) for more information.
3. `haproxy-route-policy-operator`: A machine charm deploying the `haproxy-route-policy` application for controlling the data from different `haproxy-route` relations. See the [haproxy-route-policy-operator README](haproxy-route-policy-operator/README.md) for more information.

The repository also contains the snapped workload of some charms:
1. `haproxy-spoe-auth-snap`: A snap of the SPOE agent made for the haproxy-spoe-auth-operator charm. See the [haproxy-spoe-auth-snap README](haproxy-spoe-auth-snap/README.md) for more information.
2. `haproxy-route-policy-snap`: A snap of the `haproxy-route-policy` app made for the `haproxy-route-policy-operator` charm. See the [haproxy-route-policy-snap README](haproxy-route-policy/README.md) for more information.

## Charm architecture diagram

.. mermaid::

    C4Component
    title Component diagram for HAProxy Charm

    Container_Boundary(haproxy, "Haproxy charm monorepo") {
    Container_Boundary("haproxy_charm", "HAProxy") {
        Component(charm, "Haproxy charm")
    }
    Container_Boundary("spoe", "SPOE-auth") {
        Component(spoe_auth, "SPOE-auth charm")
        Component(spoe_auth_snap, "SPOE-auth snap")
    }
    Container_Boundary("ddos", "ddos-configurator") {
        Component(ddos, "ddos-configurator charm")
    }
    Container_Boundary("haproxy_route_policy", "haproxy-route-policy") {
        Component(haproxy_route_policy, "haproxy-route-policy charm")
        Component(haproxy_route_policy_snap, "haproxy-route-policy snap")
    }
    }

## Integrations

See the Integrations section on each of the component's Charmhub page for more details:
1. (Integrations for haproxy-operator)[https://charmhub.io/haproxy/integrations?channel=2.8/edge]
2. (Integrations for haproxy-spoe-auth-operator)[https://charmhub.io/haproxy-spoe-auth/integrations?channel=latest/edge]
3. (Integrations for haproxy-route-policy-operator)[https://charmhub.io/haproxy-route-policy/integrations?channel=latest/edge]

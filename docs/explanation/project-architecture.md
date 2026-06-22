---
myst:
  html_meta:
    "description lang=en": "Architecture overview of the HAProxy project, its components, and how they work together to provide a TCP/HTTP reverse proxy solution."
---

(explanation_project_architecture)=

# Project architecture

HAProxy is a TCP/HTTP reverse proxy which is particularly suited for high availability environments. It features connection persistence through HTTP cookies, load balancing, header addition, modification, deletion both ways. It has request blocking capabilities and provides interface to display server status.

The HAProxy charm repository is a collection of charms and snaps that manages the deployment and operation of HAProxy:

1. `haproxy`: A machine charm managing HAProxy. See the [`haproxy` README](https://github.com/canonical/haproxy-operator/tree/main/haproxy-operator) for more information.
2. `haproxy-spoe-auth-operator`: A machine charm deploying an SPOE agent that serves as an authentication proxy. See the [`haproxy-spoe-auth-operator` README](https://github.com/canonical/haproxy-operator/tree/main/haproxy-spoe-auth-operator) for more information.
3. `haproxy-route-policy-operator`: A machine charm deploying the `haproxy-route-policy` application for controlling the data from different `haproxy-route` relations. See the [`haproxy-route-policy-operator` README](https://github.com/canonical/haproxy-operator/tree/main/haproxy-route-policy-operator) for more information.

The repository also contains the snapped workload of some charms:

1. `haproxy-spoe-auth-snap`: A snap of the SPOE agent made for the haproxy-spoe-auth-operator charm. See the [haproxy-spoe-auth-snap README](https://github.com/canonical/haproxy-operator/tree/main/haproxy-spoe-auth-snap) for more information.
2. `haproxy-route-policy-snap`: A snap of the `haproxy-route-policy` app made for the `haproxy-route-policy-operator` charm. See the [haproxy-route-policy-snap README](https://github.com/canonical/haproxy-operator/tree/main/haproxy-route-policy) for more information.

## High-level overview of deployment

```{mermaid}
C4Component
title Component diagram for HAProxy Charm

Container_Boundary(haproxy, "HAProxy deployment") {
    Container_Boundary(haproxy_charm, "HAProxy") {
        Component(charm, "HAProxy charm")
    }
    Container_Boundary(spoe, "SPOE-auth") {
        Component(spoe_auth, "SPOE-auth charm")
        Component(spoe_auth_snap, "SPOE-auth snap")
    }
    Container_Boundary(ddos_boundary, "ddos-configurator") {
        Component(ddos_charm, "ddos-configurator charm")
    }
    Container_Boundary(haproxy_route_policy, "haproxy-route-policy") {
        Component(haproxy_route_policy_charm, "haproxy-route-policy charm")
        Component(haproxy_route_policy_snap, "haproxy-route-policy snap")
    }
}

Rel(charm, spoe_auth, "SPOE protocol", "Authentication offload")
Rel(haproxy_route_policy_charm, charm, "haproxy-route-policy", "Route approval")
Rel(charm, ddos_charm, "ddos-protection", "DDoS protection (optional)")
Rel(spoe_auth, spoe_auth_snap, "Manages")
Rel(haproxy_route_policy_charm, haproxy_route_policy_snap, "Manages")

UpdateRelStyle(haproxy_route_policy_charm, charm, $offsetY="-60", $offsetX="-130")
UpdateRelStyle(charm, spoe_auth, $offsetY="10", $offsetX="-50")
UpdateRelStyle(charm, ddos_charm, $offsetY="10", $offsetX="-50")
UpdateRelStyle(spoe_auth, spoe_auth_snap, $offsetX="10")
UpdateRelStyle(haproxy_route_policy_charm, haproxy_route_policy_snap, $offsetX="10")
```

The `haproxy` charm is the central component, responsible for configuring and running the HAProxy reverse proxy on machine. It receives routing information from related applications via `haproxy-route` (HTTP) and `haproxy-route-tcp` (TCP) relations and generates the appropriate HAProxy configuration.

The `haproxy` charm can be deployed with the `haproxy-spoe-auth-operator` charm to add an authentication layer via a Stream Processing Offload Engine (SPOE) agent packaged in `haproxy-spoe-auth-snap`. HAProxy delegates authentication decisions to this agent which is integrated with an OpenID Connect (OIDC) provider charm.

The `haproxy` charm can also be deployed with the `haproxy-route-policy-operator` charm to control which backends are permitted to be routed through `haproxy-route` relations. The workload of the `haproxy-route-policy-operator` charm is a Django application packaged as a snap. It evaluates incoming requests against configured rules and accepts or rejects them accordingly. It's deployed together with a PostgreSQL database.

The `haproxy` charm can optionally be deployed with the `haproxy-ddos-protection-configurator` charm to add advanced DDoS protection via the `ddos-protection` interface. This charm provides rate limiting, connection blocking, and timeout customisation to help protect services against distributed denial-of-service attacks.

## Integrations

The `haproxy` charm integrates with backend application charms via `haproxy-route` (HTTP) and `haproxy-route-tcp` (TCP) relations — these are required for a basic reverse proxy deployment. Optionally, the `haproxy-spoe-auth-operator` can be integrated to add OIDC authentication, the `haproxy-route-policy-operator` to enforce route approval policies, and the `haproxy-ddos-protection-configurator` to enable DDoS protection. The optional integrations all connect back to the central `haproxy` charm.

See the Integrations section on each of the component's Charmhub page for more details:

1. [Integrations for `haproxy`](https://charmhub.io/haproxy/integrations?channel=2.8/edge)
2. [Integrations for `haproxy-spoe-auth-operator`](https://charmhub.io/haproxy-spoe-auth/integrations?channel=latest/edge)
3. [Integrations for `haproxy-route-policy-operator`](https://charmhub.io/haproxy-route-policy/integrations?channel=latest/edge)
4. [Integrations for `haproxy-ddos-protection-configurator`](https://charmhub.io/haproxy-ddos-protection-configurator/integrations)

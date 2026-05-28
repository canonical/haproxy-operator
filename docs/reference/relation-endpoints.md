---
myst:
  html_meta:
    "description lang=en": "Reference documentation for all relation endpoints supported by the HAProxy charm."
---

(reference_relation_endpoints)=

# Relation endpoints

This page lists all relation endpoints exposed by the HAProxy charm, grouped by role.

## Provides

### `haproxy-route`

- **Interface**: `haproxy-route`
- **Supported charms**: Any charm implementing the `haproxy-route` interface

Allows HTTP-based backend charms to register themselves with HAProxy, configuring hosts, paths, ports, load-balancing, health checks, and rewrite rules.

Example `haproxy-route` integrate command:

```shell
juju integrate <charm>:haproxy-route haproxy:haproxy-route
```

---

### `haproxy-route-tcp`

- **Interface**: `haproxy-route-tcp`
- **Supported charms**: Any charm implementing the `haproxy-route-tcp` interface

Allows TCP-based backend charms to register themselves with HAProxy using SNI-based routing, with support for TLS termination and health checks.

Example `haproxy-route-tcp` integrate command:

```shell
juju integrate <charm>:haproxy-route-tcp haproxy:haproxy-route-tcp
```

---

### `ingress`

- **Interface**: `ingress`
- **Supported charms**: Any charm implementing the traefik-compatible `ingress` interface

Exposes per-application ingress to charms that use the traefik-compatible `ingress` interface, load-balancing traffic across all units of the application.

Example `ingress` integrate command:

```shell
juju integrate <charm>:ingress haproxy:ingress
```

---

### `ingress-per-unit`

- **Interface**: `ingress_per_unit`
- **Supported charms**: Any charm implementing the traefik-compatible `ingress-per-unit` interface

Provides a dedicated ingress URL per unit, rather than per application, for charms that use the traefik-compatible `ingress-per-unit` interface.

Example `ingress-per-unit` integrate command:

```shell
juju integrate <charm>:ingress-per-unit haproxy:ingress-per-unit
```

---

### `website`

- **Interface**: `http`
- **Supported charms**: Any charm implementing the `http` interface

Legacy interface that exposes HAProxy as an HTTP endpoint to other charms expecting a reverse proxy. Prefer `haproxy-route` for new integrations.

Example `website` integrate command:

```shell
juju integrate <charm>:reverseproxy haproxy:website
```

---

### `cos-agent`

- **Interface**: `cos_agent`
- **Supported charms**: [grafana-agent](https://charmhub.io/grafana-agent)

Integrates HAProxy with the Canonical Observability Stack, enabling metrics and log collection via the Grafana Agent.

Example `cos-agent` integrate command:

```shell
juju integrate grafana-agent:juju-info haproxy:cos-agent
```

---

## Requires

### `certificates`

- **Interface**: `tls-certificates`
- **Supported charms**: [self-signed-certificates](https://charmhub.io/self-signed-certificates), [manual-tls-certificates](https://charmhub.io/manual-tls-certificates)

Requests TLS certificates from a certificate authority charm so HAProxy can serve HTTPS frontends.

Example `certificates` integrate command:

```shell
juju integrate haproxy:certificates self-signed-certificates:certificates
```

---

### `reverseproxy`

- **Interface**: `http`
- **Supported charms**: Any charm implementing the `http` interface

Legacy interface allowing backend charms to register themselves as reverse proxy targets. Prefer `haproxy-route` for new integrations.

Example `reverseproxy` integrate command:

```shell
juju integrate haproxy:reverseproxy <charm>:website
```

---

### `ha`

- **Interface**: `hacluster`
- **Supported charms**: [hacluster](https://charmhub.io/hacluster)

Integrates with the `hacluster` charm to enable active/passive high-availability using a shared virtual IP address.

Example `ha` integrate command:

```shell
juju integrate haproxy:ha hacluster:ha
```

---

### `receive-ca-certs`

- **Interface**: `certificate_transfer`
- **Supported charms**: Any charm implementing the `certificate_transfer` interface

Receives CA certificates from another charm so HAProxy can trust custom certificate authorities when connecting to backends.

Example `receive-ca-certs` integrate command:

```shell
juju integrate haproxy:receive-ca-certs <charm>:send-ca-cert
```

---

### `spoe-auth`

- **Interface**: `spoe-auth`
- **Supported charms**: [haproxy-spoe-auth](https://charmhub.io/haproxy-spoe-auth)

Delegates request authentication to an external SPOE agent using OpenID Connect. See {ref}`reference_spoe-auth_support` for details.

Example `spoe-auth` integrate command:

```shell
juju integrate haproxy:spoe-auth haproxy-spoe-auth:spoe-auth
```

---

### `ddos-protection`

- **Interface**: `ddos_protection`
- **Supported charms**: [haproxy-ddos-protection-configurator](https://charmhub.io/haproxy-ddos-protection-configurator)

Receives DDoS protection policy settings — including rate limits, connection limits, and timeouts — from an external configurator charm.

Example `ddos-protection` integrate command:

```shell
juju integrate haproxy:ddos-protection haproxy-ddos-protection-configurator:ddos-protection
```

---

### `haproxy-route-policy`

- **Interface**: `haproxy-route-policy`
- **Supported charms**: [haproxy-route-policy](https://charmhub.io/haproxy-route-policy)

Receives approved routing policy rules from an external policy operator, controlling which backend route requests are permitted.

Example `haproxy-route-policy` integrate command:

```shell
juju integrate haproxy:haproxy-route-policy haproxy-route-policy:haproxy-route-policy
```

---

## Peers

### `haproxy-peers`

- **Interface**: `haproxy-peers`
- **Supported charms**: Internal peer relation, no external charms

Used by HAProxy units to coordinate state with each other, required for correct behaviour when multiple units are deployed.

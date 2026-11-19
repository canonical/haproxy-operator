---
myst:
  html_meta:
    "description lang=en": "Required CPU, memory, disk, software versions, and network access for an HAProxy deployment."
---

(reference_resource_requirements)=

# Resource requirements

This page describes the resources and software versions required to deploy the
HAProxy charm on machines.

HAProxy is an event-driven reverse proxy with a small baseline footprint.
Actual resource usage grows with the number of concurrent connections, TLS
handshakes, request rate, enabled integrations, and log volume. Use the values
in this page as a starting point, then monitor your deployment and adjust the
Juju constraints as needed.

The charm is a machine charm for IaaS and virtual machines. It is not supported
on Kubernetes.

## Machine requirements

Each HAProxy unit runs on its own machine and has the following resource
requirements:

| Resource  | Minimum     | Recommended |
| --------- | ----------- | ----------- |
| CPU       | 1 vCPU      | 2 vCPU      |
| Memory    | 2 GiB       | 4 GiB       |
| Root disk | 10 GiB      | 25 GiB      |

The minimum values cover Ubuntu, the Juju agent, the charm, and HAProxy with the
default configuration and light traffic. The recommended values provide
headroom for production traffic, TLS termination, DDoS protection, SPOE
authentication, and route policies.

The root disk holds the operating system, the Juju agent, the installed
packages, TLS certificates, and logs. HAProxy logs rotate daily or when they
exceed 1 GiB, and up to seven rotated logs are retained per unit. Size the disk
according to the expected log volume.

You can set the resources for a deployment with Juju constraints. For example:

```sh
juju deploy haproxy --channel=3.2/edge \
  --constraints="cores=2 mem=4G root-disk=25G"
```

Memory usage increases with the number of concurrent connections. If you raise
the `global-maxconn` configuration option or expect a high connection rate,
provision additional memory.

## Software versions

The HAProxy charm requires the following software:

| Component                                | Requirement                                             |
| ---------------------------------------- | ------------------------------------------------------- |
| Juju                                     | 3.3 or later (3.6 or later is recommended)              |
| Ubuntu                                   | 26.04 LTS                                               |
| HAProxy                                  | 3.2, installed from the Ubuntu archive and pinned       |
| Terraform (optional, for IaC deployments) | 1.6 or later with the Juju provider 1.0 or later        |

The charm installs HAProxy and its dependencies. You don't need to install
HAProxy or a Python runtime on the target machine yourself.

## Supported architectures

The charm is published for the following architectures:

- `amd64`
- `arm64`

## Network access

An HAProxy deployment requires the following network access:

- Inbound TCP port 80 for HTTP traffic and TCP port 443 for HTTPS traffic.
- Inbound TCP port 8404 for the Prometheus metrics endpoint, if metrics
  scraping is enabled.
- Inbound TCP ports for any additional frontend ports configured through the
  `haproxy-route`, `haproxy-route-tcp`, or ingress relations.
- Outbound access to the backend applications that HAProxy proxies.
- Access to the Juju API for the deployed units.

If you use the `keepalived` subordinate charm for active/passive high
availability, allow VRRP traffic (IP protocol 112) between the HAProxy units.

## High availability

When you deploy multiple units for high availability, provision the required
resources for every unit, because each unit can serve traffic or become the
active unit. Subordinate charms share the machine with the HAProxy unit and add
a small amount of CPU and memory overhead.

For more information, see {ref}`High availability <explanation_high_availability>`.

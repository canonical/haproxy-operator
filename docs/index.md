---
myst:
  html_meta:
    "description lang=en": "A Juju charm deploying and managing HAProxy."
---
# HAProxy operator

The HAProxy operator is an open-source software operator that deploys and operates HAProxy on Juju 3.3 and above.

The charm provides a managed ingress entry point for backend applications, handling secure traffic routing and load balancing. It also offers advanced features such as TLS, monitoring and high-availability. This operator is built for **IaaS/VM** and is not supported in **Kubernetes** environments.

## In this documentation

```{list-table}
   :header-rows: 1
   :widths: 10 20

* - 
  - 
* - **Get started**
  - {ref}`tutorial_getting_started`
* - **Deployment**
  - {ref}`Configure high availability <how_to_configure_high_availability>` • {ref}`Control backend routing <how_to_control_haproxy_route_relation_data>` • {ref}`Create OpenStack virtual IP <how_to_configure_virtual_ip_on_openstack>`
* - **Integrations**
  - {ref}`Relation endpoints <reference_relation_endpoints>` • {ref}`Integrate with non-charmed workloads <how_to_integrate_with_non_charm_workload>` • {ref}`Configure ingress requirers <how_to_provide_extra_configurations_for_ingress_requirer_charms>`
* - **Supported protocols** 
  - {ref}`FTP <how_to_loadbalancing_for_an_ftp_server>` • {ref}`gRPC <how_to_loadbalancing_for_a_grpc_server>` • {ref}`HTTP/2 <reference_http2_support>`
* - **Security**
  - {ref}`Overview <explanation_security>` • {ref}`Enable DDoS protection <how_to_enable_ddos_protection>` • {ref}`Protect a hostname <how_to_protect_hostname_spoe_auth>`
```

## How this documentation is organized

This documentation uses the
[Diátaxis documentation structure](https://diataxis.fr/).

* The {ref}`Tutorial <tutorial_index>` takes you step-by-step through a basic deployment of the HAProxy charm.
* The {ref}`How-to guides <how_to_index>` cover practical tasks for configuring, integrating, and maintaining your HAProxy deployment.
* {ref}`Reference <reference_index>` provides technical details on supported server protocols and authentication.
* {ref}`Explanation <explanation_index>` includes context and overviews on security and high availability.

## Project and community

The HAProxy operator is a member of the Ubuntu family. It's an open-source project that warmly welcomes community 
projects, contributions, suggestions, fixes, and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/docs/ethos/code-of-conduct)
- [File a bug](https://github.com/canonical/haproxy-operator/issues)
- Get support through the [Discourse forum](https://discourse.charmhub.io/)
- Join our [online chat](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
- {ref}`Contribute <how_to_contribute>`

Thinking about using the HAProxy operator for your next project? 
[Get in touch](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)!

```{toctree}
:hidden:
:maxdepth: 1
Tutorial <tutorial/index.md>
How-to guides <how-to/index.md>
Reference <reference/index.md>
Explanation <explanation/index.md>
```

```{toctree}
:hidden:
:maxdepth: 1
Release notes <release-notes/index.md>
```

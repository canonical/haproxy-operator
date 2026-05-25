---
myst:
  html_meta:
    "description lang=en": "A Juju charm deploying and managing HAProxy."
---
# HAProxy operator

The HAProxy operator is an open-source software operator that deploys and operates HAProxy on Juju 3.3 and above.

The charm provides a managed ingress entry point for backend applications, handling secure traffic routing and load balancing. It also offers advanced features such as TLS, monitoring and high-availability. This operator is built for **IaaS/VM** and is not supported in **Kubernetes** environments.

This charm provides infrastructure operators and DevOps engineers straightforward deployment and operation of HAProxy.

## In this documentation

### Basics 

* **Tutorial**: {ref}`tutorial_getting_started` 

### Understanding the HAProxy charm

* **Server protocols**: {ref}`reference_http2_support` • {ref}`tutorial_loadbalancing_for_an_ftp_server` • {ref}`tutorial_loadbalancing_for_a_grpc_server` • {ref}`reference_grpc_support` 
* **Configuring and integrating**: {ref}`Provide extra configuration to ingress requirers <how_to_provide_extra_configurations_for_ingress_requirer_charms>` • {ref}`Configure a virtual IP on OpenStack <how_to_configure_virtual_ip_on_openstack>` • {ref}`Integrate with non-charmed workloads <how_to_integrate_with_non_charm_workload>`

### Security and performance

* **Security**: {ref}`Overview <explanation_security>` • {ref}`how_to_enable_ddos_protection`
* **SPOE authentication**: {ref}`reference_spoe-auth_support` • {ref}`Protect a hostname using OpenID Connect <how_to_protect_hostname_spoe_auth>`
* **High availability**: {ref}`explanation_high_availability` • {ref}`how_to_configure_high_availability`

## How this documentation is organized

This documentation uses the
[Diátaxis documentation structure](https://diataxis.fr/).

* The {ref}`Tutorial <tutorial_index>` takes you step-by-step through a basic deployment of the HAProxy charm, and there are advanced tutorials covering load balancing for different server protocols.
* The {ref}`How-to guides <how_to_index>` assume you have basic familiarity with the HAProxy charm. They cover practical tasks such as configuring, integrating, and upgrading your HAProxy deployment.
* {ref}`Reference <reference_index>` provides technical details on supported server protocols and authentication.
* {ref}`Explanation <explanation_index>` includes context and overviews on security and high availability.

## Project and community

The HAProxy operator is a member of the Ubuntu family. It's an open-source project that warmly welcomes community 
projects, contributions, suggestions, fixes, and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/code-of-conduct)
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

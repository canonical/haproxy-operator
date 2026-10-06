---
myst:
  html_meta:
    "description lang=en": "How-to guides covering the HAProxy charm operations lifecycle."
---

(how_to_index)=

# How-to guides

Manage the full operations lifecycle of the HAProxy charm, from initial traffic routing and protocol configuration through high-availability scaling and security hardening. Each guide assumes that you have already deployed the charm with Juju.

## Ingress and routing

HAProxy routes traffic to charmed applications as well as external workloads. Route behavior and backend approval policies can be customized through dedicated integrator charms.

* {ref}`Integrate with non-charm workloads <how_to_integrate_with_non_charm_workload>`: Route HTTP and TCP traffic to external services running outside Juju using the `ingress-configurator` charm.
* {ref}`Provide extra configuration to ingress requirers <how_to_provide_extra_configurations_for_ingress_requirer_charms>`: Extend standard `ingress` relations with advanced `haproxy-route` features such as path rewrites and custom hostnames.
* {ref}`Control haproxy-route relation data with the policy charm <how_to_control_haproxy_route_relation_data>`: Restrict and approve backend routes dynamically using the `haproxy-route-policy` REST API.

## Protocol load balancing

Workloads requiring protocols beyond standard HTTP requires more advanced configurations. The HAProxy charm can provide gRPC load balancing over HTTP/2 and routes TCP traffic to a range of backend ports for services like FTP.

* {ref}`Provide load balancing for a gRPC server <how_to_loadbalancing_for_a_grpc_server>`: Configure Layer-7 load balancing and ALPN negotiation for gRPC services.
* {ref}`Provide load balancing for an FTP server <how_to_loadbalancing_for_an_ftp_server>`: Configure Layer-4 TCP frontends and port ranges for passive FTP and FTPS traffic.

## Security

Production deployments require defense against malicious traffic, identity verification, and encrypted communication. Built-in integrations protect frontends and ensure privacy compliance.

* {ref}`Enable DDoS Protection <how_to_enable_ddos_protection>`: Integrate the DDoS protection configurator charm to mitigate volumetric and rate-based abuse.
* {ref}`Protect a hostname using OpenID Connect <how_to_protect_hostname_spoe_auth>`: Enforce user authentication for proxied routes via the `haproxy-spoe-auth` integration.
* {ref}`Configure the backend protocol <how_to_configure_backend_protocol>`: Establish secure HTTPS connections between HAProxy and backend applications using CA certificates.
* {ref}`Use self-signed certificates <how_to_use_self_signed_certificates>`: Generate and apply TLS certificates for testing and internal transport security.
* {ref}`Hash client IP addresses in logs <how_to_hash_client_ip_addresses_in_logs>`: Anonymize client IP addresses in access logs using cryptographic salting for privacy compliance.

## High availability

Clustered deployments ensure uninterrupted traffic handling during unit failures or maintenance. A shared virtual IP coordinates traffic distribution and automatic recovery across units.

* {ref}`Configure high availability <how_to_configure_high_availability>`: Deploy the `hacluster` subordinate charm to establish a shared virtual IP across multiple HAProxy units.
* {ref}`Configure virtual IP on OpenStack <how_to_configure_virtual_ip_on_openstack>`: Allocate an OpenStack VIP port and configure allowed address pairs for traffic routing.

## Operations and maintenance

Automated deployment workflows, version upgrades, and development tooling keep the HAProxy operator aligned with infrastructure requirements and community standards.

* {ref}`Add to existing Terraform project <how-to-deploy-with-terraform>`: Define and provision the HAProxy charm and its integrations using Terraform.
* {ref}`Upgrade <how_to_upgrade>`: Update the HAProxy charm to a newer revision or track with minimal operational disruption.
* {ref}`Contribute <how_to_contribute>`: Set up a development environment to build the charm, run tests, and submit improvements.

```{toctree}
:hidden:

Integrate with non-charm workloads <integrate-with-non-charm-workload.md>
Provide extra configurations for ingress requirer charms <provide-extra-configurations-for-ingress-requirer-charms.md>
Control haproxy-route relation data <control-haproxy-route-relation-data.md>
Provide load balancing for a gRPC server <loadbalancing-for-a-grpc-server.md>
Provide load balancing for an FTP server <loadbalancing-for-an-ftp-server.md>
Enable DDoS Protection <enable-ddos-protection.md>
Protect a hostname using OpenID Connect <protect-hostname-spoe-auth.md>
Configure the backend protocol <configure-backend-protocol.md>
Use self-signed certificates <use-self-signed-certificates.md>
Hash client IP addresses in logs <hash-client-ip-addresses-in-logs.md>
Configure high availability <configure-high-availability.md>
Configure virtual IP on OpenStack <configure-virtual-ip-on-openstack.md>
Add to existing Terraform project <deploy-with-terraform.md>
Upgrade <upgrade.md>
Contribute <contribute.rst>
```

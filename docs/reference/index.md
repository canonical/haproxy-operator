---
myst:
  html_meta:
    "description lang=en": "Technical information related to the HAProxy charm."
---

(reference_index)=

# Reference

Technical specifications, protocol capabilities, and interface definitions for the HAProxy charm. These references provide look-up details for configuring relations, network protocols, and deployment automation.

## Protocols

This section covers the most common protocols supported by the HAProxy charm.

* [gRPC support](grpc-support.md): Specifications and limitations for proxying gRPC traffic over HTTPS and custom frontend ports.
* [HTTP/2 support](http2-support.md): ALPN protocol negotiation, independent frontend and backend version handling, and TLS requirements.
* [FTP support](ftp-support.md): Passive FTP, FTPS, and SFTP support mechanisms, port range architectures, and operational constraints.

## Integrations

This section discusses the relations supported between the HAProxy and its related charms, as well as the integration between HAProxy and an authentication proxy via Stream Processing Offload Engine (SPOE).

* [Relation endpoints](relation-endpoints.md): Comprehensive inventory of provided and required Juju relation endpoints, interfaces, and supported charms.
* [SPOE authentication](spoe-auth-support.md): Architectural details and constraints of the Stream Processing Offload Engine (SPOE) OpenID Connect integration.

## Deployment and release

Infrastructure-as-code definitions and changelog format.

* [Terraform module](terraform.md): Input variables, outputs, and integration parameters for the HAProxy Terraform deployment module.
* [Changelog](../changelog.md): Historical log of feature releases, bug fixes, breaking changes, and documentation updates across revisions.

```{toctree}
:hidden:

gRPC support <grpc-support.md>
HTTP/2 support <http2-support.md>
FTP support <ftp-support.md>
Relation endpoints <relation-endpoints.md>
SPOE authentication <spoe-auth-support.md>
Terraform module <terraform.md>
Changelog <../changelog.md>
```

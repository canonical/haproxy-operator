---
myst:
  html_meta:
    "description lang=en": "Reference for the terraform module of the HAProxy charm."
---

(reference_terraform)=

# Terraform module for the HAProxy charm

Terraform is an infrastructure as code tool to assist in deployment. The HAProxy charm provides a Terraform module for deployment. The auto-generated documentation is located at `terraform/product/README.md` in the repository, and documents the module, resources, inputs, and outputs.

The terraform module supports deploying HAProxy charm as a single unit, or with hacluster for High Availability. The `haproxy_ddos_protection_configurator` option can be used to provide the DDOS protection configuration to the HAProxy charm. The `haproxy_spoe_auth` option can be used to provide the SPOE authentication configuration to the HAProxy charm. The `oauth_external_idp_integrator` option can be used to provide the external IDP integration configuration to the HAProxy charm.

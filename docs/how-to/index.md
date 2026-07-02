---
myst:
  html_meta:
    "description lang=en": "How-to guides covering the HAProxy charm operations lifecycle."
---

(how_to_index)=

# How-to guides

Manage the full operations lifecycle of the HAProxy charm, from initial deployment through
production maintenance. Each guide assumes that you’ve already deployed the charm with Juju.

## Common use-cases

Once you've set up the HAProxy charm, you can take advantage of the built-in features and capabilities to customize the charm based on your specific needs and use case.

```{toctree}
:maxdepth: 1
Configure high availability <configure-high-availability.md>
Integrate with non-charm workloads <integrate-with-non-charm-workload.md>
Provide extra configurations for ingress requirer charms <provide-extra-configurations-for-ingress-requirer-charms.md>
Control haproxy-route relation data <control-haproxy-route-relation-data.md>
Configure virtual IP on OpenStack <configure-virtual-ip-on-openstack.md>
How to add HAProxy charm to existing Terraform project <deploy-with-terraform.md>
```

## Load balancing

Additional steps need to be performed to provide load balancing to your deployment
depending on your required server protocol.

```{toctree}
:maxdepth: 1
Provide load balancing for a gRPC server <loadbalancing-for-a-grpc-server.md>
Provide load balancing for an FTP server <loadbalancing-for-an-ftp-server.md>
```

## Security

The HAProxy charm comes with built-in configurations and integrations to secure your deployment
against vulnerabilities and attacks.

```{toctree}
:maxdepth: 1
Enable DDoS Protection <enable-ddos-protection.md>
Protect a hostname using OpenID Connect <protect-hostname-spoe-auth.md>
```

## Maintenance and development

Upgrades and community contributions ensure the HAProxy charm stays current
and benefits from ongoing improvements.

```{toctree}
:maxdepth: 1
Upgrade <upgrade.md>
Contribute <contribute.rst>
```

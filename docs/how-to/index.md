---
myst:
  html_meta:
    "description lang=en": "How-to guides covering the HAProxy charm operations lifecycle."
---

(how_to_index)=

# How-to guides

The following guides cover key processes and common tasks for managing and using the HAProxy charm.

## Common use-cases

Once you've set up the HAProxy charm, you can take advantage of the built-in features and capabilities to customize the charm based on your specific needs and use case.
```{toctree}
:maxdepth: 1
Integrate with non-charm workloads <integrate-with-non-charm-workload.md>
Provide extra configurations for ingress requirer charms <provide-extra-configurations-for-ingress-requirer-charms.md>
Protect a hostname using OpenID Connect <protect-hostname-spoe-auth.md>
Enable DDoS Protection <enable-ddos-protection.md>
Configure high availability <configure-high-availability.md>
```

## Platform-specific workflows

In some cases additional steps need to be performed on specific substrates to ensure that the charm is working as intended.
```{toctree}
:maxdepth: 1
Configure virtual IP on OpenStack <configure-virtual-ip-on-openstack.md>
```

## Maintenance

This section contains how-to guides for maintenance actions that you might need to take while operating the charm.
```{toctree}
:maxdepth: 1
Upgrade <upgrade.md>
```

## Development

This section contains how-to guides for developing the `haproxy` charm.
```{toctree}
:maxdepth: 1
Contribute <contribute.md>
```

# HAProxy operator

This repository provides a collection of operators related to HAproxy. For deployment, integration, and management guidance, see the official [HAProxy operator documentation](https://canonical.com/juju/docs/haproxy-charm/).

## Repository layout

```text
docs/                                      # HAProxy charm documentation source

haproxy-operator/                          # Juju charm: HAProxy reverse proxy and ingress provider

haproxy-ddos-protection-configurator/      # Juju charm: DDoS protection configuration provider for HAProxy

haproxy-route-policy-operator/             # Juju charm: route-policy API service for HAProxy route requests

haproxy-route-policy/                      # Snap workload: HAProxy Route Policy Django application

haproxy-spoe-auth-operator/                # Juju charm: HAProxy SPOE authentication agent
haproxy-spoe-auth-snap/                    # Snap workload: HAProxy SPOE authentication agent

terraform/                                 # Terraform modules for deploying the HAProxy charm

tests/                                     # Shared integration and spread tests
```

## Components

This repository contains the code for the following charms:

| Component | Path | Role |  |
| --- | --- | --- | --- |
| `haproxy` | [`haproxy-operator/`](haproxy-operator/README.md) | A machine charm managing HAproxy. See the [haproxy README](haproxy-operator/README.md) for more information. |  |
| `haproxy-ddos-protection-configurator` | [`haproxy-ddos-protection-configurator/`](haproxy-ddos-protection-configurator/README.md) | A [Juju](https://canonical.com/juju) [charm](https://documentation.ubuntu.com/juju/3.6/reference/charm/) that serves as a configurator for HAProxy to provide DDoS protection capabilities. |  |
| `haproxy-spoe-auth-operator` | [`haproxy-spoe-auth-operator/`](haproxy-spoe-auth-operator/README.md) | A machine charm deploying an SPOE agent that serves as an authentication proxy. See the [haproxy-spoe-auth-operator README](haproxy-spoe-auth-operator/README.md) for more information. |  |
| `haproxy-route-policy-operator` | [`haproxy-route-policy-operator/`](haproxy-route-policy-operator/README.md) | A machine charm deploying the `haproxy-route-policy` application for controlling the data from different `haproxy-route` relations. See the [haproxy-route-policy-operator README](haproxy-route-policy-operator/README.md) for more information. |  |

The repository also contains the snapped workload of some charms:

| Component | Path | Role | Related charm |
| --- | --- | --- | --- |
| `haproxy-spoe-auth` | [`haproxy-spoe-auth-snap/`](haproxy-spoe-auth-snap/README.md) | A snap of the SPOE agent made for the haproxy-spoe-auth-operator charm. See the [haproxy-spoe-auth-snap README](haproxy-spoe-auth-snap/README.md) for more information. | `haproxy-spoe-auth-operator` |
| `haproxy-route-policy` | [`haproxy-route-policy/`](haproxy-route-policy/README.md) | A snap of the `haproxy-route-policy` app made for the `haproxy-route-policy-operator` charm. See the [haproxy-route-policy-snap README](haproxy-route-policy/README.md) for more information. | `haproxy-route-policy-operator` |

### Charmhub and Snapcraft

| Name | Listing |
| --- | --- |
| `haproxy` | https://charmhub.io/haproxy |
| `haproxy-ddos-protection-configurator` | https://charmhub.io/haproxy-ddos-protection-configurator |
| `haproxy-route-policy` | https://charmhub.io/haproxy-route-policy |
| `haproxy-spoe-auth` | https://charmhub.io/haproxy-spoe-auth |
| `haproxy-route-policy` | https://snapcraft.io/haproxy-route-policy |
| `haproxy-spoe-auth` | https://snapcraft.io/haproxy-spoe-auth |

## Get started

For a step-by-step basic deployment, start with [`docs/tutorial/getting-started.md`](docs/tutorial/getting-started.md). That tutorial covers requirements, setting up a tutorial model, deploying the HAProxy charm, configuring TLS, deploying the backend application, cleaning up the environment, and next steps.

## Documentation

Our documentation is stored in the `docs` directory and
can be viewed at https://canonical.com/juju/docs/haproxy-charm/.
It is based on the Canonical Sphinx Stack and hosted on
[Read the Docs](https://about.readthedocs.com/). In structuring, the
documentation employs the [Diátaxis](https://diataxis.fr/) approach.

You may open a pull request with your documentation changes, or you can
[file a bug](https://github.com/canonical/haproxy-operator/issues) to
provide constructive feedback or suggestions.

To run the documentation locally before submitting your changes:

```bash
cd docs
make run
```

GitHub runs automatic checks on the documentation to verify spelling,
validate links and style guide compliance.

You can (and should) run the same checks locally:

```bash
make spelling
make linkcheck
make vale
make lint-md
```

## Project and community

The haproxy-operator project is a member of the Ubuntu family. It is an open source project that warmly welcomes community projects, contributions, suggestions, fixes and constructive feedback.

* [Code of conduct](https://ubuntu.com/community/code-of-conduct)
* [Get support](https://discourse.charmhub.io/)
* [Issues](https://github.com/canonical/haproxy-operator/issues)
* [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
* [Contribute](https://github.com/canonical/haproxy-operator/blob/main/CONTRIBUTING.md)


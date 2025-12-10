# HAProxy operator

This repository provides a collection of operators related to HAproxy

This repository contains the code for the following charms:
1. `haproxy`: A machine charm managing HAproxy. See the [haproxy README](haproxy-operator/README.md) for more information.
2. `haproxy-spoe-auth-operator`: A machine charm deploying an SPOE agent that serves as an authentication proxy. See the [haproxy-spoe-auth-operator README](haproxy-spoe-auth-operator/README.md) for more information.

The repository also contains the snapped workload of some charms:
1. `haproxy-spoe-auth-snap`: A snap of the SPOE agent made for the haproxy-spoe-auth-operator charm. See the [haproxy-spoe-auth-snap README](haproxy-spoe-auth-snap/README.md) for more information.

## Project and community

The haproxy-operator project is a member of the Ubuntu family. It is an open source project that warmly welcomes community projects, contributions, suggestions, fixes and constructive feedback.

* [Code of conduct](https://ubuntu.com/community/code-of-conduct)
* [Get support](https://discourse.charmhub.io/)
* [Issues](https://github.com/canonical/haproxy-operator/issues)
* [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
* [Contribute](https://github.com/canonical/haproxy-operator/blob/main/CONTRIBUTING.md)

## Documentation

Our documentation is stored in the `docs` directory.
It is based on the Canonical starter pack
and hosted on [Read the Docs](https://about.readthedocs.com/). In structuring,
the documentation employs the [Diátaxis](https://diataxis.fr/) approach.

You may open a pull request with your documentation changes, or you can
[file a bug](https://github.com/canonical/haproxy-operator/issues) to provide constructive feedback or suggestions.

To run the documentation locally before submitting your changes:

```bash
cd docs
make run
```

GitHub runs automatic checks on the documentation
to verify spelling, validate links and style guide compliance.

You can (and should) run the same checks locally:

```bash
make spelling
make linkcheck
make vale
make lint-md
```
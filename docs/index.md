---
myst:
  html_meta:
    "description lang=en": "A Juju charm deploying and managing HAProxy."
---
# HAProxy operator

The HAProxy operator is an open-source software operator that deploys and operates HAProxy IAAS/VM that functions on Juju 3.3 and above. The charm offers advanced features such as TLS, monitoring and high-availability. This operator is built for **IAAS/VM** and is not supported in **Kubernetes** environments.

## In this documentation

TBD

## How this documentation is organized

The documentation uses the
[Diátaxis documentation structure](https://diataxis.fr/).

* The {ref}`Tutorial <tutorial_index>` takes you step-by-step through a basic deployment of the HAProxy charm, and there are advanced tutorials covering load balancing for different server protocols.
* The {ref}`How-to guides <how_to_index>` assume you have basic familiarity with the HAProxy charm. They cover practical tasks such as configuring, integrating, and upgrading your HAProxy deployment.
* {ref}`Reference <reference_index>` provides technical details on supported server protocols and authentication.
* {ref}`Explanation <explanation_index>` includes context and overviews on security and high availability.

## Project and community

The HAProxy operator is a member of the Ubuntu family. It's an open-source project that warmly welcomes community 
projects, contributions, suggestions, fixes, and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/code-of-conduct)
- [Get support](https://discourse.charmhub.io/)
- [Join our online chat](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
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

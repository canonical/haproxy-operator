---
myst:
  html_meta:
    "description lang=en": "How-to guides covering the HAProxy charm operations lifecycle."
---

(tutorial_index)=

# Tutorials

This section contains a step-by-step guide to help you start exploring how to deploy and configure the HAProxy charm to provide ingress to a backend application.

```{toctree}
:hidden:
Overview <self>
```

## Getting started

This tutorial walks through the deployment of the HAProxy charm to provide HTTP load balancing to a basic web server charm.

```{toctree}
:glob:
:titlesonly:
Getting Started <getting-started.md>
```

## Protocol-specific setup

In these tutorials you will learn how to use HAProxy to provide loadbalancing for different protocols.

```{toctree}
:glob:
:titlesonly:
Loadbalancing for an FTP server <loadbalancing-for-an-ftp-server.md>
Loadbalancing for a gRPC server <loadbalancing-for-a-grpc-server.md>
```

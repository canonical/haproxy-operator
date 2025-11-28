# HAProxy SPOE Auth Operator

A Juju charm that deploys and manages HAProxy SPOE Auth on machines.

## Overview

HAProxy SPOE Auth is a Stream Processing Offload Engine (SPOE) agent for HAProxy that provides authentication capabilities. This charm simplifies the deployment and management of the agent.


## Usage

Deploy the charm:

```bash
juju deploy haproxy_spoe_auth_operator --channel=latest/edge --config hostname=auth.example.com
```

Integrate with an OAuth provider:

```bash
juju relate haproxy-spoe-auth oauth-provider
```

Integrate with haproxy
```bash
juju relate haproxy-spoe-auth haproxy
```

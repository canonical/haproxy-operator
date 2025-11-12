# HAProxy SPOE Auth Operator

A Juju charm that deploys and manages HAProxy SPOE Auth on machines.

## Overview

HAProxy SPOE Auth is a Stream Processing Offload Engine (SPOE) agent for HAProxy that provides authentication capabilities. This charm simplifies the deployment and management of the agent.

## Features

- **OAuth Authentication**: Support for OAuth-based authentication
- **Snap-based Deployment**: Uses the haproxy-spoe-auth snap for easy installation and updates
- **Configuration Management**: Automated configuration file management via Jinja2 templates

## Usage

Deploy the charm:

```bash
juju deploy ./haproxy_spoe_auth_operator
```

Configure the SPOE address:

```bash
juju config haproxy-spoe-auth spoe-address="127.0.0.1:3000"
```

Integrate with an OAuth provider:

```bash
juju integrate haproxy-spoe-auth oauth-provider
```

## Configuration

- `spoe-address`: Address for SPOE agent to listen on (default: "127.0.0.1:3000")

## Relations

- `oauth` (requires): OAuth authentication provider integration

## Development

This charm is part of the haproxy-operator monorepo.

### Testing

Run unit tests:
```bash
tox -e unit
```

Run integration tests:
```bash
tox -e integration
```

Run linting:
```bash
tox -e lint
```

## Project Information

- [Source Code](https://github.com/canonical/haproxy-operator)
- [Issue Tracker](https://github.com/canonical/haproxy-operator/issues)

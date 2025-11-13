# Haproxy SPOE Auth Snap

A snap package running an SPOE (Stream Processing Offload Engine) agent.
The agent can work with Haproxy to act as an authentication proxy for both LDAP and OIDC.

## Installation

```bash
sudo snap install haproxy-spoe-auth
```

## Configuration

The configuration file is located at:
```
/var/snap/haproxy-spoe-auth/current/config.yaml
```

Edit this file to customize your agent settings.


## Usage

The agent will run as a background service and handle authentication according to your configuration.

## Logs

View service logs with:
```bash
sudo snap logs haproxy-spoe-auth
```
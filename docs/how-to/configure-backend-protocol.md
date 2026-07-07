---
myst:
  html_meta:
    "description lang=en": "Learn about how to configure the backend protocol to use HTTPS for connections."
---

(how_to_configure_backend_protocol)=

# How to configure the backend protocol

By default, the HAProxy charm enforces HTTPS for connections from clients while communicating with backend applications over HTTP. In some scenarios, you may also want to use HTTPS as the communication protocol for connections between HAProxy and the backend applications.

To do so, HAProxy verifies the identity of the backend application against a set of trusted certificate authority (CA) certificates. These certificates are sent to the `haproxy` charm through the `receive-ca-certs` relation. Therefore, at least one `receive-ca-certs` relation is required before you can set the backend protocol to HTTPS.

This guide assumes that you have already deployed the `haproxy` charm and integrated it with a `haproxy-route` requirer. In this guide we use the [`ingress-configurator`](https://charmhub.io/ingress-configurator) charm as the requirer.

## Transfer the CA certificate of the backend application

Integrate the charm that provides the backend CA certificate with the `haproxy` charm through the `receive-ca-certs` relation. In this guide we use the `self-signed-certificates` charm as an example:

```sh
juju integrate haproxy:receive-ca-certs self-signed-certificates
```

Verify that the CA certificate has been transferred and written to the expected location on the HAProxy unit:

```sh
juju ssh haproxy/leader ls /var/lib/haproxy/cas
```

You should see the `cas.pem` file listed in the output.

## Configure the backend protocol

Set the `backend-protocol` configuration on the `ingress-configurator` charm to `https`:

```sh
juju config ingress-configurator backend-protocol=https
```

Once all charms have settled into an "Active" state, HAProxy establishes HTTPS connections to the backend application and verifies its identity using the transferred CA certificate.

## Verify the backend protocol

Send a request through HAProxy and confirm that you can still reach the backend application, and that the backend application is now terminating TLS.

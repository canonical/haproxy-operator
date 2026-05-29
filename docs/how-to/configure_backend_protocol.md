# How to configure the protocol for connections between the `haproxy` charm and the backend charm
In some scenarios, in addition to enforcing clients to connect to `HAproxy` via HTTPS, we can also set HTTPS as the communication protocol for connections between `HAproxy` and backend applications. 

The `haproxy` charm verifies the identity of the backend application by referring to a set of trusted internal certificate authorities (CAs) that are sent to the `haproxy` charm via the `certificates-transfer` relation. Therefore, establishing at least one `certificates-transfer` relation is required in order to set the backend protocol to `HTTPS`.

# Transfer the CA certificate of the backend application

Integrate the requirer charm with the `haproxy` charm via the `certificates-transfer` relation:
```bash
juju integrate haproxy:certificates-transfer requirer
```

Verify that the CA certificate has been correctly transferred and written to the correct location
```bash
juju ssh haproxy/leader ls /var/lib/haproxy/cas
```

Configure `backend-protocol`:
```bash
juju config ingress-configurator backend-protocol=https
```

Verify that you can reach the backend application and the backend application is the one terminating TLS.
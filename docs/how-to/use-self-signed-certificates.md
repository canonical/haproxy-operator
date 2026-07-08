(how_to_use_self_signed_certificates)=

# How to use self-signed certificates

If you need HAProxy to serve HTTPS content using a self-signed certificate,
there are two major ways depending on whether your use case requires a
general or specific certificate.

## Use a general self-signed certificate 

If your use case only requires a general self-signed certificate,
you can use the
[`self-signed-certificates` charm](https://charmhub.io/self-signed-certificates).

The self-signed-certificates charm will generate a self-signed CA inside the
charm and then use it to sign certificates for the HAProxy charm.

To use the self-signed-certificates charm with the HAProxy charm, simply deploy
the self-signed-certificates charm and integrate it with the HAProxy charm using
the `certificates` relation.

```
juju deploy haproxy --channel=2.8/stable
juju deploy pollen --channel=latest/edge
juju integrate haproxy:haproxy-route pollen

juju deploy self-signed-certificates
juju integrate self-signed-certificates haproxy:certificates
```

Verify HAProxy is using the self-signed certificates signed by the
self-signed-certificates charm.

```
juju config haproxy external-hostname=pollen.test
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
curl -k -v --resolve "pollen.test:443:$HAPROXY_IP" https://pollen.test
```

In the output, you should see the HAProxy charm is using the certificates signed
by the self-signed-certificates charm.

## Use a custom CA to sign certificates

If you wish to sign the certificates used by the HAProxy charm using a custom CA
you own, you can use the [`manual-tls-certificates`](https://charmhub.io/manual-tls-certificates) charm.

The HAProxy charm will generate a certificate signing request (CSR), which will be
transmitted to the `manual-tls-certificates` charm. Sign the
CSR with your own CA using the `get-outstanding-certificate-requests` and
`provide-certificate` actions of the `manual-tls-certificates` charm.

To use the
`manual-tls-certificates` charm with the HAProxy charm, deploy the
manual-tls-certificates charm and integrate it with the HAProxy charm using
the `certificates` relation.

```
juju deploy haproxy --channel=2.8/stable
juju deploy pollen --channel=latest/edge
juju integrate haproxy:haproxy-route pollen

juju deploy manual-tls-certificates
juju integrate manual-tls-certificates haproxy:certificates
```

Let's then create a test CA for signing certificates for the HAProxy charm.

```
mkdir certs
openssl genrsa -out certs/ca.key 2048
openssl req -new -x509 -days 3650 -key certs/ca.key -out certs/ca.crt -subj "/C=US/CN=ca.test"
```

Now sign the CSR of the HAProxy charm by first retrieving the CSR from the
manual-tls-certificates charm.

```
juju config haproxy external-hostname=pollen.test
juju run manual-tls-certificates/leader get-outstanding-certificate-requests --format=json \
  | jq -r '."manual-tls-certificates/0".results.result' \
  | jq -r '.[0].csr' > certs/client.csr
```

Then sign the CSR using the CA we created earlier, and provide the signed
certificate back to the `manual-tls-certificates` charm using the `provide-certificate` action.

```
openssl x509 -req -in certs/client.csr -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial -out certs/client.crt -days 365 -sha256
juju run manual-tls-certificates/leader provide-certificate \
  certificate="$(base64 -w0 certs/client.crt)" \
  ca-certificate="$(base64 -w0 certs/ca.crt)" \
  certificate-signing-request="$(base64 -w0 certs/client.csr)"
```

Verify HAProxy is using the certificates signed by the CA (`ca.test`) we created
earlier.

```
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
curl -k -vv --resolve "pollen.test:443:$HAPROXY_IP" https://pollen.test
```

In the output, you should see the HAProxy charm is using the custom CA:


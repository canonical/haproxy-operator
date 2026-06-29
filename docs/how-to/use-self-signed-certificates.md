# How to use self-signed certificates

If you wish HAProxy to serve HTTPS content using a self-signed certificate,
there are two major ways to do this.

## Use `self-signed-certificates` charm

If your use case only requires a general self-signed certificate, instead of a
specific self-signed certificate, you can use the
[`self-signed-certificates` charm](https://charmhub.io/self-signed-certificates).

The self-signed-certificates charm will generate a self-signed CA inside the
charm and then use it to sign certificates for the HAProxy charm. This is the
simplest way to set up self-signed certificates for the HAProxy charm.

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

And then verify HAProxy is using the self-signed certificates signed by the
self-signed-certificates charm.

```
juju config haproxy external-hostname=pollen.test
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
curl -k -v --resolve "pollen.test:443:$HAPROXY_IP" https://pollen.test
```

In the output, you should see the HAProxy charm is using the certificates signed
by the self-signed-certificates charm.

```
...
*   issuer: CN=self-signed-certificates-operator; x500UniqueIdentifier=e964420b-6ae9-4955-87f8-0a797ef5fd24
...
```

## Use `manual-tls-certificates` charm

If you wish to sign the certificates used by the HAProxy charm using a custom CA
you own, you can use the [`manual-tls-certificates`](https://charmhub.io/manual-tls-certificates) charm.

HAProxy charm will generate a CSR (certificate signing request), which will be
transmitted to the manual-tls-certificates charm. And then you can sign the
CSR using your own CA using the `get-outstanding-certificate-requests` and
`provide-certificate` actions of the manual-tls-certificates charm.

Similar to the `self-signed-certificates` charm, to use the
manual-tls-certificates charm with the HAProxy charm, deploy the
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

Then sign the CSR using the CA we created earlier and provide the signed
certificate back to the `manual-tls-certificates` charm.

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

```
12:28:19.254023 [0-0] * Server certificate:
12:28:19.254047 [0-0] *   subject: CN=pollen.test; x500UniqueIdentifier=cdb08400-f565-46cf-b3a9-86a3c566e4e5
12:28:19.254066 [0-0] *   start date: Jun 29 04:26:41 2026 GMT
12:28:19.254085 [0-0] *   expire date: Jun 29 04:26:41 2027 GMT
12:28:19.254103 [0-0] *   issuer: C=US; CN=ca.test
12:28:19.254122 [0-0] *   Certificate level 0: Public key type RSA (2048/112 Bits/secBits), signed using sha256WithRSAEncryption
12:28:19.254141 [0-0] *   Certificate level 1: Public key type RSA (2048/112 Bits/secBits), signed using sha256WithRSAEncryption
12:28:19.254157 [0-0] *  SSL certificate verification failed, continuing anyway!
```

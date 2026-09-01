---
myst:
  html_meta:
    "description lang=en": "Learn how to enable salted hashing of client IP addresses in the HAProxy charm logs."
---

(how_to_hash_client_ip_addresses_in_logs)=

# How to hash client IP addresses in logs

Use the `client-ip-salt-hash` configuration option to enable salted hashing of client IP addresses in HAProxy logs. Hashing client IP addresses helps protect user privacy in logs; see {ref}`Security <explanation_security>` for details.

## Deploy and configure the `haproxy` charm

Deploy the `haproxy` charm. Refer to the {ref}`Tutorial <tutorial_getting_started>` for a more detailed explanation.

```shell
juju deploy haproxy --channel=2.8/edge
```

## Enable client IP hashing

This feature hashes client IP addresses using SHA-256 combined with a salt that you provide through a Juju secret. Generate a random salt with sufficient entropy, for example using `openssl`:

```shell
openssl rand -hex 32
```

The salt must be a non-empty string. It must not contain control characters, double quotes (`"`), backslashes (`\`), or dollar signs (`$`); if the secret contains any of these characters, the charm enters a blocked state.

Create a secret containing a `salt` key, and grant the `haproxy` application access to it.

```shell
juju add-secret client-ip-hash-salt salt=<salt-value>
juju grant-secret client-ip-hash-salt haproxy
```

The `add-secret` command prints the secret's URI. Set the charm configuration to that URI to enable hashing.

```shell
juju config haproxy client-ip-hash-salt=<secret-uri>
```

## Disable client IP hashing

Remove the configuration option to restore plaintext client IP logging.

```shell
juju config haproxy --reset client-ip-hash-salt
```

## Rotate the salt

Update the secret's content to rotate the salt.

```shell
juju update-secret client-ip-hash-salt salt=<new-salt-value>
```

Secret revisions are supported, but rotating the salt changes the hash produced for a given client IP address. Logs recorded before the rotation cannot be correlated with logs recorded afterwards.

## Verify client IP hashing is applied

Send a request to HAProxy using the unit's public address:

```shell
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
curl $HAPROXY_IP
```

Then inspect the access log:

```shell
juju ssh haproxy/0 -- sudo journalctl -u haproxy -n 5
```

Before enabling hashing, the client IP address appears in plaintext.

```{terminal}
:output-only:

192.0.2.10:54321 [31/Aug/2026:20:15:42.123] haproxy~ default/default 0/0/1/2/3 200 1312 - - ---- 1/1/0/0/0 0/0 "GET / HTTP/1.1"
```

After enabling hashing with the salt `example-salt`, the same request is logged with the client IP replaced by its hash.

```{terminal}
:output-only:

5BD1F203B50928CFEC3F9CEB925BDB55B9C1C059AA0361471464ED5632497F2:54321 [31/Aug/2026:20:15:42.123] haproxy~ default/default 0/0/1/2/3 200 1312 - - ---- 1/1/0/0/0 0/0 "GET / HTTP/1.1"
```

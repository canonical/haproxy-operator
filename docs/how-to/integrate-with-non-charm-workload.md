# How to integrate with non-charmed workloads
This guide will show you how non-charm applications can use the `haproxy` charm to load balance traffic with the help of the `ingress-configurator` charm.


## Deploy and configure the `haproxy` charm
Deploy the `haproxy` and `self-signed-certificates` charms. Please refer to the [getting-started](../getting-started.md) section for a more detailed explanation.
```sh
juju deploy haproxy --channel=2.8/edge --base=ubuntu@24.04
juju deploy self-signed-certificates cert
juju integrate haproxy cert
```

## Deploy the ingress configurator charm
```sh
juju deploy ingress-configurator --channel=edge
```

## Deploy a non-charm web server
Spin up a Juju machine without deploying a charm:
```sh
juju add-machine
```

If successful, the terminal will output `created machine 4`.

Take note of the machine ID, in this example it's `4`.

Next, install an `apache` server on the created Juju unit:
```sh
juju ssh 4 sudo apt install apache2
```

Get the IP address of the created unit and verify that the `apache` server is responding to requests:

```sh
APACHE_IP=$(juju status --format=json | jq -r '.machines["4"].ip-addresses[0]')
curl $APACHE_IP -I
```

You should see the `apache` server's response in the terminal:
```
HTTP/1.1 200 OK
Date: Fri, 25 Jul 2025 15:13:58 GMT
Server: Apache/2.4.58 (Ubuntu)
Last-Modified: Fri, 25 Jul 2025 15:10:10 GMT
ETag: "e-63ac2568f4f7e"
Accept-Ranges: bytes
Content-Length: 14
Content-Type: text/html
```

## Configure integrations
Integrate the `ingress-configurator` charm with the `haproxy` charm:
```sh
juju integrate haproxy ingress-configurator
```

Configure a hostname for the requirer charm:
```sh
juju config ingress-configurator hostname=apache.internal
```

## Verify that the requirer charm is reachable through `haproxy`
Using `juju status`, note down the IP address of the `haproxy` charm unit, in this example it is `10.207.217.234`. Then, verify that we can reach the Apache server using `curl`:
```sh
HAPROXY_IP=$(juju status --format=json | jq '.applications["haproxy"].units["haproxy/0"]."public-address"')
curl https://apache.internal -L --insecure --resolve apache.internal:443:$HAPROXY_IP -I
```

You should see the `apache` server's response in the terminal:
```
HTTP/2 200 
date: Fri, 25 Jul 2025 15:19:21 GMT
server: Apache/2.4.58 (Ubuntu)
last-modified: Fri, 25 Jul 2025 15:10:10 GMT
etag: "e-63ac2568f4f7e"
accept-ranges: bytes
content-length: 14
content-type: text/html
```

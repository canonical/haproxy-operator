# How to integrate with non-charmed workloads
This guide will show you how a charm implementing only the `ingress` integration can leverage the added functionalities of the `haproxy-route` integration with the help of the `ingress-configurator` charm.


## Deploy and configure the `haproxy` charm
We will deploy the `haproxy` charm, the `self-signed-certificates` charm. Please refer to the [getting-started](../getting-started.md) section for a more detailed explanation:
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
We will spin up a juju machine without deploying a charm:
```sh
juju add-machine
```

If successful, the terminal will output `created machine 4`.

Take note of the machine ID, in this example it's `4`.

Next, we will install an `apache` server on the created juju unit:
```sh
juju ssh 4 sudo apt install apache2
```

Get the IP address of the created unit using `juju status --format=json | jq -r '.machines["4"].ip-addresses[0]'`. In this example, the unit IP address is `10.207.217.155`:
```sh
Model    Controller  Cloud/Region         Version  SLA          Timestamp
haproxy  lxd         localhost/localhost  3.6.8    unsupported  17:11:16+02:00

App                   Version  Status  Scale  Charm                     Channel      Rev  Exposed  Message
cert                           active      1  self-signed-certificates  1/stable     317  no       
haproxy                        active      1  haproxy                   2.8/edge     199  no       
ingress-configurator           active      1  ingress-configurator      latest/edge    9  no       

Unit                     Workload  Agent  Machine  Public address  Ports       Message
cert/0*                  active    idle   1        10.207.217.216              
haproxy/0*               active    idle   0        10.207.217.234  80,443/tcp  
ingress-configurator/0*  active    idle   2        10.207.217.215              

Machine  State    Address         Inst id        Base          AZ  Message
0        started  10.207.217.234  juju-61cf18-0  ubuntu@24.04      Running
1        started  10.207.217.216  juju-61cf18-1  ubuntu@24.04      Running
2        started  10.207.217.215  juju-61cf18-2  ubuntu@24.04      Running
4        started  10.207.217.155  juju-61cf18-4  ubuntu@24.04      Running
```

Verify that the `apache` server is responding to requests:
```sh
curl 10.207.217.155 -I
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
Integrate the pollen charm with the ingress-configurator charm and the ingress-configurator charm with the haproxy charm:
```sh
juju integrate haproxy ingress-configurator
```

Then, configure a hostname for the requirer charm:
```sh
juju config ingress-configurator hostname=apache.internal
```

## Verify that the requirer charm is reachable through haproxy
Using `juju status`, note down the IP address of the haproxy charm unit, in this example it is `10.207.217.234`. Then, verify that we can reach the Apache server using `curl`:
```sh
curl https://apache.internal -L --insecure --resolve apache.internal:443:10.207.217.234 -I
HTTP/2 200 
date: Fri, 25 Jul 2025 15:19:21 GMT
server: Apache/2.4.58 (Ubuntu)
last-modified: Fri, 25 Jul 2025 15:10:10 GMT
etag: "e-63ac2568f4f7e"
accept-ranges: bytes
content-length: 14
content-type: text/html
```

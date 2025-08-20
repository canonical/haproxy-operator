# How to provide extra configuration to ingress requirers
This guide will show you how a charm implementing only the `ingress` relation can leverage the added functionalities of the `haproxy-route` relation with the help of the `ingress-configurator` charm.

## Deploy the `ingress-configurator` charm
```sh
juju deploy ingress-configurator --channel edge
```
## Deploy an ingress requirer charm
Deploy the `pollen` charm:
```sh
juju deploy pollen --channel edge
```

# Verify that the requirer application is responding to requests
First, get the IP address of the unit of the pollen charm using `juju status` and take note of the address. In this example, the unit address is `10.207.217.174`:
```sh
juju status
Model     Controller  Cloud/Region         Version  SLA          Timestamp
tutorial  lxd         localhost/localhost  3.6.8    unsupported  17:48:33+02:00

App                   Version  Status   Scale  Charm                 Channel      Rev  Exposed  Message
ingress-configurator           blocked      1  ingress-configurator  latest/edge    9  no       Missing haproxy-route relation.
pollen                         active       1  pollen                latest/edge   50  no       

Unit                     Workload  Agent  Machine  Public address  Ports     Message
ingress-configurator/0*  blocked   idle   0        10.207.217.232            Missing haproxy-route relation.
pollen/0*                active    idle   1        10.207.217.174  8080/tcp  

Machine  State    Address         Inst id        Base          AZ  Message
0        started  10.207.217.232  juju-6989d3-0  ubuntu@24.04      Running
1        started  10.207.217.174  juju-6989d3-1  ubuntu@22.04      Running
```

Then, verify that the requirer application is responding to requests by using `curl`:
```sh
$ curl 10.207.217.174:8080
Please use the pollinate client.  'sudo apt-get install pollinate' or download from: https://bazaar.launchpad.net/~pollinate/pollinate/trunk/view/head:/pollinate
```

## Deploy and configure the haproxy charm
We will deploy the `haproxy` and `self-signed-certificates` charms. Please refer to the [getting-started](../getting-started.md) section for a more detailed explanation:
```sh
juju deploy haproxy --channel=2.8/edge --base=ubuntu@24.04
juju deploy self-signed-certificates cert
juju integrate haproxy cert
```

## Configure integrations
Interate the `pollen` charm with the `ingress-configurator` charm and the `ingress-configurator` charm with the `haproxy` charm:
```sh
juju integrate haproxy ingress-configurator
juju integrate ingress-configurator pollen
```

Then, configure a hostname for the requirer charm:
```sh
juju config ingress-configurator hostname=pollen.internal
```

## Verify that the requirer charm is reachable through `haproxy`
sing `juju status`, note down the IP address of the `haproxy` charm unit, in this example it is `10.207.217.234`.Then, verify that we can reach `pollen` using `curl` 
```sh
curl https://pollen.internal -L --insecure --resolve pollen.internal:443:10.207.217.234
Please use the pollinate client.  'sudo apt-get install pollinate' or download from: https://bazaar.launchpad.net/~pollinate/pollinate/trunk/view/head:/pollinate
```


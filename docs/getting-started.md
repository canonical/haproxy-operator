# Deploy the haproxy charm

In this tutorial we'll look at how to deploy the haproxy charm to provide ingress to a backend application, then configure high-avalability using the `hacluster` relation. This tutorial is done on LXD and assumes that you have a Juju controller bootstrapped and a machine model to deploy charms.

## Requirements

* A working station, e.g., a laptop, with amd64 architecture.
* Juju 3.3 or higher installed and bootstrapped to a LXD controller. You can accomplish
this process by using a [Multipass](https://multipass.run/) VM as outlined in this guide: [Set up / Tear down your test environment](https://canonical-juju.readthedocs-hosted.com/en/3.6/user/howto/manage-your-deployment/manage-your-deployment-environment/#set-things-up)

## Set up a tutorial model

To manage resources effectively and to separate this tutorial's workload from your usual work, create a new model using the following command.
```
juju add-model haproxy-tutorial
```

## Deploy the haproxy charm
We will deploy charm from Charmhub. The `--base=ubuntu@24.04` is used so that the latest revision is correctly fetched. 
```
juju deploy haproxy --channel=2.8/edge --base=ubuntu@24.04
```

## Configure TLS
Haproxy enforces HTTPS when using the `ingress` integration. To set up the TLS for the `haproxy` charm, deploy the `self-signed-certificates` charm as the `cert` application, integrate with the haproxy charm and configure a hostname.
```
juju deploy self-signed-certificates cert
juju integrate haproxy cert

HAPROXY_HOSTNAME="haproxy.internal"
juju config haproxy external-hostname=$HAPROXY_HOSTNAME
```

Check the status of the charms using `juju status`. The output should look similar to the following:
```
haproxy-tutorial  lxd         localhost/localhost  3.6.4    unsupported  13:56:51+01:00

App      Version  Status  Scale  Charm                     Channel   Rev  Exposed  Message
cert              active      1  self-signed-certificates  1/stable  263  no       
haproxy           active      1  haproxy                   2.8/edge  141  no       

Unit        Workload  Agent  Machine  Public address  Ports   Message
cert/0*     active    idle   1        10.208.204.86           
haproxy/0*  active    idle   0        10.208.204.138  80/tcp  

Machine  State    Address         Inst id        Base          AZ  Message
0        started  10.208.204.138  juju-1d3062-0  ubuntu@24.04      Running
1        started  10.208.204.86   juju-1d3062-1  ubuntu@24.04      Running
```

Note the IP address of the haproxy unit; in the above example, the relevant IP address is `10.208.204.138`. Save the IP address to an environment variable named HAPROXY_IP:
```
HAPROXY_IP=10.208.204.138
```

Now let's verify with curl:
```
curl $HAPROXY_IP
```

If successful, the terminal will output:
```
Default page for the haproxy-operator charm
```

## Deploy the backend application and relate to the haproxy charm
In this tutorial we will use `any-charm` as the backend application. We will fetch the predefined source file using `curl` and pass it to the charm with the `src-overwrite` option. This source file will allow us to start an Apache web server and communicate the relevant details to the `haproxy` charm so that traffic is properly routed to the Apache web server.
```
juju deploy any-charm requirer --channel beta --config src-overwrite="$(curl -L https://github.com/canonical/haproxy-operator/releases/download/rev141/haproxy_route_requirer_src.json)" --config python-packages="pydantic~=2.10"
juju run requirer/0 rpc method=start_server
juju integrate requirer haproxy
```

Let's check that the request has been properly proxied to the backend service. The `--insecure` option is needed here as we are using a self-signed certificate, as well as the `--resolve` option to manually perform a DNS lookup as haproxy will issue an HTTPS redirect to `$HAPROXY_HOSTNAME`. Finally, `-L` is also needed to automatically follow redirects.
```
curl -H "Host: $HAPROXY_HOSTNAME" $HAPROXY_IP/haproxy-tutorial-requirer/ok -L --insecure --resolve $HAPROXY_HOSTNAME:443:$HAPROXY_IP
```

If successful, the terminal will respond with `ok!`.

## Configure high-availability
High availability (HA) allows the haproxy charm to continue to function even if some units fails, while maintaining the same address across all units. We'll do that with the help of the `hacluster` subordinate charm.

### Scale the haproxy charm to 3 units
We'll start by scaling the haproxy charm to 3 units as by default it's the minimum required by the `hacluster` charm.
```
juju add-unit haproxy -n 3
```

### Deploy and integrate the `hacluster` subordinate charm
Deploy the subordinate charm, and specify `--base=ubuntu@24.04` so that the charm is deployed with a base matching the `haproxy` charm.
```
juju deploy hacluster --channel=2.4/edge --base=ubuntu@24.04
juju integrate hacluster haproxy
```

### Configure a virtual IP (vip)
A virtual IP is shared between all haproxy units and serves as the single entrypoint to all requirer applications. To add a virtual IP to the haproxy charm we take a free IP address from the network of the haproxy units. In this example we take the first available address on the LXD subnet.
```
VIP="$(echo "${HAPROXY_IP}" | awk -F'.' '{print $1,$2,$3,2}' OFS='.')"
juju config haproxy vip=$VIP
```

Performing the same request as before, let's replace `$HAPROXY_IP` with `$VIP`. We should see that the request is properly routed to the requirer.
```
curl -H "Host: $HAPROXY_HOSTNAME" $VIP/haproxy-tutorial-requirer/ok -L --insecure --resolve $HAPROXY_HOSTNAME:443:$VIP
```

If successful, the terminal will respond with `ok!`.

## Clean up the environment
Well done! You've successfully completed the haproxy tutorial. To remove the model environment you created, use the following command.
```
juju destroy-model haproxy-tutorial
```
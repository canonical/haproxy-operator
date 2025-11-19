# Deploy the HAProxy charm

In this tutorial we'll look at how to deploy the HAProxy charm to provide ingress to a backend application, then configure high-avalability using the `hacluster` relation. This tutorial is done on LXD and assumes that you have a Juju controller bootstrapped and a machine model to deploy charms.

## Requirements

* A working station, e.g., a laptop, with amd64 architecture.
* Juju 3.3 or higher installed and bootstrapped to a LXD controller. You can accomplish
this process by using a [Multipass](https://multipass.run/) VM as outlined in this guide: [Set up / Tear down your test environment](https://canonical-juju.readthedocs-hosted.com/en/3.6/user/howto/manage-your-deployment/manage-your-deployment-environment/#set-things-up)

## Set up a tutorial model

To manage resources effectively and to separate this tutorial's workload from your usual work, create a new model using the following command.
```
juju add-model haproxy-tutorial
```

## Deploy the HAProxy charm
We will deploy charm from Charmhub. The `--base=ubuntu@24.04` is used so that the latest revision is correctly fetched. 
```
juju deploy haproxy --channel=2.8/edge --base=ubuntu@24.04
```

## Configure TLS
HAProxy enforces HTTPS when using the `ingress` integration. To set up the TLS for the HAProxy charm, deploy the `self-signed-certificates` charm as the `cert` application and integrate with the HAProxy charm.
```
juju deploy self-signed-certificates cert
juju integrate haproxy:certificates cert
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

Note the IP address of the HAProxy unit; in the above example, the relevant IP address is `10.208.204.138`. Use that IP address to an environment variable named `HAPROXY_IP`. 
You can configure the IP from the output of `juju status` with:
```
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
```

Now let's verify with curl:
```
curl $HAPROXY_IP
```

If successful, the terminal will output:
```
Default page for the haproxy-operator charm
```

<!-- valeCanonical.007-Headings-sentence-case = NO -->
## Use the Ingress configurator charm to proxy a web server
<!-- valeCanonical.007-Headings-sentence-case = YES -->

The [Ingress configurator charm](https://charmhub.io/ingress-configurator) can
be used as a translation layer between the ingress interface and the `haproxy-route` interface,
but it also works to proxy backends external to Juju.

In this tutorial we are going to run a local Python application hosting a web server. Run the following command:
```
python3 -m http.server 8080 &
```

Deploy the Ingress Configurator charm and point it to the Python web server. We also need to configure a hostname for the
frontend.
```
HAPROXY_HOSTNAME="haproxy.internal"
LOCAL_IPADDR=$(ip -4 -j route get 2.2.2.2 | jq -r '.[] | .prefsrc')
juju deploy ingress-configurator  --channel=edge --config hostname=$HAPROXY_HOSTNAME --config backend-addresses=$LOCAL_IPADDR --config backend-ports=8080
juju integrate ingress-configurator haproxy
```

Let's check that the request has been properly proxied to the backend service. 
The `--insecure` option is needed here as we are using a self-signed certificate, as well as the `--resolve` option to manually perform a DNS lookup as HAProxy will issue an HTTPS redirect to `$HAPROXY_HOSTNAME`. Finally, `-L` is also needed to automatically follow redirects.
```
curl -H "Host: $HAPROXY_HOSTNAME" "$HAPROXY_IP" -L --insecure --resolve "$HAPROXY_HOSTNAME:443:$HAPROXY_IP"
```

If successful, you will see a list of the contents of the working directory for the Python web server.

## Configure high-availability
High availability (HA) allows the HAProxy charm to continue to function even if some units fails, while maintaining the same address across all units. We'll do that with the help of the `hacluster` subordinate charm.

### Scale the HAProxy charm to three units
We'll start by scaling the HAProxy charm to three units as by default it's the minimum required by the `hacluster` charm.
```
juju add-unit haproxy -n 3
```

### Deploy and integrate the `hacluster` subordinate charm
Deploy the subordinate charm, and specify `--base=ubuntu@24.04` so that the charm is deployed with a base matching the HAProxy charm.
```
juju deploy hacluster --channel=2.4/edge --base=ubuntu@24.04
juju integrate hacluster haproxy
```

### Configure a virtual IP (vip)
A virtual IP is shared between all HAProxy units and serves as the single entrypoint to all requirer applications. To add a virtual IP to the HAProxy charm we take a free IP address from the network of the HAProxy units. In this example we take the first available address on the LXD subnet.
```
VIP="$(echo "${HAPROXY_IP}" | awk -F'.' '{print $1,$2,$3,2}' OFS='.')"
juju config haproxy vip=$VIP
```

Performing the same request as before, let's replace `$HAPROXY_IP` with `$VIP`. We should see that the request is properly routed to the requirer.
```
curl -H "Host: $HAPROXY_HOSTNAME" "${VIP}" -L --insecure --resolve "$HAPROXY_HOSTNAME:443:$VIP"
```

If successful, the terminal will respond with `ok!`.

## Clean up the environment

Well done! You've successfully completed the HAProxy tutorial.

Kill the background Python web server with:
```
kill $!
```

To remove the model environment you created, use the following command.
```
juju destroy-model haproxy-tutorial
```
# Deploy the haproxy charm

In this tutorial we'll look at how to deploy the haproxy charm to provide ingress to a backend application, then configure high-avalability using the `hacluster` relation. This tutorial is done on lxd and assumes that you have a juju controller bootstrapped and a machine model to deploy charms.

## Requirements

* A working station, e.g., a laptop, with amd64 architecture.
* Juju 3.3 or higher installed and bootstrapped to a LXD controller. You can accomplish
this process by using a [Multipass](https://multipass.run/) VM as outlined in this guide: [Set up / Tear down your test environment](https://canonical-juju.readthedocs-hosted.com/en/3.6/user/howto/manage-your-deployment/manage-your-deployment-environment/#set-things-up)

### Set up a tutorial model

To manage resources effectively and to separate this tutorial's workload from
your usual work, create a new model using the following command.

```
juju add-model haproxy-tutorial
```

# Deploy the haproxy charm
```
juju deploy haproxy --channel=2.8/edge --base=ubuntu@24.04
```

# Configure TLS
```
juju deploy self-signed-certificates cert
juju relate haproxy cert

HAPROXY_HOSTNAME="haproxy.internal"
juju config haproxy external-hostname=$HAPROXY_HOSTNAME
```

After the charm has been successfully deployed, verify that it's serving the default page.
```
juju status
# Note down the IP address of the haproxy unit
# Save the IP address to an environment variable named HAPROXY_IP
HAPROXY_IP=
# Verify with curl
curl $HAPROXY_IP
```

# Deploy the requirer application and relate to the haproxy charm
```
juju deploy any-charm requirer --channel beta --config src-overwrite="$(curl https://raw.githubusercontent.com/canonical/haproxy-operator/2518f9efe58f48ef60a140f3cffe039078855b1d/tests/integration/any_charm_ingress_requirer_src_rewrite.json)" --config python-packages="pydantic<2.0"
juju run requirer/0 rpc method=start_server
juju relate requirer haproxy
```

You should now see that the request has been properly proxied to the backend service
```
$ curl -H "Host: $HAPROXY_HOSTNAME" $HAPROXY_IP/haproxy-tutorial-requirer/ok -L --insecure --resolve $HAPROXY_HOSTNAME:443:$HAPROXY_IP
ok!
```

# Configure high-availability
## Scale the haproxy charm to 4 units
```
juju add-unit haproxy -n 3
```

## Deploy the `hacluster` subordinate charm and relate it to the haproxy charm. 
```
juju deploy hacluster --channel=2.4/edge --base=ubuntu@24.04
juju relate hacluster haproxy
```

### Configure a virtual IP (vip)
A virtual IP is shared between all haproxy units and serves as the single entrypoint to all requirer applications. To add a virtual IP to the haproxy charm we take a free IP address from the network of the haproxy units. In this example we take the first available address on the lxd subnet.
```
VIP="$(echo "${HAPROXY_IP}" | awk -F'.' '{print $1,$2,$3,2}' OFS='.')"
juju config haproxy vip=$VIP
```

Performing the same request, replacing $HAPROXY_IP with $VIP and you should see that the request is properly routed to the requirer.
```
$ curl -H "Host: $HAPROXY_HOSTNAME" $VIP/haproxy-tutorial-requirer/ok -L --insecure --resolve $HAPROXY_HOSTNAME:443:$VIP
ok!
```

# Clean up the Environment
Well done! You've successfully completed the Deploy haproxy tutorial. To remove the model environment you created during this tutorial, use the following command.

```
juju destroy-model haproxy-tutorial
```
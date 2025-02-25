In this tutorial we'll look at how to deploy the haproxy charm to provide ingress to a backend application, then configure high-avalability using the `hacluster` relation. This tutorial is done on lxd and assumes that you have a juju controller bootstrapped and a machine model to deploy charms.
# Deploy the haproxy charm
```
juju deploy haproxy --channel=2.8/edge --base=ubuntu@24.04
```

After the charm has been sucessfully deployed, verify that it's serving the default page.
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
juju deploy irc-bridge
juju relate irc-bridge haproxy
curl $HAPROXY_IP
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

## Configure a virtual IP (vip)
A virtual IP is shared between all haproxy units and serves as the single entrypoint to all requirer applications. To add a virtual IP to the haproxy charm we take a free IP address from the network of the haproxy units.
```
VIP="" # TODO: add command to parse the IP address here
juju config haproxy vip=$VIP
```

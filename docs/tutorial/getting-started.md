(tutorial_getting_started)=

# Deploy the HAProxy charm

In this tutorial we'll deploy the HAProxy charm to provide ingress to a backend application, then configure high-avalability using the `hacluster` relation. This tutorial is done on LXD and assumes that you have a Juju controller bootstrapped and a machine model to deploy charms.

## Requirements

You will need a working station, e.g., a laptop, with AMD64 architecture. Your working station
should have at least 4 CPU cores, 8 GB of RAM, and 50 GB of disk space.

````{tip}
You can use Multipass to create an isolated environment by running:
```
multipass launch 24.04 --name charm-tutorial-vm --cpus 4 --memory 8G --disk 50G
```
````

This tutorial requires the following software to be installed on your working station
(either locally or in the Multipass VM):

- Juju 3.3
- LXD 5.21.4

Use [Concierge](https://github.com/canonical/concierge) to set up Juju and LXD:

```
sudo snap install --classic concierge
sudo concierge prepare -p machine
```

This first command installs Concierge, and the second command uses Concierge to install
and configure Juju and LXD.

For this tutorial, Juju must be bootstrapped to a LXD controller. Concierge should
complete this step for you, and you can verify by checking for `msg="Bootstrapped Juju" provider=lxd`
in the terminal output and by running `juju controllers`.

If Concierge did not perform the bootstrap, run:

```bash
juju bootstrap lxd tutorial-controller
```

## Set up a tutorial model

To manage resources effectively and to separate this tutorial's workload from your usual work, create a new model using the following command:

```
juju add-model haproxy-tutorial
```

## Deploy the HAProxy charm

We will deploy charm from Charmhub using the `2.8/stable` channel:

```
juju deploy haproxy --channel=2.8/stable
```

## Configure TLS

HAProxy enforces HTTPS when using the `haproxy-route` relation. To set up the TLS for the HAProxy charm, deploy the `self-signed-certificates` charm and integrate with the HAProxy charm:

```
juju deploy self-signed-certificates
juju integrate haproxy:certificates self-signed-certificates
```
 
Once all the application has settled into an "Idle" state, we can verify by sending a request to the HAProxy's IP address:

```sh
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
curl $HAPROXY_IP
```

If successful, the terminal will output:
If successful, the terminal will output:

```{terminal}
:output-only:

Default page for the haproxy-operator charm
```

## Deploy the backend application

For this tutorial we'll use the [Pollen charm](https://charmhub.io/pollen). Start by deploying the Pollen charm:

```sh
juju deploy pollen --channel=latest/edge
```

Configure a hostname for HAProxy and integrate the Pollen charm with HAProxy:

```sh
juju config haproxy external-hostname=pollen.internal
juju integrate pollen haproxy:haproxy-route
```

Let's check that the request has been properly proxied to the backend service using the `pollinate` script:

```sh
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
echo "$HAPROXY_IP pollen.internal" | sudo tee /etc/hosts
sudo pollinate -s https://pollen.internal -r -i
```

If successful, you should see a success message in the terminal:

```{terminal}
:output-only:

<13>Dec 17 20:45:02 pollinate[59078]: system was previously seeded at [2025-12-17 00:08:36.226000000 +0100]
<13>Dec 17 20:45:02 pollinate[59078]: client sent challenge to [https://pollen.internal]
<13>Dec 17 20:45:02 pollinate[59078]: client verified challenge/response with [https://pollen.internal]
<13>Dec 17 20:45:02 pollinate[59078]: client hashed response from [https://pollen.internal]
<13>Dec 17 20:45:02 pollinate[59078]: client successfully seeded [/dev/urandom]
```

## Clean up the environment

Well done! You've successfully completed the HAProxy tutorial.

To remove the model environment you created, use the following command:

```
juju destroy-model haproxy-tutorial
```

## Next steps

Check out these advanced tutorials to learn how to use HAProxy to provide load balancing for different protocols.

* {ref}`tutorial_loadbalancing_for_an_ftp_server`
* {ref}`tutorial_loadbalancing_for_a_grpc_server`

(tutorial_getting_started)=

# Deploy the HAProxy charm

In this tutorial we'll look at how to deploy the HAProxy charm to provide ingress to a backend application, then configure high-avalability using the `hacluster` relation. This tutorial is done on LXD and assumes that you have a Juju controller bootstrapped and a machine model to deploy charms.

## Requirements

* A working station, e.g., a laptop, with amd64 architecture.
* Juju 3.3 or higher installed and bootstrapped to a LXD controller. You can accomplish
this process by using a [Multipass](https://multipass.run/) VM as outlined in this guide: {ref}`Set up your test environment <juju:set-things-up>`

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
```
Default page for the haproxy-operator charm
```

<!-- valeCanonical.007-Headings-sentence-case = NO -->
## Deploy the backend application
<!-- valeCanonical.007-Headings-sentence-case = YES -->

For this tutorial we'll use the [Pollen charm](https://charmhub.io/pollen). Start by deploying the Pollen charm:

```sh
juju deploy pollen --channel=latest/edge
```

Configure a hostname for HAProxy and integrate the Pollen charm with HAProxy:

```sh
juju config haproxy external-hostname=pollen.internal
juju integrate pollen haproxy:haproxy-route
```

Let's check that the request has been properly proxied to the backend service. using the `pollinate` script:

```sh
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
echo "$HAPROXY_IP pollen.internal" | sudo tee /etc/hosts
sudo pollinate -s https://pollen.internal -r -i
```

If successful, you should see a success message in the terminal:

```
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

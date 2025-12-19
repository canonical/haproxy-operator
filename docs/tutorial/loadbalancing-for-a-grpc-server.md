(tutorial_loadbalancing_for_a_grpc_server)=

# Loadbalancing for a gRPC server

In this tutorial we'll look at how to deploy the HAProxy charm to provide loadbalancing for a VM running [`flagd`](https://flagd.dev). This tutorial is done on LXD and assumes that you have a Juju controller bootstrapped and a machine model to deploy charms.

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

We will deploy charm from Charmhub using the `2.8/edge` channel:

```
juju deploy haproxy --channel=2.8/edge
```

## Configure TLS

HAProxy enforces HTTPS when using the `haproxy-route` relation. To set up the TLS for the HAProxy charm, deploy the `self-signed-certificates` charm and integrate with the HAProxy charm:

```
juju deploy self-signed-certificates
juju integrate haproxy:certificates self-signed-certificates
```

## Deploy and configure `flagd`

First, we'll spin up a juju machine to host the `flagd` service:

```sh
juju add-machine
```

Once the machine is in an "Active" state, install and configure the `flagd` server. The following command will fetch the `flagd` binary and setup a dedicated working directory for the `flagd` service:

```sh
cat << EOF | juju ssh 1
curl -L -s https://github.com/open-feature/flagd/releases/download/flagd%2Fv0.12.9/flagd_0.12.9_Linux_x86_64.tar.gz | tar xzvf -
sudo mv flagd_linux_x86_64 /usr/bin/flagd
sudo mkdir -p /etc/flagd
EOF
```

Before continuing further, we need to get a certificate for the `flagd` service. This is because loadbalancing gRPC in the HAProxy charm requires the backend to support the standard HTTP/2 over TLS protocol. To do this, first, deploy the [TLS Certificates Requirer charm](https://charmhub.io/tls-certificates-requirer) to request a certificate for `flagd`:

```sh
GRPC_SERVER_ADDRESS=$(juju status --format json | jq -r  '.machines."1"."ip-addresses".[0]')
juju deploy tls-certificates-requirer --channel=latest/edge --config common_name=$GRPC_SERVER_ADDRESS
juju integrate tls-certificates-requirer self-signed-certificates
```

Then, once the `tls-certificates-requirer` charm has settled into an "Active" state, fetch the certificate and the private key and copy them to the machine running `flagd`. We'll use the [`jhack`](https://snapcraft.io/jhack) debugging tool to fetch the private key from the charm:

```sh
sudo snap install jhack --channel=latest/stable
echo "y" | jhack eval tls-certificates-requirer/0 self.certificates.private_key 2>/dev/null | tail -n +2 | awk '{$1=$1;print}' > server.key
juju run tls-certificates-requirer/0 get-certificate --format json | jq -r '."tls-certificates-requirer/0".results.certificates' | jq -r '.[0].certificate' > server.crt

juju scp server.{crt,key} 1:~
```

Then, configure haproxy to retrieve and trust the CA certificate from the `self-signed-certificates` charm:

```sh
juju integrate haproxy:receive-ca-certs self-signed-certificates
```

Finally, setup the `systemd` service for `flagd`:

```sh
cat << EOF | juju ssh 1
cat << EEOF | sudo tee /etc/systemd/system/flagd.service
[Unit]
Description="A feature flag daemon with a Unix philosophy"

[Service]
User=root
WorkingDirectory=/etc/flagd
ExecStart=flagd start --port 8013 --uri https://raw.githubusercontent.com/open-feature/flagd/main/samples/example_flags.flagd.json --server-cert-path=/home/ubuntu/server.crt --server-key-path=/home/ubuntu/server.key
Restart=always

[Install]
WantedBy=multi-user.target
EEOF

sudo systemctl daemon-reload
sudo systemctl restart flagd
EOF
```

## Deploy and configure the ingress configurator charms

To expose our gRPC server through HAProxy, we need to deploy the [Ingress Configurator charm](https://charmhub.io/ingress-configurator):

```sh
juju deploy ingress-configurator grpc-configurator --channel=latest/edge
```

Once the charm has settled into an "Active" state, update its configuration and integrate with HAProxy via the `haproxy-route` relation:

```sh
GRPC_SERVER_ADDRESS=$(juju status --format json | jq -r  '.machines."1"."ip-addresses".[0]')
juju config grpc-configurator \
    backend-addresses=$GRPC_SERVER_ADDRESS \
    backend-ports=8013 \
    backend-protocol=https \
    hostname=flagd.haproxy.internal

juju integrate grpc-configurator:haproxy-route haproxy
```

## Verify connection to the gRPC server

Install `grpcurl` and fetch the protocol for the evaluation service of `flagd`:

```sh
sudo snap install grpcurl --edge
curl https://buf.build/open-feature/flagd/raw/main/-/flagd/evaluation/v1/evaluation.proto | sudo tee /var/snap/grpcurl/current/evaluation.proto
```

Once all of the charms have settled into an "Active" state, verify that the gRPC server is reachable through HAProxy:

```sh
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
echo $HAPROXY_IP flagd.haproxy.internal | sudo tee -a /etc/hosts

grpcurl -insecure -d '{"flagKey":"myStringFlag","context":{}}' -proto=evaluation.proto -import-path /var/snap/grpcurl/current flagd.haproxy.internal flagd.evaluation.v1.Service/ResolveString
```

After running the command you should see the reply from `flagd`:

```sh
{
  "value": "val1",
  "reason": "STATIC",
  "variant": "key1",
  "metadata": {}
}
```

## Clean up the environment

Well done! You've successfully completed this tutorial.

To remove the model environment you created, use the following command:

```
juju destroy-model haproxy-tutorial
```

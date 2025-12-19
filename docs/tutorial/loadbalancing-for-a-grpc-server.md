(tutorial_getting_started)=

# Loadbalancing for a gRPC server

In this tutorial we'll look at how to deploy the HAProxy charm to provide loadbalancing for a VM running `flagd`. This tutorial is done on LXD and assumes that you have a Juju controller bootstrapped and a machine model to deploy charms.

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

First, we'll spin up a juju machine to host our FTP server:
```sh
juju add-machine
```

Once the machine is in an "Active" state, install and configure the `flagd` server. The following command will fetch the `flagd` binary and setup a dedicated configuration folder:
```sh
cat << EOF | juju ssh 1
curl -L -s https://github.com/open-feature/flagd/releases/download/flagd%2Fv0.12.9/flagd_0.12.9_Linux_x86_64.tar.gz | tar xzvf -
sudo mv flagd_linux_x86_64 /usr/bin/flagd
sudo mkdir -p /etc/flagd
```

Loadbalancing gRPC in the HAProxy charm requires the backend to support the standard HTTP/2 over TLS protocol. To do this, first, we need to generate a server certificate and a private key for `flagd`:
```sh
GRPC_SERVER_ADDRESS=$(juju status --format json | jq -r  '.machines."1"."ip-addresses".[0]')
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 1024 -out ca.crt -subj "/C=FR/ST=CA/O=, Inc./CN=$GRPC_SERVER_ADDRESS"
openssl genrsa -out server.key 2048
openssl req -new -sha256 -key server.key -subj "/C=FR/ST=P/O=, Inc./CN=$GRPC_SERVER_ADDRESS" -out server.csr
openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt
```

Then, copy the server certificate and private key to the machine running `flagd`, and configure HAProxy to trust the CA that signed the server certificate:
```sh
juju scp server.{crt,key} 1:~

juju scp ca.crt haproxy/0:~
cat << EOF | juju ssh haproxy/0
sudo mv ca.crt /usr/local/share/ca-certificates/flagd.ca.crt
sudo update-ca-certificates
EOF
```

Finally, setup the `systemd` service:
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

```sh
grpcurl -plaintext -d '{"flagKey":"myStringFlag","context":{}}' -proto=evaluation.proto -import-path /var/snap/grpcurl/current localhost:8013 flagd.evaluation.v1.Service/ResolveString
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

Once all of the charms have settled into an "Active" state, verify that the gRPC server is reachable through HAProxy:
```sh
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
ftp -P 2100 ftp://$HAPROXY_IP
```

After running the command you should see `230 Login successful` and an interactive session is openned:
```sh
...
331 Please specify the password.
230 Login successful.
Remote system type is UNIX.
Using binary mode to transfer files.
200 Switching to Binary mode.
ftp>
```

## Clean up the environment

Well done! You've successfully completed this tutorial.

To remove the model environment you created, use the following command:
```
juju destroy-model haproxy-tutorial
```

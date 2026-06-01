(how_to_loadbalancing_for_an_ftp_server)=

# How to provide loadbalancing for an FTP server

In this guide we'll look at how to deploy the HAProxy charm to provide TCP load balancing for a VM running an FTP server. This guide is done on LXD and assumes that you have a Juju controller bootstrapped and a machine model to deploy charms.

## Requirements

You will need a working station, e.g., a laptop, with AMD64 architecture. Your working station
should have at least 4 CPU cores, 8 GB of RAM, and 50 GB of disk space.

This guide requires the following software to be installed on your working station
(either locally or in the Multipass VM):

- Juju 3.3
- LXD 5.21.4

For this guide, Juju must be bootstrapped to a LXD controller. 

Follow the {ref}`setup instructions <tutorial_requirements>` in the tutorial to achieve these requirements.

## Set up a Juju model

To manage resources effectively and to separate this guide's workload from your usual work, create a new model using the following command:

```
juju add-model haproxy-guide
```

## Deploy the HAProxy charm

We will deploy charm from Charmhub using the `2.8/edge` channel:

```
juju deploy haproxy --channel=2.8/edge
```

## Deploy and configure the FTP server

First, we'll spin up a Juju machine to host our FTP server:

```sh
juju add-machine
```

Once the machine is in an "Active" state, install and configure the FTP server. The following command will install `vsftpd` and configure the daemon to run in passive mode with anonymous login enabled:

```sh
cat << EOF | juju ssh 1
sudo apt update; sudo apt install vsftpd -y

sudo sed -i -e 's/anonymous_enable=NO/anonymous_enable=YES/g' /etc/vsftpd.conf
cat << EEOF | sudo tee -a /etc/vsftpd.conf
pasv_enable=Yes
pasv_max_port=10100
pasv_min_port=10100
EEOF

sudo systemctl reload vsftpd.service
EOF
```

## Deploy and configure the ingress configurator charms

To expose our FTP server through HAProxy, we need to deploy two instance of the [Ingress Configurator charm](https://charmhub.io/ingress-configurator), one to configure the control port and the other to configure the data port. Add a machine to host the two charms:

```sh
juju add-machine
```

Then, deploy the two charms to the new machine:

```sh
juju deploy ingress-configurator ftp-control --channel=latest/edge --to 2
juju deploy ingress-configurator ftp-data --channel=latest/edge --to 2
```

Once the two charms have settled into an "Active" state, update their configuration and integrate them with HAProxy using the `haproxy-route-tcp` relation:

```sh
FTP_SERVER_ADDRESS = $(juju status --format json | jq -r  '.machines."5"."ip-addresses".[0]')
juju config ftp-control tcp-backend-addresses=$FTP_SERVER_ADDRESS tcp-backend-port=21 tcp-frontend-port=2100
juju config ftp-data tcp-backend-addresses=$FTP_SERVER_ADDRESS tcp-backend-port=10100 tcp-frontend-port=10100

juju integrate ftp-control:haproxy-route-tcp haproxy
juju integrate ftp-data:haproxy-route-tcp haproxy
```

## Verify connection to the FTP server

Once all of the charms have settled into an "Active" state, verify that the FTP server is reachable through HAProxy:

```sh
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
ftp -P 2100 ftp://$HAPROXY_IP
```

After running the command you should see `230 Login successful` and an interactive session is opened:

```{terminal}
:output-only:

...
331 Please specify the password.
230 Login successful.
Remote system type is UNIX.
Using binary mode to transfer files.
200 Switching to Binary mode.
ftp>
```


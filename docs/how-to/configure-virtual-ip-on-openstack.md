# How to configure a virtual IP on OpenStack
The process to get a virtual IP address for hacluster is different based the cloud on which the HAProxy charm units are running. This document covers the process of creating a virtual IP address for a HAProxy charm deployed on OpenStack.

## Create the OpenStack port for the virtual IP
We need to do this to ensure that this IP will not get assigned to a new machine in the OpenStack subnet. 
First, run `openstack subnet list` to find the subnet ID and the network ID on which the charm units are running. Then create the port using `openstack port create`, replacing `<subnet-id>` and `<network-id>` with values you got from running `openstack subnet list`:
```
openstack port create --fixed-ip subnet=<subnet-id>,ip-address=10.142.65.2 --no-security-group --network <network-id> vip
```

## Configure OpenStack ports
Run `juju status` to get the IP address information for each HAProxy unit. You should see something similar to the output below:
```
haproxy/1                  active       idle       15       10.142.65.173   80/tcp  
  grafana-agent/9          active       idle                10.142.65.173           send-remote-write: off, tracing: off
  hacluster/3              active       idle                10.142.65.173           Unit is ready and clustered
haproxy/2                  active       idle       16       10.142.65.60    80/tcp  
  grafana-agent/10         active       idle                10.142.65.60            send-remote-write: off, tracing: off
  hacluster/4              waiting      idle                10.142.65.60            Resource: res_haproxy_b34f0e1_vip not yet configured
haproxy/3*                 active       idle       17       10.142.65.229   80/tcp  
  grafana-agent/11*        active       idle                10.142.65.229           send-remote-write: off, tracing: off
  hacluster/5*             active       idle                10.142.65.229           Unit is ready and clustered
haproxy/4                  active       idle       18       10.142.65.219   80/tcp  
  grafana-agent/12         active       idle                10.142.65.219           send-remote-write: off, tracing: off
  hacluster/6              waiting      idle                10.142.65.219           Resource: res_haproxy_b34f0e1_vip not yet configured
```

Note the IP address for each unit. In this example the IP addresses of the HAProxy units are `10.142.65.173`, `10.142.65.60`, `10.142.65.229` and `10.142.65.219`. 

Run `openstack port list` to get the ID of the corresponding OpenStack ports. The terminal will output something like the following:
```
+--------------------------------------+------+-------------------+------------------------------------------------------------------------------+--------+
| ID                                   | Name | MAC Address       | Fixed IP Addresses                                                           | Status |
+--------------------------------------+------+-------------------+------------------------------------------------------------------------------+--------+
| 07521c1c-c9d2-4a80-b5bd-c6733f5175f7 |      | fa:16:3e:0c:41:c2 | ip_address='10.142.65.1', subnet_id='0a3b2455-b6f9-47d5-a9aa-ce6857de9284'   | ACTIVE |
| 38861254-8991-4d1a-b686-050a016b2622 |      | fa:16:3e:df:54:1c | ip_address='10.142.65.173', subnet_id='0a3b2455-b6f9-47d5-a9aa-ce6857de9284' | ACTIVE |
| 6040a4d1-8f91-4fc2-b961-170fcf0eaf2c | vip  | fa:16:3e:cb:09:10 | ip_address='10.142.65.2', subnet_id='0a3b2455-b6f9-47d5-a9aa-ce6857de9284'   | DOWN   |
| 6885fbf7-8a3d-463b-9a85-5a74f88559c2 |      | fa:16:3e:20:fe:69 | ip_address='10.142.65.229', subnet_id='0a3b2455-b6f9-47d5-a9aa-ce6857de9284' | ACTIVE |
| 75ed7444-9fb6-42f9-bf33-237022b59255 |      | fa:16:3e:53:7a:d2 | ip_address='10.142.65.60', subnet_id='0a3b2455-b6f9-47d5-a9aa-ce6857de9284'  | ACTIVE |
| afd0c724-a9a8-4f32-8e40-5b410ba0989d |      | fa:16:3e:9a:c7:d8 | ip_address='10.142.65.205', subnet_id='0a3b2455-b6f9-47d5-a9aa-ce6857de9284' | ACTIVE |
| c896fd79-f360-467c-8c2c-2821f5fc9d11 |      | fa:16:3e:16:e2:d3 | ip_address='10.142.65.3', subnet_id='0a3b2455-b6f9-47d5-a9aa-ce6857de9284'   | DOWN   |
| fa086c2f-f8c4-41c1-87e6-89c4751c2cd3 |      | fa:16:3e:8f:e1:f3 | ip_address='10.142.65.219', subnet_id='0a3b2455-b6f9-47d5-a9aa-ce6857de9284' | ACTIVE |
+--------------------------------------+------+-------------------+------------------------------------------------------------------------------+--------+
```

In this example, the OpenStack port IDs of the relevant units are `38861254-8991-4d1a-b686-050a016b2622`, `6885fbf7-8a3d-463b-9a85-5a74f88559c2`, `75ed7444-9fb6-42f9-bf33-237022b59255` and `fa086c2f-f8c4-41c1-87e6-89c4751c2cd3`. For each port, run `openstack port set --allow-address` to allow the virtual IP to forward traffic to the HAProxy charm units:
```
openstack port set 38861254-8991-4d1a-b686-050a016b2622 --allowed-address ip-address=10.142.65.2
openstack port set 6885fbf7-8a3d-463b-9a85-5a74f88559c2 --allowed-address ip-address=10.142.65.2
openstack port set 75ed7444-9fb6-42f9-bf33-237022b59255 --allowed-address ip-address=10.142.65.2
openstack port set fa086c2f-f8c4-41c1-87e6-89c4751c2cd3 --allowed-address ip-address=10.142.65.2
```

## Test that the virtual IP address is working as intended
Run `curl` to verify that you can reach the active HAProxy unit with the virtual IP address:
```
curl 10.142.65.2
```

You should see that the active unit returns the default page:
```
Default page for the haproxy-operator charm
``` 
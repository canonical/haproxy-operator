(how_to_control_haproxy_route_relation_data)=

# How to control haproxy-route relation data with the policy charm

This guide will show you how to use the `haproxy-route-policy` charm to control which backends are allowed to be routed through `haproxy`. When integrated, all `haproxy-route` backends are blocked by default until explicitly approved through the policy API.

## Set up the model

```sh
juju add-model haproxy-route-guide
```

## Deploy HAProxy and a backend requirer

Deploy the `haproxy` charm with TLS and an `ingress-configurator` as the backend requirer:

```sh
juju deploy haproxy --channel=2.8/edge
juju deploy self-signed-certificates cert
juju integrate haproxy:certificates cert
juju deploy ingress-configurator requirer --channel=latest/edge
juju integrate ingress-configurator:haproxy-route haproxy
```

<!-- SPREAD
juju wait-for application requirer --query='status=="active"' --timeout 10m
-->

## Configure the backend requirer

Install a web server on the requirer unit and configure the external hostname on the `haproxy` charm:

```sh
juju ssh requirer/0 -- sudo apt update; sudo apt install -y apache2
REQUIRER_IP=$(juju status --format json | jq -r '.applications.requirer.units."requirer/0"."public-address"')
juju config haproxy external-hostname=haproxy.internal
juju config requirer backend-addresses=$REQUIRER_IP backend-ports=80
```

## Deploy the policy charm

Deploy the `haproxy-route-policy` charm, then integrate it with `postgresql` and `haproxy`:

```sh
juju deploy haproxy-route-policy --channel=latest/edge
juju deploy postgresql --channel=16/edge
juju relate haproxy-route-policy postgresql
juju relate haproxy-route-policy haproxy
```

<!-- SPREAD
juju wait-for application haproxy-route-policy --query='status=="active"' --timeout 10m
juju wait-for application haproxy --query='status=="active"' --timeout 10m
-->

## Verify that the backend is blocked

Once the policy charm is integrated, all backends are blocked by default. Verify that the backend is no longer reachable:

```sh
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
curl -H "Host: haproxy.internal" https://$HAPROXY_IP -k
```

You should see the HAProxy default page instead of the Apache server:

```{terminal}
:output-only:

Default page for the haproxy-operator charm.
```

## Access the policy API

HAProxy exposes the policy REST API through at a generated subdomain. Query the list of pending backend requests using the IP address of the HAProxy unit and the policy admin password:

```sh
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
POLICY_ADMIN_PASSWORD=$(juju run haproxy-route-policy/0 get-admin-credentials --format json | jq -r '.results.password')
curl -H "Host: tutorial-haproxy-route-policy.haproxy.internal" -u "admin:$POLICY_ADMIN_PASSWORD" https://$HAPROXY_IP/api/v1/requests -k
```

The response contains a JSON list of backend requests waiting for approval.

## Create an allow rule and refresh requests

Create a rule to allow backends matching the configured hostname, then refresh all pending requests:

```sh
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
POLICY_ADMIN_PASSWORD=$(juju run haproxy-route-policy/0 get-admin-credentials --format json | jq -r '.results.password')
curl -H "Host: tutorial-haproxy-route-policy.haproxy.internal" -u "admin:$POLICY_ADMIN_PASSWORD" https://$HAPROXY_IP/api/v1/rules -k \
-H 'Content-Type: application/json' \
--data '{
    "kind": "hostname_and_path_match",
    "parameters": {"hostnames": ["haproxy.internal"]},
    "action": "allow"
}'
curl -H "Host: tutorial-haproxy-route-policy.haproxy.internal" -u "admin:$POLICY_ADMIN_PASSWORD" https://$HAPROXY_IP/api/v1/requests/refresh -k
```

## Propagate approved requests

Run the action to propagate the updated approvals back to the `haproxy` charm:

```sh
juju run haproxy-route-policy/0 refresh-backend-requests
```

<!-- SPREAD
juju wait-for application haproxy-route-policy --query='status=="active"' --timeout 10m
juju wait-for application haproxy --query='status=="active"' --timeout 10m
-->

## Verify that the backend is now routed

The approved backend should now be reachable through HAProxy:

```sh
HAPROXY_IP=$(juju status --format json | jq -r '.applications.haproxy.units."haproxy/0"."public-address"')
curl -H "Host: haproxy.internal" https://$HAPROXY_IP -k
```

You should now see the Apache default page in the response.
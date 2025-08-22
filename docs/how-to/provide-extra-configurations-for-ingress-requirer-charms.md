# How to provide extra configuration to ingress requirers
This guide will show you how a charm implementing only the `ingress` relation can leverage the added functionalities of the `haproxy-route` relation with the help of the `ingress-configurator` charm.

## Deploy an ingress requirer charm
Deploy `any-charm`:
```sh
juju deploy any-charm --channel=beta
```

Configure `any-charm` to use the ingress relation
```sh
juju config any-charm src-overwrite="$(cat << EOF | python3 -
import json
import textwrap

any_charm_src = textwrap.dedent(
    '''
    import json
    import socket
    import ops
    import subprocess
    from any_charm_base import AnyCharmBase
    REQUIRE_INGRESS_RELATION = "require-ingress"
    class AnyCharm(AnyCharmBase):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.framework.observe(
                self.on[REQUIRE_INGRESS_RELATION].relation_joined, self._configure
            )
        def _configure(self, _: ops.EventBase):
            if relation := self.model.get_relation(REQUIRE_INGRESS_RELATION):
                relation.data[self.app]["model"] = json.dumps(self.model.name)
                relation.data[self.app]["name"] = json.dumps(self.app.name)
                relation.data[self.app]["port"] = json.dumps(80)
                network_binding = self.model.get_binding(relation)
                bind_address = network_binding.network.bind_address
                relation.data[self.unit]["host"] = json.dumps(socket.getfqdn())
                relation.data[self.unit]["ip"] = json.dumps(str(bind_address))
        def start_server(self):
            subprocess.check_output(["/bin/sh", "-c", "apt install apache2 -y; hostname > /var/www/html/index.html"])
    '''
)
print(json.dumps({"any_charm.py": any_charm_src}))
EOF
)"
```

Finally, start the web server on the `any-charm` unit:
```sh
juju run any-charm/0 rpc method=start_server
```


# Verify that the requirer application is responding to requests
Send a request with `curl` to the `any-charm` unit:
```sh
curl $(juju status --format=json | jq -r '.applications["any-charm"].units["any-charm/0"]."public-address"')
```

You should see the Apache server replying with the unit's hostname:
```sh
juju-344909-3
```

## Deploy and configure the haproxy charm
We will deploy the `haproxy` and `self-signed-certificates` charms. Please refer to the [getting-started](../getting-started.md) section for a more detailed explanation:
```sh
juju deploy haproxy --channel=2.8/edge --base=ubuntu@24.04
juju deploy self-signed-certificates cert
juju integrate haproxy cert
```

## Deploy the `ingress-configurator` charm
```sh
juju deploy ingress-configurator --channel edge
```

## Configure relations
Integrate `any-charm` with the `ingress-configurator` charm and the `ingress-configurator` charm with the `haproxy` charm:
```sh
juju integrate haproxy ingress-configurator
juju integrate ingress-configurator any-charm:require-ingress
```

Then, configure a hostname for the requirer charm:
```sh
juju config ingress-configurator hostname=example.com
```

## Verify that the requirer charm is reachable through `haproxy`
Send a request with `curl` to the `haproxy` charm unit:
```sh
curl https://$(juju status --format=json | jq -r '.applications["haproxy"].units["haproxy/0"]."public-address"') \
    -H "Host: example.com" --insecure
```

You should see the `any-charm` unit's hostname in the returned response:
```sh
juju-344909-3
```

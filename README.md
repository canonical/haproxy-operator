# Overview

This charm deploys a reverse proxy in front of other services. You can use
this to load balance existing deployments.

# Usage

    juju deploy haproxy
    juju deploy my-web-app
    juju relate my-web-app:website haproxy:reverseproxy
    juju add-unit my-web-app
    ...

## Reverse Proxy Relation

The reverse proxy relation is used to distribute connections from one frontend
port to many backend services (typically different Juju _units_).  You can use
haproxy just like this, but typically in a production service you would
frontend this service with apache2 to handle the SSL negotiation, etc.  See
the "Website Relation" section for more information about that.

When your charm hooks into reverseproxy you have two general approaches
which can be used to notify haproxy about what services you are running.
1) Single-service proxying or 2) Multi-service or relation-driven proxying.

1. Single-Service Proxying

In this case, your website relation will join underneath a single `listen`
stanza in haproxy.  This stanza will have one `service` entry for each unit
connecting. By convention, this is typically called "website".  The
following is an example of a relation-joined or changed hook:

    #!/bin/bash
    # hooks/website-relation-joined

    relation-set "hostname=$(unit-get private-address)"
    relation-set "port=80"

    # Set an optional service name, allowing more config-based
    # customization
    relation-set "service_name=my_web_app"

If you set the `service_name` relation setting, the configuration `services`
yaml mapping will be consulted to lookup 3 other options based on service
name.

  * `{service_name}_servers` - sets the `server` line in the listen stanza
    explicitly.
  * `{service_name}_server_options` - Will append to the charm-generated
    server line for for each joining unit in the reverseproxy relation.
  * `{service_name}_service_options` - expected to be a list of strings.  Will
    set each item as an option under the listen stanza.


2. Relation-Driven Proxying 

In this relation style, your charm should specify these relation settings
directly as relation variables when joining reverseproxy.  Your charm's
website-relation-changed hook would look something like this:

    #!/bin/bash
    # hooks/website-relation-changed

    host=$(unit-get private-address)
    port=80

    relation-set "services=
    - { service_name: my_web_app,
        service_host: 0.0.0.0,
        service_port: 80,
        service_options: [mode http, balance leastconn],
        servers: [[my_web_app_1, $host, $port, option httpchk GET / HTTP/1.0],
                  [... optionally more servers here ...]]}
    - { ... optionally more services here ... }
    "

Once set, haproxy will union multiple `servers` stanzas from any units
joining with the same `service_name` under one backend stanza, which will be
the default backend for the service (requests against the given service_port on
the haproxy unit will be forwarded to that backend). Note that `service-options`
and `server_options` will be overwritten, so ensure they are set uniformly on
all services with the same name.

If you need additional backends, possibly handling ACL-filtered requests, you
can add a 'backends' entry to a service stanza. For example in order to redirect
to a different backend all requests to URLs starting with '/foo', you could have:

    relation-set "services=
    - { service_name: my_web_app,
        service_host: 0.0.0.0,
        service_port: 80,
        service_options: [mode http, acl foo path_beg -i /foo, use_backend foo if foo],
        servers: [[my_web_app_1, $host, $port, option httpchk GET / HTTP/1.0],
                  [... optionally more servers here ...]]
        backends:
        - { backend_name: foo,
            servers: [[my_web_app2, $host, $port2, option httpchk GET / HTTP/1.0],
                      [... optionally more servers here ...]]}}


In all cases if your service needs to know the public IP(s) of the haproxy unit(s)
it relates to, or the value of the default SSL certificate set on or generated by
the haproxy service, you can look for the 'public-address' and 'ssl_cert' keys
on your relation, which are set by the haproxy service as soon as it joins the
reverseproxy relation.


## Website Relation

The website relation is the other side of haproxy.  It can communicate with
charms written like apache2 that can act as a front-end for haproxy to take of
things like ssl encryption.  When joining a service like apache2 on its
reverseproxy relation, haproxy's website relation will set an `all_services`
variable that conforms to the spec laid out in the apache2 charm.

These settings can then be used when crafting your vhost template to make sure
traffic goes to the correct haproxy listener which will in turn forward the
traffic to the correct backend server/port

## SSL Termination

You can turn on SSL termination by using the `ssl_cert`/`ssl_key` service configuration
options and then using the `crts` key in the services yaml, e.g.:

    #!/bin/bash
    # hooks/website-relation-changed

    host=$(unit-get private-address)
    port=80

    relation-set "services=
    - { service_name: my_web_app,
        service_options: [mode http, balance leastconn],
        crts: [DEFAULT],
        servers: [[my_web_app_1, $host, $port, option httpchk GET / HTTP/1.0],
                  [... optionally more servers here ...]]}
    - { ... optionally more services here ... }
    "

The DEFAULT keyword means use the certificate set with `ssl_cert`/`ssl_key` (or
alternatively you can inline different base64-encode certificates).

Note that in order to use SSL termination you need haproxy 1.5 or later, which
is not available in stock trusty, but you can get it from trusty-backports setting
the `source` configuration option to `backports` or to whatever PPA/archive you
wish to use.

## SSL Termination with directory for certs

You can configure services to use a filesystem path in the *crts*. This is a good fit when you might have certbot or acme.sh to maintain certificates outside of haproxy itself.

This is an example of this:

Create a services.yaml file for the microsample service:

```
- service_name: microsample
  service_host: "0.0.0.0"
  service_port: 8080
  service_options:
    - mode http
    - balance leastconn
  crts: [/var/lib/haproxy/certs]
```

```
juju deploy microsample
juju deploy haproxy
juju relate haproxy microsample
```

Create the directory and self signed certificate in haproxy/0
```
juju exec --unit haproxy/0 -- sudo mkdir -p /var/lib/haproxy/certs
openssl genpkey -algorithm RSA -out example.key
openssl req -x509 -new -key example.key -out example.crt
cat example.key example.crt > /var/lib/haproxy/certs/example.pem
```

Configure haproxy with the services.yaml content.

`juju config haproxy services="$(cat services.yaml)"`

This produces a stanza in haproxy.cfg as:

```
frontend haproxy-0-8080
    bind 0.0.0.0:8080 ssl crt /var/lib/haproxy/certs no-sslv3
    default_backend microsample
    mode http
```

Once you have valid certs in the directory, they will be used.

## Monitoring

Telegraf is recommended for monitoring HAProxy. To do so, deploy the
following:

    juju deploy haproxy
    juju deploy telegraf
    juju relate telegraf:juju-info haproxy # For standard telegraf host metrics
    juju relate telegraf:haproxy haproxy   # For HAProxy-specific metrics

You can then get metrics for your HAProxy instance(s) by visiting
`http://${unit_up}:9103/metrics`.

## Development

The following steps are needed for testing and development of the charm,
but **not** for deployment:

    sudo apt-get install python-software-properties
    sudo add-apt-repository ppa:cjohnston/flake8
    sudo apt-get update
    sudo apt-get install python-mock python-flake8 python-nose python-nosexcover python-testtools charm-tools

To run the tests:

    make build

... will run the unit tests, run flake8 over the source to warn about
formatting issues and output a code coverage summary of the 'hooks.py' module.


## Known Limitations and Issues

- Expand Single-Service section as this has not been fully tested.
- Trigger website-relation-changed when the reverse-proxy relation changes


# Configuration

Many of the haproxy settings can be altered via the standard juju configuration
settings.  Please see the config.yaml file as each is fairly clearly documented.

## statsd

This charm supports sending metrics to statsd.

This is done by setting config values (metrics_target being the primary one)
to a host/port of a (UDP) statsd server.

This could instead be done using a relation, but it is common to have
one statsd server that serves multiple environments. Once juju supports
cross-environment relations then that will be the best way to handle 
this configuration, as it will work in either scenario.

## peering\_mode and the indirection layer

If you are going to spawn multiple haproxy units, you should pay special
attention to the peering\_mode configuration option.

### active-passive mode

The peering\_mode option defaults to "active-passive" and in this mode, all
haproxy units ("peers") will proxy traffic to the first working peer (i.e. that
passes a basic layer4 check). What this means is that extra peers are working
as "hot spares", and so adding units doesn't add global bandwidth to the
haproxy layer.

In order to achieve this, the charm configures a new service in haproxy that
will simply forward the traffic to the first working peer. The haproxy service
that actually load-balances between the backends is renamed, and its port
number is increased by one.

For example, if you have 3 working haproxy units haproxy/0, haproxy/1 and
haproxy/2 configured to listen on port 80, in active-passive mode, and
haproxy/2 gets a request, the request is routed through the following path :

haproxy/2:80 ==> haproxy/0:81 ==> \[backends\]

In the same fashion, if haproxy/1 receives a request, it's routed in the following way :

haproxy/1:80 ==> haproxy/0:81 ==> \[backends\]

If haproxy/0 was to go down, then all the requests would be forwarded to the
next working peer, i.e. haproxy/1. In this case, a request received by
haproxy/2 would be routed as follows :

haproxy/2:80 ==> haproxy/1:81 ==> \[backends\]

This mode allows a strict control of the maximum number of connections the
backends will receive, and guarantees you'll have enough bandwidth to the
backends should an haproxy unit die, at the cost of having less overall
bandwidth to the backends.

### active-active mode

If the peering\_mode option is set to "active-active", then any haproxy unit
will be independent from each other and will simply load-balance the traffic to
the backends. In this case, the indirection layer described above is not
created.

This mode allows increasing the bandwidth to the backends by adding additional
units, at the cost of having less control over the number of connections that
they will receive.

# HAProxy Project Information

- [HAProxy Homepage](http://haproxy.1wt.eu/)
- [HAProxy mailing list](http://haproxy.1wt.eu/#tact)

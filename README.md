# Overview

This charm deploys a reverse proxy in front of other servies. You can use this to load balance existing deployments.

# Usage

    juju deploy haproxy
    juju deploy my-web-app
    juju add-relation my-web-app:website haproxy:reverseproxy
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
        service_options: [mode http, balance leastconn],
        servers: [[my_web_app_1, $host, $port, option httpchk GET / HTTP/1.0],
                  [... optionally more servers here ...]]}
    - { ... optionally more services here ... }
    "

Once set, haproxy will union multiple `servers` stanzas from any units
joining with the same `service_name` under one listen stanza.
`service-options` and `server_options` will be overwritten, so ensure they
are set uniformly on all services with the same name.

## Website Relation


The website relation is the other side of haproxy.  It can communicate with
charms written like apache2 that can act as a front-end for haproxy to take of
things like ssl encryption.  When joining a service like apache2 on its
reverseproxy relation, haproxy's website relation will set an `all_services`
varaible that conforms to the spec layed out in the apache2 charm.

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
        crts: [DEFAULT]
        servers: [[my_web_app_1, $host, $port, option httpchk GET / HTTP/1.0],
                  [... optionally more servers here ...]]}
    - { ... optionally more services here ... }
    "

where the DEFAULT keyword means use the certificate set with `ssl_cert`/`ssl_key` (or
alternatively you can inline different base64-encode certificates).

Note that in order to use SSL termination you need haproxy 1.5 or later, which
is not available in stock trusty, but you can get it from trusty-backports setting
the `source` configuration option to `backports` or to whatever PPA/archive you
wish to use.

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

- Expand Single-Service section as I have not tested that mode fully.
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

## HAProxy Project Information

- [HAProxy Homepage](http://haproxy.1wt.eu/)
- [HAProxy mailing list](http://haproxy.1wt.eu/#tact)

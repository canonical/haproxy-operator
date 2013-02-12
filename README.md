Juju charm haproxy
==================

HAProxy is a free, very fast and reliable solution offering high availability,
load balancing, and proxying for TCP and HTTP-based applications. It is
particularly suited for web sites crawling under very high loads while needing
persistence or Layer7 processing. Supporting tens of thousands of connections
is clearly realistic with todays hardware. Its mode of operation makes its
integration into existing architectures very easy and riskless, while still
offering the possibility not to expose fragile web servers to the Net.

How to deploy the charm
-----------------------
    juju deploy haproxy
    juju deploy my-web-app
    juju add-relation my-web-app:website haproxy:reverseproxy
    juju add-unit my-web-app
    ...

Reverseproxy Relation
---------------------

The reverse proxy relation is used to distribute connections from one frontend
port to many backend services (typically different Juju _units_).  You can use
haproxy just like this, but typically in a production service you would
frontend this service with apache2 to handle the SSL negotiation, etc.  See
the "Website Relation" section for more information about that.

When your charm hooks into reverseproxy you have two general approaches
which can be used to notify haproxy about what services you are running. 
1) Single-service proxying or 2) Multi-service or relation-driven proxying.

** 1) Single-Service Proxying **

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


** 2) Relation-Driven Proxying **

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

Website Relation
----------------

The website relation is the other side of haproxy.  It can communicate with
charms written like apache2 that can act as a front-end for haproxy to take of
things like ssl encryption.  When joining a service like apache2 on its
reverseproxy relation, haproxy's website relation will set an `all_services`
varaible that conforms to the spec layed out in the apache2 charm.

These settings can then be used when crafting your vhost template to make sure
traffic goes to the correct haproxy listener which will in turn forward the
traffic to the correct backend server/port

Configuration
-------------
Many of the haproxy settings can be altered via the standard juju configuration
settings.  Please see the config.yaml file as each is fairly clearly documented.

Testing
-------
This charm has a simple unit-test program.  Please expand it and make sure new
changes are covered by simple unit tests.  To run the unit tests:

    sudo apt-get install python-mocker
    sudo apt-get install python-twisted-core
    cd hooks; trial test_hooks

TODO:
-----

  * Expand Single-Service section as I have not tested that mode fully.
  * Trigger website-relation-changed when the reverse-proxy relation changes


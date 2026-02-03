<!-- Remember to update this file for your charm!! -->

# HAProxy release notes – 2.8/stable

These release notes cover new features and changes in HAProxy for revisions
293-314.

Main features:

* Implemented custom external port for gRPC in haproxy-route relation.


Main breaking changes:



Main bug fixes:


See our {ref}`Release policy and schedule <release_notes_index>`.

## Requirements and compatibility

<!--
Specify the workload version; link to the workload's release notes if available.

Add information about the requirements for this charm in the table
below, for instance, a minimum Juju version. 

If the user will need any specific upgrade instructions for this
release, include those instructions here.
-->

The charm operates HAProxy 2.8.

The table below shows the required or supported versions of the software necessary to operate the charm.

| Software                | Required version |
|-------------------------|------------------|
| Juju                    | XXXX             |
| Terraform               | XXXX             |
| Terraform Juju provider | XXXX             |
| Ubuntu                  | XXXX             |
| XXXX                    | XXXX             |







## Updates

The following major and minor features were added in this release.

### Added basic DDoS protection mechanisms with option to disable them.
Added sensible security defaults to prevent basic DDoS attacks.
By default, basic DDoS protection mechanisms are enabled, including
http-request, http-keep-alive and client timeouts, automatic dropping of connections
with invalid, empty, or missing host headers.
A new config option `ddos-protection` has been added to enable basic DDoS protections
if needed.

<Add more context and information about the entry>

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/300)



### Added terraform modules for the HAProxy DDoS Protection configurator charm.
Added terraform modules for the HAProxy DDoS Protection configurator charm in the `charm` and `product` directories.

<Add more context and information about the entry>

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/328)


* [Related documentation]()
* [Related issue]()


### Added terraform for `haproxy-spoe-auth` charm and product.
Refactor terraform/charm, so the modules are under a subdirectory, one per charm.
Add terraform charm module for `haproxy-spoe-auth`.
Update terraform product module to include the options to protect hostnames and
have the option to deploy the `oauth-external-idp-integrator` if the configuration
is given.

<Add more context and information about the entry>

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/316)



### Remove extra slash from _get_backend_proxied_endpoints
Remove extra slash in _get_backend_proxied_endpoints function in `charm.py`. Fixes bug #285

<Add more context and information about the entry>

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/299)

* [Related issue](https://github.com/canonical/haproxy-operator/issues/285)


### Added the provider side of the `ddos-protection` interface.
Added the provider side of the `ddos-protection` interface and introduced a new
validation in the interface provider to ensure that limit policy is not set when the
rate limits are not set.

<Add more context and information about the entry>

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/318)



### Added documentation for `haproxy-spoe-auth`
Now the documentation contains a how-to guide and reference page on using HAProxy as a forward
authentication proxy with OpenID Connect.

<Add more context and information about the entry>

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/315)



### Added path rewrite support for gRPC backends.
Added support for path rewriting in gRPC backends. Used in the same way as path rewrites for HTTP backends, by specifying the 'path_rewrite_expressions' in the `haproxy-route` relation.

<Add more context and information about the entry>

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/329)


* [Related documentation]()
* [Related issue]()


### Added header rewrite support for gRPC backends.
Added support for header rewriting in gRPC backends. Used in the same way as header rewrites for HTTP backends, by specifying the 'header_rewrite_expressions' in the `haproxy-route` relation.

<Add more context and information about the entry>

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/324)


* [Related documentation]()
* [Related issue]()


### Added the `ddos-protection` interface.
Introduced a new interface `ddos-protection` to configure DDoS protection features
in HAProxy.

<Add more context and information about the entry>

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/302)



### Implemented custom external port for gRPC in haproxy-route relation
Added support for custom external port for gRPC services using the config option `external_grpc_port`.

<Add more context and information about the entry>

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/287)








## Bug fixes

* Added missing settings from haproxy-route-tcp relation template ([PR](['https://github.com/canonical/haproxy-operator/pull/325'])).





## Known issues

<!--
Add a bulleted list with links to unresolved issues – the most important/pressing ones,
the ones being worked on currently, or the ones with the most visibility/traffic.
You don’t need to add links to all the issues in the repository if there are
several – a list of 3-5 issues is sufficient. 
If there are no known issues, keep the section and write "No known issues".
-->

## Thanks to our contributors

<!--
List of contributors based on PRs/commits. Remove this section if there are no contributors in this release.
-->

[skatsaounis](https://github.com/skatsaounis), [swetha1654](https://github.com/swetha1654), [javierdelapuente](https://github.com/javierdelapuente), [Alex Lukens](https://github.com/Alex Lukens), [f-atwi](https://github.com/f-atwi)

<!-- Remember to update this file for your charm -- replace <charm-name> with the appropriate name,
follow the release notes policy in the title, and fill in the relevant details. -->

# HAProxy release notes – 2.8/stable

These release notes cover new features and changes in HAProxy for <release condition here>.

<!--
Add an introduction summarizing the most significant features and impactful changes
outlined in this file. Organize this content in bulleted lists of "Main features"
and "Main bug fixes", using past tense to describe each of the items
(for instance, "Added support for X relation").
-->

See our [Release policy and schedule](docs/release-notes/landing-page.md).

## Requirements and compatibility

<!--
Specify the workload version; link to the workload's release notes if available.

Add information about the requirements for this charm in the table
below, for instance, a minimum Juju version. 

If the user will need any specific upgrade instructions for this
release, include those instructions here.

-->

The charm operates <workload name with version>.

The table below shows the required or supported versions of the software necessary to operate the charm.

| Software                | Required version |
|-------------------------|------------------|
| Juju                    | XXXX             |
| Terraform               | XXXX             |
| Terraform Juju provider | XXXX             |
| Ubuntu                  | XXXX             |
| XXXX                    | XXXX             |

## Updates
<!--
Use this section to highlight major and minor features that were added in this release.
The subsection below shows the pattern for each feature. Include links to the relevant PR or commit.
-->

### Allow customization to configure port for HTTP check
Added `check-port` attribute to the requirer databag model, allowing users to customize the port used for `http-check`.
<Add more context and information about the entry>

Relevant links:
* [PR](https://github.com/canonical/haproxy-operator/pull/119)


### Added hosts attribute to requirer data
Requirer application data now includes a `hosts` attribute to allow for the requirer to override the unit IP addresses used to generate server entries in the HAProxy configuration.
<Add more context and information about the entry>

Relevant links:
* [PR](https://github.com/canonical/haproxy-operator/pull/149)


### Validated requirer relation data object
Validation is now done on both the requirer and provider side to check for invalid characters. On the requirer an exception will be raised while on the provider the related service will be ignored.
<Add more context and information about the entry>

Relevant links:
* [PR](https://github.com/canonical/haproxy-operator/pull/118)


### Updated integration tests
The integration tests now only run one unit to save CI time.
<Add more context and information about the entry>

Relevant links:
* [PR](https://github.com/canonical/haproxy-operator/pull/131)


### Updated certifications handling
The charm now requests a new certification for each subdomain during initialization.
<Add more context and information about the entry>

Relevant links:
* [PR](https://github.com/canonical/haproxy-operator/pull/150)


### Added a new relation
Added the `ingress-per-unit` relation to support reaching each unit separately for a Vault deployed behind an ingress.
<Add more context and information about the entry>

Relevant links:
* [PR](https://github.com/canonical/haproxy-operator/pull/153)
* [Related issue](https://github.com/canonical/haproxy-operator/issues/88)


### Updated library to add more attributes
The `subdomain` attribute has been replaced with the `hostname` and `additional_hostnames` attribute. The charm now sends an empty list as the `proxied_endpoints` when the requirer data is ignored.
<Add more context and information about the entry>

Relevant links:
* [PR](https://github.com/canonical/haproxy-operator/pull/152)


### Added first scenario test
Added the first scenario test which kickstarts the transition process from Harness to Scenario.
<Add more context and information about the entry>

Relevant links:
* [PR](https://github.com/canonical/haproxy-operator/pull/108)


### Added terraform charm and product module
You can now deploy HAProxy with high-availability support through Terraform. The module can be found under https://github.com/canonical/haproxy-operator/tree/main/terraform/product
<Add more context and information about the entry>

Relevant links:
* [PR](https://github.com/canonical/haproxy-operator/pull/98)


## Bug fixes
<!--
Add a bulleted list of bug fixes here, with links to the relevant PR/commit.
-->

* Added missing new lines in haproxy-route j2 template and added missing `unit_address` in `provide_haproxy_route_requirements` helper method ([PR](https://github.com/canonical/haproxy-operator/pull/128)).
* Pinned the HAProxy version and prevented automatic updates ([PR](https://github.com/canonical/haproxy-operator/pull/136)).
* Disabled sending host headers in `httpchk` so the charm doesn't refuse to proxy incoming requests ([PR](https://github.com/canonical/haproxy-operator/pull/111)).
* Added checks before reloading the HAProxy service and set the charm to waiting if the validation fails ([PR](https://github.com/canonical/haproxy-operator/pull/122)).
* Added a new dependency to fix the linting step ([PR](https://github.com/canonical/haproxy-operator/pull/105)).
* Fixed Jinja2 handling of newlines to prevent invalid configuration generation ([PR](https://github.com/canonical/haproxy-operator/pull/139)).
* Mitigated bug in Terraform provider by setting subordinate charm units to `1` ([PR](https://github.com/canonical/haproxy-operator/pull/135)).
* Fixed an ambiguous endpoint in an integration test ([PR](https://github.com/canonical/haproxy-operator/pull/129)).


## Breaking changes

<!--
Use this section to highlight any backwards-incompatible changes in this release.
Include links to the relevant PR or commit.
If there are no breaking changes, keep the section and write "No breaking changes".
-->

## Deprecated

<!--
Use this section to highlight any deprecated features in this release.
Include links to the relevant PR or commit.
If there are no deprecated features, keep the section and write "No deprecated features".
-->

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
Thanhphan1147,
erinecon,
Thanhphan1147,
Thanhphan1147,
Thanhphan1147,
Thanhphan1147,
swetha1654,
Thanhphan1147,
Thanhphan1147,
Thanhphan1147,
Thanhphan1147,
Thanhphan1147,
Thanhphan1147,
Thanhphan1147,
Thanhphan1147,
Thanhphan1147,
Thanhphan1147,
Thanhphan1147,




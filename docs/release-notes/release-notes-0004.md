<!-- Remember to update this file for your charm!! -->

# HAProxy release notes – 2.8/stable

These release notes cover new features and changes in HAProxy for revisions
315-330.

Main features:



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

### Added support for wildcard hostnames in haproxy-route relation
Added support for wildcard hostnames (e.g., *.example.com) in the haproxy-route relation. Hostnames can now include a wildcard prefix, allowing a single backend to handle requests for multiple subdomains. The wildcard character (*) cannot be used at the TLD level.
HAProxy configuration now uses '-m end' matching for wildcard hostnames instead of exact matching ('-i'), ensuring proper routing of requests to wildcard domains.
Added the 'validators' library dependency to validate domain names with wildcard support.

<Add more context and information about the entry>

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/364)


* [Related documentation]()
* [Related issue]()


### Fixed issues with the DDoS protection configurator charm found in staging.
Removed "assumes juju >= 3.6" for the HAProxy DDoS protection configurator charm. The HAProxy DDoS protection configurator charm works without requiring Juju version 3.6 or  higher. This change enhances compatibility with earlier Juju versions.
Added the `sc` prefix to the `conn_rate` and `conn_cur` options in the HAProxy template.
Fixed the previous PR's changelog and artifact to accurately reflect requirer instead of provider.

<Add more context and information about the entry>

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/336)


* [Related documentation]()
* [Related issue]()


### Updated issue and enhancement templates
Updated issue and enhancement templates to include impact of the issue / feature.

<Add more context and information about the entry>

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/368)



### Fix remove ca certificate relation where there are still ca certificates.
Instead of removing the cas.pem file when removing a CA relation, call the update_trusted_cas() method. Update the update_trusted_cas() method to check if all CAs have been removed.

<Add more context and information about the entry>

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/358)


* [Related documentation]()
* [Related issue](https://github.com/canonical/haproxy-operator/issues/357)


### Added documentation for the HAProxy DDoS protection configurator charm.
Updated the security documentation to include information about the HAProxy DDoS protection configurator charm and added a "how to" guide for configuring DDoS protection using this charm.

<Add more context and information about the entry>

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/330)


* [Related documentation]()
* [Related issue]()


### Added support for wildcard SNIs in haproxy-route-tcp relation
Added support for wildcard Server Name Indication (SNI) patterns (e.g., *.example.com)  in the haproxy-route-tcp relation. This is a major version bump of the haproxy-route-tcp  library from v0 to v1.
Backends can now use wildcard SNI prefixes to handle connections for multiple subdomains  with a single relation, instead of requiring separate haproxy-route-tcp relations for  each subdomain. The wildcard character (*) cannot be used at the TLD level.
HAProxy configuration now uses '-m end' matching for wildcard SNIs instead of exact  matching ('-i'), ensuring proper routing of TLS connections based on SNI.
Requirer charms using this library must include the 'validators' Python package in their  dependencies (charm-python-packages in charmcraft.yaml) for domain validation.
This change follows the same pattern as PR #364 which added wildcard support for the  haproxy-route relation.

<Add more context and information about the entry>

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/XXXX)


* [Related documentation]()
* [Related issue]()







## Bug fixes






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

[tphan025](https://github.com/tphan025), [swetha1654](https://github.com/swetha1654), [alexdlukens](https://github.com/alexdlukens), [copilot](https://github.com/copilot)

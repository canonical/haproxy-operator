# HAProxy release notes – 2.8/stable

These release notes cover new features and changes in HAProxy for revisions 315-330.

Main features:

- Added support for wildcard Server Name Indication (SNI) patterns (e.g., *.example.com) in the haproxy-route-tcp relation.
- Added support for wildcard hostnames (e.g., *.example.com) in the haproxy-route relation.

Main breaking changes:

- None

Main bug fixes:

- Fix remove ca certificate relation where there are still ca certificates.

See our {ref}`Release policy and schedule <release_notes_index>`.

## Requirements and compatibility

The charm operates HAProxy 2.8.

The table below shows the required or supported versions of the software necessary to operate the charm.

| Software                | Required version |
|-------------------------|------------------|
| Juju                    | 3.6              |
| Terraform               | 1.9              |
| Terraform Juju provider | 1.0              |
| Ubuntu                  | 24.04            |

## Updates

The following major and minor features were added in this release.

### Added support for wildcard hostnames in haproxy-route relation

Added support for wildcard hostnames (e.g., *.example.com) in the haproxy-route relation. Hostnames can now include a wildcard prefix, allowing a single backend to handle requests for multiple subdomains. The wildcard character (*) cannot be used at the TLD level.
HAProxy configuration now uses '-m end' matching for wildcard hostnames instead of exact matching ('-i'), ensuring proper routing of requests to wildcard domains.
Added the 'validators' library dependency to validate domain names with wildcard support.

Relevant links:

- [PR](https://github.com/canonical/haproxy-operator/pull/364)

### Fixed issues with the DDoS protection configurator charm found in staging

Removed "assumes juju >= 3.6" for the HAProxy DDoS protection configurator charm. The HAProxy DDoS protection configurator charm works without requiring Juju version 3.6 or  higher. This change enhances compatibility with earlier Juju versions.
Added the `sc` prefix to the `conn_rate` and `conn_cur` options in the HAProxy template.
Fixed the previous PR's changelog and artifact to accurately reflect requirer instead of provider.

Relevant links:

- [PR](https://github.com/canonical/haproxy-operator/pull/336)

### Updated issue and enhancement templates

Updated issue and enhancement templates to include impact of the issue / feature.

Relevant links:

- [PR](https://github.com/canonical/haproxy-operator/pull/368)

### Added documentation for the HAProxy DDoS protection configurator charm

Updated the security documentation to include information about the HAProxy DDoS protection configurator charm and added a "how to" guide for configuring DDoS protection using this charm.

Relevant links:

- [PR](https://github.com/canonical/haproxy-operator/pull/330)

### Added support for wildcard SNIs in haproxy-route-tcp relation

Added support for wildcard Server Name Indication (SNI) patterns (e.g., *.example.com)  in the haproxy-route-tcp relation. This is a major version bump of the haproxy-route-tcp  library from v0 to v1.
Backends can now use wildcard SNI prefixes to handle connections for multiple subdomains  with a single relation, instead of requiring separate haproxy-route-tcp relations for  each subdomain. The wildcard character (*) cannot be used at the TLD level.
HAProxy configuration now uses '-m end' matching for wildcard SNIs instead of exact  matching ('-i'), ensuring proper routing of TLS connections based on SNI.
Requirer charms using this library must include the 'validators' Python package in their  dependencies (charm-python-packages in charmcraft.yaml) for domain validation.
This change follows the same pattern as PR #364 which added wildcard support for the  haproxy-route relation.

Relevant links:

- [PR](https://github.com/canonical/haproxy-operator/pull/XXXX)

## Bug fixes

### Fix remove ca certificate relation where there are still ca certificates

Instead of removing the cas.pem file when removing a CA relation, call the update_trusted_cas() method. Update the update_trusted_cas() method to check if all CAs have been removed.

Relevant links:

- [PR](https://github.com/canonical/haproxy-operator/pull/358)
- [Related issue](https://github.com/canonical/haproxy-operator/issues/357)

## Thanks to our contributors

[tphan025](https://github.com/tphan025), [swetha1654](https://github.com/swetha1654), [alexdlukens](https://github.com/alexdlukens)

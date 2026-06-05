<!-- Remember to update this file for your charm!! -->

# HAProxy release notes – 2.8/stable

These release notes cover new features and changes in HAProxy for revisions
340-392.

Main features:

- Added wildcard hostname and wildcard SNI support for `haproxy-route` and `haproxy-route-tcp` integrations.
- Introduced `haproxy-route-policy` and `haproxy-route-policy-operator` with requests/rules APIs, authentication, PostgreSQL backend, and snap packaging.
- Added policy relation provider support and improved HTTPS backend health checks with `check-alpn`.

Main breaking changes:

- None

Main bug fixes:

- Fixed host validation in the `haproxy-route` and `haproxy-route-tcp` libraries.


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
| Juju                    | 3.6              |
| Terraform               | 1.9              |
| Terraform Juju provider | 1.0              |
| Ubuntu                  | 24.04            |

## Updates

The following major and minor features were added in this release.

### Bootstrapped MVP for haproxy-route-policy-operator charm
Added a new machine charm, `haproxy-route-policy-operator`, as an MVP to manage the haproxy-route-policy service. The charm installs and configures the `haproxy-route-policy` snap from PostgreSQL relation data, runs database migrations, starts the gunicorn snap service, and opens port 8080. Included charm metadata/configuration, PostgreSQL relation handling state, supporting policy helpers, vendored data-platform relation library, and initial unit and integration tests.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/421)




### Added snap packaging and runtime scripts for haproxy-route-policy
Added snap packaging for the haproxy-route-policy app, including `snap/snapcraft.yaml`, install/configure hooks, and helper scripts to run Gunicorn and Django management commands with snap configuration values. Added Gunicorn as a dependency and configured uv build metadata in `pyproject.toml` for packaging. Updated the app README with a basic setup flow for PostgreSQL and snap configuration.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/415)




### Added check-alpn to HTTPS backend server configuration
Updated the HAProxy route backend server configuration for HTTPS upstreams to include `check-alpn h2,http/1.1` together with `alpn h2,http/1.1`. This ensures health checks negotiate ALPN consistently with HTTPS backend connections. Refactored backend/server configuration rendering to use computed properties in state models and updated unit tests to cover HTTPS behavior with and without explicit health checks.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/452)




### Added support for wildcard hostnames in haproxy-route relation
Added support for wildcard hostnames (e.g., *.example.com) in the haproxy-route relation. Hostnames can now include a wildcard prefix, allowing a single backend to handle requests for multiple subdomains. The wildcard character (*) cannot be used at the TLD level.
HAProxy configuration now uses '-m end' matching for wildcard hostnames instead of exact matching ('-i'), ensuring proper routing of requests to wildcard domains.
Added the 'validators' library dependency to validate domain names with wildcard support.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/364)




### Added allowed-hosts configuration support to haproxy-route-policy-operator
Added a new `allowed-hosts` charm configuration option for `haproxy-route-policy-operator` and wired it into snap configuration as a JSON-encoded `DJANGO_ALLOWED_HOSTS` value. Introduced a dedicated policy state module to centralize shared operator information (allowed hosts, admin credentials, secret key), including validation of hostnames/IP addresses. Updated charm reconcile flow to consume the new state model and refined leader/non-leader behavior for migration and admin-user updates. Added unit tests for allowed-hosts validation/serialization and updated charm unit tests for the new peer/state behavior.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/423)




### Added authentication to haproxy-route-policy REST API
Configured Django REST Framework with JWT and session-based authentication as default authentication classes, requiring all API endpoints to be accessed by authenticated users. Added test_settings_authenticated.py for auth-enabled tests, a dedicated unit-auth tox environment, and integration tests verifying that unauthenticated requests are rejected and authenticated requests succeed. Added djangorestframework-simplejwt as a dependency.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/412)




### Added haproxy-route-policy relation provider interface to route-policy operator
Added a new `haproxy-route-policy` provided relation on `haproxy-route-policy-operator`, including a new charm library for requirer/provider data schemas and validation. Added basic logic and tests.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/451)




### Added rules management REST API for haproxy-route-policy app
Added the Rule model with UUID primary key and fields for kind, value, action, priority, and comment. Implemented REST API endpoints for rules: GET /api/v1/rules (list ordered by descending priority), POST /api/v1/rules (create with validation), GET /api/v1/rules/<uuid> (retrieve by ID), PUT /api/v1/rules/<uuid> (partial update), and DELETE /api/v1/rules/<uuid> (idempotent delete). Added RuleSerializer with custom validation for hostname_and_path_match rules including hostname and path checks. Included unit and integration tests for the Rule model and API views.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/400)




### Added requests management REST API for haproxy-route-policy app
Added the policy Django app with a BackendRequest model and REST API endpoints for managing backend requests. Implemented GET /api/v1/requests (list with optional status filter), POST /api/v1/requests (bulk create with all requests set to pending), GET /api/v1/requests/<id> (retrieve by ID), and DELETE /api/v1/requests/<id> (idempotent delete). Included hostname validation, test settings with in-memory SQLite, and unit and integration tests for models and views.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/399)




### Added support for wildcard SNIs in haproxy-route-tcp relation
Added support for wildcard Server Name Indication (SNI) patterns (e.g., *.example.com)  in the haproxy-route-tcp relation. This is a major version bump of the haproxy-route-tcp  library from v0 to v1.
Backends can now use wildcard SNI prefixes to handle connections for multiple subdomains  with a single relation, instead of requiring separate haproxy-route-tcp relations for  each subdomain. The wildcard character (*) cannot be used at the TLD level.
HAProxy configuration now uses '-m end' matching for wildcard SNIs instead of exact  matching ('-i'), ensuring proper routing of TLS connections based on SNI.
Requirer charms using this library must include the 'validators' Python package in their  dependencies (charm-python-packages in charmcraft.yaml) for domain validation.
This change follows the same pattern as PR #364 which added wildcard support for the  haproxy-route relation.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/371)




### Publish proxied endpoints for haproxy-route-tcp frontends
Added publishing of proxied endpoints for haproxy-route-tcp relations. For SNI-enabled frontends, endpoints are published as "<sni>:<port>". For non-SNI frontends, endpoints use the HA VIP when available or fallback to peer unit addresses. The haproxy-route-tcp library now uses string endpoints instead of AnyUrl.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/384)




### Added rule matching engine and request evaluation on creation
Added a rule matching engine that evaluates backend requests against rules ordered by descending priority. Within the same priority group, deny rules take precedence over allow rules. Integrated the engine into the bulk create endpoint so that each new request is evaluated immediately and its status is set to accepted, rejected, or pending accordingly. Included unit tests for the matching logic and integration tests for rule evaluation during request creation.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/401)




### Updated issue and enhancement templates
Updated issue and enhancement templates to include impact of the issue / feature.

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/368)



### Switched haproxy-route-policy database backend to PostgreSQL
Changed the default database backend from SQLite to PostgreSQL with environment-variable-based configuration for host, port, user, password, and database name. Added psycopg2-binary as a project dependency.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/413)




### Added leader-managed Django secrets and admin user bootstrap for route-policy operator
Updated the `haproxy-route-policy-operator` charm to generate and share Django runtime secrets from the leader unit, including a secret key and admin credentials. During reconcile, the charm now configures the snap with the generated secret key and upserts the Django admin user via the snap management command. Non-leader units now wait until shared secrets are available. Added unit tests covering reconcile behavior with existing, missing, and leader-generated secrets.

Relevant links:


* [PR](https://github.com/canonical/haproxy-operator/pull/422)









## Bug fixes

* Fix hosts validation in haproxy-route-tcp, and haproxy-route relation libraries ([PR](https://github.com/canonical/haproxy-operator/pull/383)).





## Known issues

<!--
Add a bulleted list with links to unresolved issues – the most important/pressing ones,
the ones being worked on currently, or the ones with the most visibility/traffic.
You don’t need to add links to all the issues in the repository if there are
several – a list of 3-5 issues is sufficient. 
If there are no known issues, keep the section and write "No known issues".
-->

No known issues.

## Thanks to our contributors

<!--
List of contributors based on PRs/commits. Remove this section if there are no contributors in this release.
-->

[tphan025](https://github.com/tphan025), [skatsaounis](https://github.com/skatsaounis), [copilot](https://github.com/copilot), [swetha1654](https://github.com/swetha1654)

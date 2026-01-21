<!-- Remember to update this file for your charm!! -->

# HAProxy release notes – 2.8/stable

These release notes cover new features and changes in HAProxy for revisions
284-290.

Main features:

* Implemented spoe-auth relation in HAproxy.


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

### Implemented spoe-auth relation in HAproxy
Implementation of the spoe-auth in HAProxy.

<Add more context and information about the entry>

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/279)



### Created HAProxy DDoS Protection Configurator charm
Creates the skeleton code for the HAProxy DDoS Protection Configurator charm. This charm 
serves as a configurator for HAProxy to provide DDoS protection capabilities.

<Add more context and information about the entry>

Relevant links:

* [PR](https://github.com/canonical/haproxy-operator/pull/284)








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

[javierdelapuente](https://github.com/javierdelapuente), [swetha1654](https://github.com/swetha1654)

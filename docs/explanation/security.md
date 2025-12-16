(explanation_security)=

# Security

This document describes the security design of the HAProxy charm.
The charm manages an [HAProxy](https://www.haproxy.org/) as an ingress proxy.
This document will detail the risks and good practices of operating the charm.

## Outdated dependencies

Outdated dependencies can contain known vulnerabilities for attackers to exploit.

### Good practices

The dependencies used by the charm are tied to the charm revision.
Updating the charm will ensure the latest version of the dependencies are used.

Using the latest version of Juju will ensure the latest security fix for Juju is applied as well.

### Summary

- Regularly update the charm revision.
- Regularly update the Juju version.

## Machine-in-the-middle attack

This type of attack refers to an attacker intercepting messages and pretending to be the intended recipient of the message.
For example, if an user tries to access `ubuntu.com`, an attacker might intercept the packets and pretend to be `ubuntu.com`, and trick the user into reveal their password.
Prevent this attack by using TLS certificates to validate the identity of the recipient.

As an ingress proxy, clients would be sending requests to the charm.
Encrypting these requests would help to prevent any machine-in-the-middle attack.

### Good practices

Encryption can be achieved by giving a TLS certificate to the charm, configuring it to accept an HTTPS request over an unencrypted HTTP request.
TLS certificate can be provided through the [`certificates` integration](https://charmhub.io/haproxy/integrations?channel=2.8/edge) to the HAProxy charm.

### Summary

- Use TLS certificates to encrypt traffic.

<!-- vale Canonical.007-Headings-sentence-case = NO -->
## Denial-of-service (DoS) attack
<!-- vale Canonical.007-Headings-sentence-case = YES -->

This type of attack refers to attackers overloading a service by issuing many requests in a short period of time.
Attackers hope to exhaust the service's resources, e.g., memory and CPU cycles.

The common way to deal with this type of attack is by limiting the number of requests for each IP address.
While it does not prevent all DoS attacks depending on the scale of the attack, it is generally an effective mitigation strategy.

### Good practices

The charm offers a configuration to set the maximum concurrent connection. This can prevent the charm from crashing due to high loads.

### Summary

- Set a reasonable maximum concurrent connection using the [`global-maxconn` charm configuration](https://charmhub.io/haproxy/configurations?channel=2.8/edge#global-maxconn).

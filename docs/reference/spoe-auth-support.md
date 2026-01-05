(reference_spoe-auth_support)=

# HAProxy forward authentication proxy using OpenID Connect

The HAProxy operator provides support for authenticating hostnames using
[HAProxy SPOE Authentication](https://github.com/criteo/haproxy-spoe-auth)
with OpenID Connect.

To protect a hostname exposed via the `haproxy-route` integration,
relate the `haproxy` charm with the [`haproxy-spoe-auth`](https://charmhub.io/haproxy-spoe-auth)
charm.

## Limitations

- Only hostnames provided by the `haproxy-route` relation can be protected with SPOE authentication.
- No user information is passed to backend services.
- Only OpenID Connect is supported; no claims are validated.
- The authentication cookie name is hardcoded to `auth_session`.

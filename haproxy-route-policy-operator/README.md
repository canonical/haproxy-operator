# HAProxy route policy operator

Machine charm for the HAProxy Route Policy service.

This charm:

- requires a `postgresql` relation using `postgresql_client`
- installs and configures the `haproxy-route-policy` snap
- runs first-time database migrations
- starts and keeps the snap gunicorn service running

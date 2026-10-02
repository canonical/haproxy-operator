(how_to_upgrade)=

# How to upgrade

Upgrade the charm with the `juju refresh` command.
For example, to upgrade `haproxy` along the `2.8/edge` channel, use:

```bash
juju refresh haproxy --channel=2.8/edge
```

The charm is stateless, so you don't need to perform a data backup
before upgrading.

Breaking changes aren't introduced in subsequent revisions in a given `channel`.
As long as you upgrade using the same `channel`, all configurations and
relations should remain intact between `haproxy` and the other charms
in your deployment.

from ops import testing

from charm import HAProxyDDoSProtectionConfiguratorCharm


def test_base():
    ctx = testing.Context(HAProxyDDoSProtectionConfiguratorCharm)
    state = testing.State(leader=True)
    out = ctx.run(ctx.on.start(), state)
    assert out.unit_status == testing.ActiveStatus()

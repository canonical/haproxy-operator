# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""More tests for haproxy-operator"""

from unittest.mock import MagicMock
import pytest

from ops.testing import ActiveStatus
from ops.testing import Relation, State, WaitingStatus, TCPPort, Model, Context

from charm import HAProxyCharm as CHARM_TYPE


@pytest.fixture
def mocks(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("haproxy.HAProxyService.install", MagicMock())
    monkeypatch.setattr("haproxy.render_file", MagicMock())
    monkeypatch.setattr("haproxy.HAProxyService._validate_haproxy_config", MagicMock())


def test_case(systemd_mock: None, mocks: None):
    # Arrange: prepare the state
    state = State(
        config={"external-hostname": "fqdn.example", "global-maxconn": 4096},
        relations=frozenset(
            {
                Relation(
                    endpoint="haproxy-route",
                    interface="haproxy-route",
                    id=8,
                    local_app_data={},
                    local_unit_data={},
                    remote_app_name="ingress-configurator",
                    limit=1,
                    remote_app_data={
                        "hosts": '["1.1.1.1"]',
                        "ports": "[80]",
                        "protocol": '"https"',
                        "service": '"lexi-ingress-configurator"',
                    },
                    remote_units_data={1: {"address": '"10.56.206.24"'}},
                ),
                Relation(
                    endpoint="certificates",
                    interface="tls-certificates",
                    id=7,
                    local_app_data={},
                    local_unit_data={
                        "certificate_signing_requests": '[{"certificate_signing_request": "-----BEGIN CERTIFICATE REQUEST-----\\nMIICtTCCAZ0CAQAwRjEVMBMGA1UEAwwMZnFkbi5leGFtcGxlMS0wKwYDVQQtDCRm\\nZmMyNzQ3MS1jMTc4LTQzOTgtYmZmNi0yNmQ1YmY2ZTNiYmYwggEiMA0GCSqGSIb3\\nDQEBAQUAA4IBDwAwggEKAoIBAQC/LjPWzQm2F+CCqIwbQ7S1iGKq2zZW+nNxyRFk\\n2FjXQvSxif2xdH8h+vdh/KBn0WetCEGMbPo1Gikv++MIvvsZk3WM8on4+ljEe6i+\\n1xhK61Jnxji+xl/yOtS9JS50VY+sokIVkpW403r1/Hzjtncr/5ff6eBcJ2uigt/3\\nmv18QRmJERzYyM5VqUY4R6JelEFl67yijpQOVKr1DsHiUYrXBSLxQ0phr0Q2jjL5\\ngyrbE910Rt5OdwTt/yOBhsqHWV5Fx8J/4zJm4D6f8Ohob5E8yG2HV3U1KG1qqXqV\\n56CIBqx0eZQalH4dL6MGLUiC893+lgF7fWiI8YnLzP7sPyLnAgMBAAGgKjAoBgkq\\nhkiG9w0BCQ4xGzAZMBcGA1UdEQQQMA6CDGZxZG4uZXhhbXBsZTANBgkqhkiG9w0B\\nAQsFAAOCAQEAEXTSjGqs7itBgfMUT50a5WFqr86BfkYs7oLWfR/1hP0b5I60qrLz\\nlLieZ/uYz7L/8fz1VoaavI3ciX4LtjW2RAtTG7Fqx9uPolwveiBK+xyH067Ij01/\\nsIqi+fj7O4lx+cggI9IS6GzlQPJ37h348Asg3jo1tyxDR3w0D17pWLhSz6d6KLSU\\nnedc3lomFq28h76hUew48y6qMbvP/XY5oXTDkNFv8/ilxRX2EulvZY+CCpLlmB0O\\ne7rYUmjHdyidAZyzK8Kkt4f9BYJsH31s07Y50zRV3u3atvz2un+FoOrvLcNc4MSp\\nYteoYWWk0Ey13IYlwY3Q9IoWINUw1BsJFw==\\n-----END CERTIFICATE REQUEST-----", "ca": false}]'
                    },
                    remote_app_name="self-signed-certificates",
                    limit=1,
                    remote_app_data={
                        "certificates": '[{"ca": "-----BEGIN CERTIFICATE-----\\nMIIDTTCCAjWgAwIBAgIUN2mVv5+H7t0i3hAe06udfblztkswDQYJKoZIhvcNAQEL\\nBQAwLDEqMCgGA1UEAwwhc2VsZi1zaWduZWQtY2VydGlmaWNhdGVzLW9wZXJhdG9y\\nMB4XDTI1MDgwNTA1NDEwMFoXDTI2MDgwNTA1NDEwMFowLDEqMCgGA1UEAwwhc2Vs\\nZi1zaWduZWQtY2VydGlmaWNhdGVzLW9wZXJhdG9yMIIBIjANBgkqhkiG9w0BAQEF\\nAAOCAQ8AMIIBCgKCAQEAyJ9YZBAZrJfqhmMlbxX827B9Zu4cIAwLRLoLwcB+aucL\\nqZjpCn4qz4SQg/VXrEnKpNs18JtcvmehPwy8FaL6e2Ss3fb4BhbCQ5wwmU+Urrkb\\nPiK34kgn2h1bSRDe+lCuBS9Cw4Amrfgvm0qrWzVkhbhaUnoB+Q8K9oiOu41W+YJM\\n6BTw8CBOAledVoOf8Z1NyCfpFbAbSQaXPpaquUKQugQokzqBfLFU4LHOQNfhNlSb\\n5MZNctMXb6Wss+YAHMI0BgrHPQDswB20yOWVALZp8eQJ/hgV7+uYs044sfEfQsKQ\\nc2FiogqQl6VfJbAWX+AiN/elNTejiv/99/n+IFqAgQIDAQABo2cwZTAfBgNVHQ4E\\nGAQWBBT1vWAgwk/eadV65PGhrJ25/wJdIzAhBgNVHSMEGjAYgBYEFPW9YCDCT95p\\n1Xrk8aGsnbn/Al0jMA4GA1UdDwEB/wQEAwICpDAPBgNVHRMBAf8EBTADAQH/MA0G\\nCSqGSIb3DQEBCwUAA4IBAQAG5DoW4Y6878CaVBUTT6gO/YoS1gJGNew5eNyAbD4l\\nEI2PjICYm+XqISOtdneexeZxqBZ2sqllEmLZqWbFJgJZtjenBkQZC9zLdJKWr7GW\\nQqtZZUo4hZ2Ed0bBidZw4zCQZ+MiWad7hRQfHuHQyhZPPxbA7CzKEV12UN6dJfFd\\nw41a2EoXXl2ZEa4KiNUvMYrpPVW8y6uailjEb/MzId0LFiGiygOKoHsTYUqg77Vs\\nkcdFEAWJNpzqEMN/xecmEEEqmM4cWViphLnmahOJkmV16h89UR+n36STXF0SAt82\\nxMrQ6BDmFG+D+y+BBbs3wN35x++5CgPv/wzTqea7hSgu\\n-----END CERTIFICATE-----", "certificate_signing_request": "-----BEGIN CERTIFICATE REQUEST-----\\nMIICtTCCAZ0CAQAwRjEVMBMGA1UEAwwMZnFkbi5leGFtcGxlMS0wKwYDVQQtDCRm\\nZmMyNzQ3MS1jMTc4LTQzOTgtYmZmNi0yNmQ1YmY2ZTNiYmYwggEiMA0GCSqGSIb3\\nDQEBAQUAA4IBDwAwggEKAoIBAQC/LjPWzQm2F+CCqIwbQ7S1iGKq2zZW+nNxyRFk\\n2FjXQvSxif2xdH8h+vdh/KBn0WetCEGMbPo1Gikv++MIvvsZk3WM8on4+ljEe6i+\\n1xhK61Jnxji+xl/yOtS9JS50VY+sokIVkpW403r1/Hzjtncr/5ff6eBcJ2uigt/3\\nmv18QRmJERzYyM5VqUY4R6JelEFl67yijpQOVKr1DsHiUYrXBSLxQ0phr0Q2jjL5\\ngyrbE910Rt5OdwTt/yOBhsqHWV5Fx8J/4zJm4D6f8Ohob5E8yG2HV3U1KG1qqXqV\\n56CIBqx0eZQalH4dL6MGLUiC893+lgF7fWiI8YnLzP7sPyLnAgMBAAGgKjAoBgkq\\nhkiG9w0BCQ4xGzAZMBcGA1UdEQQQMA6CDGZxZG4uZXhhbXBsZTANBgkqhkiG9w0B\\nAQsFAAOCAQEAEXTSjGqs7itBgfMUT50a5WFqr86BfkYs7oLWfR/1hP0b5I60qrLz\\nlLieZ/uYz7L/8fz1VoaavI3ciX4LtjW2RAtTG7Fqx9uPolwveiBK+xyH067Ij01/\\nsIqi+fj7O4lx+cggI9IS6GzlQPJ37h348Asg3jo1tyxDR3w0D17pWLhSz6d6KLSU\\nnedc3lomFq28h76hUew48y6qMbvP/XY5oXTDkNFv8/ilxRX2EulvZY+CCpLlmB0O\\ne7rYUmjHdyidAZyzK8Kkt4f9BYJsH31s07Y50zRV3u3atvz2un+FoOrvLcNc4MSp\\nYteoYWWk0Ey13IYlwY3Q9IoWINUw1BsJFw==\\n-----END CERTIFICATE REQUEST-----", "certificate": "-----BEGIN CERTIFICATE-----\\nMIIDazCCAlOgAwIBAgIUFYBBQ8VHHT+onBzrVv9Z3hBPfaEwDQYJKoZIhvcNAQEL\\nBQAwLDEqMCgGA1UEAwwhc2VsZi1zaWduZWQtY2VydGlmaWNhdGVzLW9wZXJhdG9y\\nMB4XDTI1MDgwNTA2NDAzNloXDTI1MTEwMzA2NDAzNlowRjEVMBMGA1UEAwwMZnFk\\nbi5leGFtcGxlMS0wKwYDVQQtDCRmZmMyNzQ3MS1jMTc4LTQzOTgtYmZmNi0yNmQ1\\nYmY2ZTNiYmYwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC/LjPWzQm2\\nF+CCqIwbQ7S1iGKq2zZW+nNxyRFk2FjXQvSxif2xdH8h+vdh/KBn0WetCEGMbPo1\\nGikv++MIvvsZk3WM8on4+ljEe6i+1xhK61Jnxji+xl/yOtS9JS50VY+sokIVkpW4\\n03r1/Hzjtncr/5ff6eBcJ2uigt/3mv18QRmJERzYyM5VqUY4R6JelEFl67yijpQO\\nVKr1DsHiUYrXBSLxQ0phr0Q2jjL5gyrbE910Rt5OdwTt/yOBhsqHWV5Fx8J/4zJm\\n4D6f8Ohob5E8yG2HV3U1KG1qqXqV56CIBqx0eZQalH4dL6MGLUiC893+lgF7fWiI\\n8YnLzP7sPyLnAgMBAAGjazBpMCEGA1UdIwQaMBiAFgQU9b1gIMJP3mnVeuTxoayd\\nuf8CXSMwHQYDVR0OBBYEFKHtvtELswbxn+Kijg/pUSS6CLy9MAwGA1UdEwEB/wQC\\nMAAwFwYDVR0RBBAwDoIMZnFkbi5leGFtcGxlMA0GCSqGSIb3DQEBCwUAA4IBAQAB\\nhPFXayF99mHU9m68fxFq9WJhpCuD1aT518dH35K2RMmPNq7Rh1f7yZvyGiTGWlK4\\n0UiWBzZPuO6BAHvts1PNWhDAXNxDDVC5bbloAii46Ii6pJa/wDsYclVgiX0CQwCh\\neyKy2iN5qC5B2hpi5qyqGDG1fqynFQkZrlOyuGVlAjP7MXRtzb0vDZko5izvwm0S\\nLQCpSx96oa8CBw76xedAUk/3D5BjlsjVMsgrbMGIjREdXKLDupplY2RNt6n2u2B+\\nGEBqiDQSA6ETOMhS5ypaGRceQ6bbIk/z/DeVuFpN6u6RYfV+Q3rbGMBBvj38LUeB\\nDd9TI0MoN5MwDzDcLl3n\\n-----END CERTIFICATE-----", "chain": ["-----BEGIN CERTIFICATE-----\\nMIIDazCCAlOgAwIBAgIUFYBBQ8VHHT+onBzrVv9Z3hBPfaEwDQYJKoZIhvcNAQEL\\nBQAwLDEqMCgGA1UEAwwhc2VsZi1zaWduZWQtY2VydGlmaWNhdGVzLW9wZXJhdG9y\\nMB4XDTI1MDgwNTA2NDAzNloXDTI1MTEwMzA2NDAzNlowRjEVMBMGA1UEAwwMZnFk\\nbi5leGFtcGxlMS0wKwYDVQQtDCRmZmMyNzQ3MS1jMTc4LTQzOTgtYmZmNi0yNmQ1\\nYmY2ZTNiYmYwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC/LjPWzQm2\\nF+CCqIwbQ7S1iGKq2zZW+nNxyRFk2FjXQvSxif2xdH8h+vdh/KBn0WetCEGMbPo1\\nGikv++MIvvsZk3WM8on4+ljEe6i+1xhK61Jnxji+xl/yOtS9JS50VY+sokIVkpW4\\n03r1/Hzjtncr/5ff6eBcJ2uigt/3mv18QRmJERzYyM5VqUY4R6JelEFl67yijpQO\\nVKr1DsHiUYrXBSLxQ0phr0Q2jjL5gyrbE910Rt5OdwTt/yOBhsqHWV5Fx8J/4zJm\\n4D6f8Ohob5E8yG2HV3U1KG1qqXqV56CIBqx0eZQalH4dL6MGLUiC893+lgF7fWiI\\n8YnLzP7sPyLnAgMBAAGjazBpMCEGA1UdIwQaMBiAFgQU9b1gIMJP3mnVeuTxoayd\\nuf8CXSMwHQYDVR0OBBYEFKHtvtELswbxn+Kijg/pUSS6CLy9MAwGA1UdEwEB/wQC\\nMAAwFwYDVR0RBBAwDoIMZnFkbi5leGFtcGxlMA0GCSqGSIb3DQEBCwUAA4IBAQAB\\nhPFXayF99mHU9m68fxFq9WJhpCuD1aT518dH35K2RMmPNq7Rh1f7yZvyGiTGWlK4\\n0UiWBzZPuO6BAHvts1PNWhDAXNxDDVC5bbloAii46Ii6pJa/wDsYclVgiX0CQwCh\\neyKy2iN5qC5B2hpi5qyqGDG1fqynFQkZrlOyuGVlAjP7MXRtzb0vDZko5izvwm0S\\nLQCpSx96oa8CBw76xedAUk/3D5BjlsjVMsgrbMGIjREdXKLDupplY2RNt6n2u2B+\\nGEBqiDQSA6ETOMhS5ypaGRceQ6bbIk/z/DeVuFpN6u6RYfV+Q3rbGMBBvj38LUeB\\nDd9TI0MoN5MwDzDcLl3n\\n-----END CERTIFICATE-----", "-----BEGIN CERTIFICATE-----\\nMIIDTTCCAjWgAwIBAgIUN2mVv5+H7t0i3hAe06udfblztkswDQYJKoZIhvcNAQEL\\nBQAwLDEqMCgGA1UEAwwhc2VsZi1zaWduZWQtY2VydGlmaWNhdGVzLW9wZXJhdG9y\\nMB4XDTI1MDgwNTA1NDEwMFoXDTI2MDgwNTA1NDEwMFowLDEqMCgGA1UEAwwhc2Vs\\nZi1zaWduZWQtY2VydGlmaWNhdGVzLW9wZXJhdG9yMIIBIjANBgkqhkiG9w0BAQEF\\nAAOCAQ8AMIIBCgKCAQEAyJ9YZBAZrJfqhmMlbxX827B9Zu4cIAwLRLoLwcB+aucL\\nqZjpCn4qz4SQg/VXrEnKpNs18JtcvmehPwy8FaL6e2Ss3fb4BhbCQ5wwmU+Urrkb\\nPiK34kgn2h1bSRDe+lCuBS9Cw4Amrfgvm0qrWzVkhbhaUnoB+Q8K9oiOu41W+YJM\\n6BTw8CBOAledVoOf8Z1NyCfpFbAbSQaXPpaquUKQugQokzqBfLFU4LHOQNfhNlSb\\n5MZNctMXb6Wss+YAHMI0BgrHPQDswB20yOWVALZp8eQJ/hgV7+uYs044sfEfQsKQ\\nc2FiogqQl6VfJbAWX+AiN/elNTejiv/99/n+IFqAgQIDAQABo2cwZTAfBgNVHQ4E\\nGAQWBBT1vWAgwk/eadV65PGhrJ25/wJdIzAhBgNVHSMEGjAYgBYEFPW9YCDCT95p\\n1Xrk8aGsnbn/Al0jMA4GA1UdDwEB/wQEAwICpDAPBgNVHRMBAf8EBTADAQH/MA0G\\nCSqGSIb3DQEBCwUAA4IBAQAG5DoW4Y6878CaVBUTT6gO/YoS1gJGNew5eNyAbD4l\\nEI2PjICYm+XqISOtdneexeZxqBZ2sqllEmLZqWbFJgJZtjenBkQZC9zLdJKWr7GW\\nQqtZZUo4hZ2Ed0bBidZw4zCQZ+MiWad7hRQfHuHQyhZPPxbA7CzKEV12UN6dJfFd\\nw41a2EoXXl2ZEa4KiNUvMYrpPVW8y6uailjEb/MzId0LFiGiygOKoHsTYUqg77Vs\\nkcdFEAWJNpzqEMN/xecmEEEqmM4cWViphLnmahOJkmV16h89UR+n36STXF0SAt82\\nxMrQ6BDmFG+D+y+BBbs3wN35x++5CgPv/wzTqea7hSgu\\n-----END CERTIFICATE-----"]}]'
                    },
                    remote_units_data={0: {}},
                ),
            }
        ),
        # networks=frozenset( {"certificates", "haproxy-peers", "juju-info", "haproxy-route"}),
        containers=frozenset(),
        storages=frozenset(),
        opened_ports=frozenset({TCPPort(port=80, protocol="tcp")}),
        leader=False,
        model=Model(
            name="lexi",
            uuid="bbd03f86-3631-4ca4-8b5f-4044f38b88ce",
            type="lxd",
            cloud_spec=None,
        ),
        secrets=frozenset(),
        resources=frozenset(),
        planned_units=1,
        deferred=[],
        stored_states=frozenset(),
        app_status=WaitingStatus("Failed validating the HAProxy config."),
        unit_status=WaitingStatus("Failed validating the HAProxy config."),
        workload_version="",
    )

    # Act: trigger an event on the state
    ctx = Context(
        CHARM_TYPE, juju_version="3.6.8"  # TODO: replace with charm type name,
    )

    out = ctx.run(
        ctx.on.config_changed(),
        state,
    )

    assert out.app_status == ActiveStatus("")

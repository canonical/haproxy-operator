# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""More tests for haproxy-operator"""

from unittest.mock import MagicMock
import pytest

from ops.testing import ActiveStatus
from ops.testing import Relation, State, TCPPort, Model, Context

from charm import HAProxyCharm


@pytest.fixture
def mocks(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("haproxy.pin_haproxy_package_version", MagicMock())
    monkeypatch.setattr("haproxy.HAProxyService._validate_haproxy_config", MagicMock())


@pytest.mark.usefixtures("systemd_mock")
def test_case(mocks: None, monkeypatch: pytest.MonkeyPatch):
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)

    # Arrange: prepare the state
    haproxy_route_relation = Relation(
        endpoint="haproxy-route",
        interface="haproxy-route",
        id=7,
        local_app_data={"endpoints": '["https://haproxy.internal/"]'},
        local_unit_data={},
        remote_app_name="ingress-configurator",
        limit=1,
        remote_app_data={
            "hostname": '"haproxy.internal"',
            "hosts": '["10.12.97.153","10.12.97.154"]',
            "ports": "[443]",
            "protocol": '"https"',
            "service": '"haproxy-tutorial-ingress-configurator"',
        },
        remote_units_data={0: {"address": '"10.75.1.129"'}}
    )

    state = State(
        config={"global-maxconn": 4096},
        relations=frozenset(
            {
                haproxy_route_relation,
                Relation(
                    endpoint="certificates",
                    interface="tls-certificates",
                    id=2,
                    local_app_data={},
                    local_unit_data={
                        "certificate_signing_requests": RANDOM_CERTIFICATES_SIGNING_REQUESTS,
                    },
                    remote_app_name="cert",
                    limit=1,
                    remote_app_data={
                        "certificates": RANDOM_CERTIFICATES,
                    },
                    remote_units_data={0: {}},
                ),
            }
        ),
        containers=frozenset(),
        storages=frozenset(),
        opened_ports=frozenset(
            {TCPPort(port=443, protocol="tcp"), TCPPort(port=80, protocol="tcp")}
        ),
        leader=False,
        model=Model(
            name="haproxy-tutorial",
            uuid="b3c6eb18-f565-4d9c-8da2-603a3e846016",
            type="lxd",
            cloud_spec=None,
        ),
        secrets=frozenset(),
        resources=frozenset(),
        planned_units=1,
        deferred=[],
        stored_states=frozenset(),
        app_status=ActiveStatus(""),
        unit_status=ActiveStatus(""),
        workload_version="",
    )
    # Act: trigger an event on the state
    ctx = Context(
        HAProxyCharm, juju_version="3.6.8"
    )

    out = ctx.run(
        ctx.on.relation_changed(haproxy_route_relation),
        state,
    )

    render_file_mock.assert_called_once()
    haproxy_conf_contents = render_file_mock.call_args_list[0].args[1]
    assert "server haproxy-tutorial-ingress-configurator_443_0 10.12.97.153:443 check inter 60s rise 2 fall 3 ssl ca-file @system-ca\n" in haproxy_conf_contents
    assert "server haproxy-tutorial-ingress-configurator_443_1 10.12.97.154:443 check inter 60s rise 2 fall 3 ssl ca-file @system-ca\n" in haproxy_conf_contents
    assert out.app_status == ActiveStatus("")

RANDOM_CERTIFICATES_SIGNING_REQUESTS="""
[
   {
      "certificate_signing_request":"-----BEGIN CERTIFICATE REQUEST-----\\nMIICvTCCAaUCAQAwSjEZMBcGA1UEAwwQaGFwcm94eS5pbnRlcm5hbDEtMCsGA1UE\\nLQwkYjAyOTMyNzUtOGU0NC00MTY0LTk5OTktOTVmMjI0NGFlMzZjMIIBIjANBgkq\\nhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvqAAvchk4gMnkGAaCSRhP6z2xabv1u1K\\npN7H07ktXt5g3gNhQfcWAhsT3NTPjt3Mkk7mubC/U7mZsGVIGTccv3oxaXfW3z3R\\nl3OZMYySdMq+TZibJEmMlk4howYToV28w7YdnaknAeNxAPRThFk6PCke4+3baEzX\\nT1kQN8d85MkwvbrMgi81rJn7HI0PyeuZQ+4jLn/WePYWyvfcNDlZm+cd3jvKDEzd\\nn/LKb+knmUeNFSzazBBToMbOCFq4V0m7k5vK6rs5uLsg43RWvKa6gX/oFm3BrJgh\\n9zxC8d4Rk09SKN4+a7nWhE5KMgnw1EZ6PbICA/L6O0kgrnYKfxsmKQIDAQABoC4w\\nLAYJKoZIhvcNAQkOMR8wHTAbBgNVHREEFDASghBoYXByb3h5LmludGVybmFsMA0G\\nCSqGSIb3DQEBCwUAA4IBAQAUuXJ9zPYKSFPILwHoxMa184VHYNaQUs8vbepXSJuE\\nd+nIzM1+TCT03cs+UM5lbBhMZei/GL53oWIqq9ZqOSKHPV0C0qMgnws5Gvvbfobf\\nS7WSqsm9GEM+tH0NTaku925T/d1FqZV9cwtGWYDFDElHvz88oJkkDSuJRd+IUekN\\n7eI/p/T3BcPN4DpTJyUPcWSOWoslsAS6ETeIlMoEGuKd9M7RYzaLpY0j0GzmH+m+\\ne1az2vOxN4Tmqa8oLqrmyinlGxLAbTfX6UaBrG4NkbEiLjOnRyYmVQTptM18B5L8\\nufXaOFTlc2T2xPcX+W461Njd9uHLwFogZrz7w0B+M9Xk\\n-----END CERTIFICATE REQUEST-----",
      "ca":false
   }
]
"""

RANDOM_CERTIFICATES = """
[
   {
      "ca":"-----BEGIN CERTIFICATE-----\\nMIIDTTCCAjWgAwIBAgIUY7GquNSsgAafIeaMAjmgfGdf9F0wDQYJKoZIhvcNAQEL\\nBQAwLDEqMCgGA1UEAwwhc2VsZi1zaWduZWQtY2VydGlmaWNhdGVzLW9wZXJhdG9y\\nMB4XDTI1MDgwNzEzNDczM1oXDTI2MDgwNzEzNDczM1owLDEqMCgGA1UEAwwhc2Vs\\nZi1zaWduZWQtY2VydGlmaWNhdGVzLW9wZXJhdG9yMIIBIjANBgkqhkiG9w0BAQEF\\nAAOCAQ8AMIIBCgKCAQEAwt5427KsVz6mAP5xLlwwBXWQCBKvaI4ge91NxPsqzUSA\\nKzl0yAVClaKaxyO0unfurxbFkbEhrD28MLAejm9GD6HR/GXoqbzR39xog9suTBzc\\nL7flPoxvgBMZOQpTsNQ/ovk+3i6jRbCuglm9rCziCEjulmU3nVceYerDlyqoNLQ+\\nYGtaYMY51FKoVHpPs4CTh1EflsWC7uQpBT0i5Qa9aqY8weJtkKPF5WdD2Uc6IFGM\\nbOCEeyXyZRMHTGBZN9J081g+9SgihapfJaBmvs5XDhxyisYMc2nhv/VLecZtWZsT\\nB6kbV4K4mN9/lHjhXzgGoJw7ooaT4FcQVWnySrbW+wIDAQABo2cwZTAfBgNVHQ4E\\nGAQWBBQFLrK51xa+OAZMmFyq3uYdP9lglDAhBgNVHSMEGjAYgBYEFAUusrnXFr44\\nBkyYXKre5h0/2WCUMA4GA1UdDwEB/wQEAwICpDAPBgNVHRMBAf8EBTADAQH/MA0G\\nCSqGSIb3DQEBCwUAA4IBAQApoZGJe3LwKipilFlCG2IT617aWDKSvcvuiDAs429O\\nJqJz5rGnchIb92CCtxHvNbyGlKebk4nCVQfWigabYkq1zdiWgTH4ntQc6DeLjtPp\\ntnxKfvWzaMYS9Y310//ekYGBdP+TwqZOMU69D4D73M1sf49/WDdaXqk18zjOhxCw\\nZn5V+1nTH1qFD2h6ecGLVXGnyaHHlpgu1CEzHM4DuggnI/j2YktAcelxqq9N+EtJ\\nhnooq8DvZ4oHAxSdpFtglIPS+mnYZ8XGvcv4EwP6fPTNwVbPZzLpwPreA/XblSMJ\\ncBeAYONSb1blSyDfrCwoJnI0Fge9xRHjtzvsl7D3loRD\\n-----END CERTIFICATE-----",
      "certificate_signing_request":"-----BEGIN CERTIFICATE REQUEST-----\\nMIICvTCCAaUCAQAwSjEZMBcGA1UEAwwQaGFwcm94eS5pbnRlcm5hbDEtMCsGA1UE\\nLQwkYjAyOTMyNzUtOGU0NC00MTY0LTk5OTktOTVmMjI0NGFlMzZjMIIBIjANBgkq\\nhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvqAAvchk4gMnkGAaCSRhP6z2xabv1u1K\\npN7H07ktXt5g3gNhQfcWAhsT3NTPjt3Mkk7mubC/U7mZsGVIGTccv3oxaXfW3z3R\\nl3OZMYySdMq+TZibJEmMlk4howYToV28w7YdnaknAeNxAPRThFk6PCke4+3baEzX\\nT1kQN8d85MkwvbrMgi81rJn7HI0PyeuZQ+4jLn/WePYWyvfcNDlZm+cd3jvKDEzd\\nn/LKb+knmUeNFSzazBBToMbOCFq4V0m7k5vK6rs5uLsg43RWvKa6gX/oFm3BrJgh\\n9zxC8d4Rk09SKN4+a7nWhE5KMgnw1EZ6PbICA/L6O0kgrnYKfxsmKQIDAQABoC4w\\nLAYJKoZIhvcNAQkOMR8wHTAbBgNVHREEFDASghBoYXByb3h5LmludGVybmFsMA0G\\nCSqGSIb3DQEBCwUAA4IBAQAUuXJ9zPYKSFPILwHoxMa184VHYNaQUs8vbepXSJuE\\nd+nIzM1+TCT03cs+UM5lbBhMZei/GL53oWIqq9ZqOSKHPV0C0qMgnws5Gvvbfobf\\nS7WSqsm9GEM+tH0NTaku925T/d1FqZV9cwtGWYDFDElHvz88oJkkDSuJRd+IUekN\\n7eI/p/T3BcPN4DpTJyUPcWSOWoslsAS6ETeIlMoEGuKd9M7RYzaLpY0j0GzmH+m+\\ne1az2vOxN4Tmqa8oLqrmyinlGxLAbTfX6UaBrG4NkbEiLjOnRyYmVQTptM18B5L8\\nufXaOFTlc2T2xPcX+W461Njd9uHLwFogZrz7w0B+M9Xk\\n-----END CERTIFICATE REQUEST-----",
      "certificate":"-----BEGIN CERTIFICATE-----\\nMIIDczCCAlugAwIBAgIUMNkZOqIO3vHv7WKN66NoRX56hFUwDQYJKoZIhvcNAQEL\\nBQAwLDEqMCgGA1UEAwwhc2VsZi1zaWduZWQtY2VydGlmaWNhdGVzLW9wZXJhdG9y\\nMB4XDTI1MDgwNzEzNTMyNloXDTI1MTEwNTEzNTMyNlowSjEZMBcGA1UEAwwQaGFw\\ncm94eS5pbnRlcm5hbDEtMCsGA1UELQwkYjAyOTMyNzUtOGU0NC00MTY0LTk5OTkt\\nOTVmMjI0NGFlMzZjMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvqAA\\nvchk4gMnkGAaCSRhP6z2xabv1u1KpN7H07ktXt5g3gNhQfcWAhsT3NTPjt3Mkk7m\\nubC/U7mZsGVIGTccv3oxaXfW3z3Rl3OZMYySdMq+TZibJEmMlk4howYToV28w7Yd\\nnaknAeNxAPRThFk6PCke4+3baEzXT1kQN8d85MkwvbrMgi81rJn7HI0PyeuZQ+4j\\nLn/WePYWyvfcNDlZm+cd3jvKDEzdn/LKb+knmUeNFSzazBBToMbOCFq4V0m7k5vK\\n6rs5uLsg43RWvKa6gX/oFm3BrJgh9zxC8d4Rk09SKN4+a7nWhE5KMgnw1EZ6PbIC\\nA/L6O0kgrnYKfxsmKQIDAQABo28wbTAhBgNVHSMEGjAYgBYEFAUusrnXFr44BkyY\\nXKre5h0/2WCUMB0GA1UdDgQWBBTOTrB4WjSKJ2c7eL8Buo8Wqs3gnzAMBgNVHRMB\\nAf8EAjAAMBsGA1UdEQQUMBKCEGhhcHJveHkuaW50ZXJuYWwwDQYJKoZIhvcNAQEL\\nBQADggEBAL2q0G0CTUkw7IIip68gy9QqU+FEuHeJLxmu/eht/a1j9bkDGbc+AN71\\nKLHlmvaAiD7VxyiynYLhLJ1Bu0k8wsoVlP7Cly9CrKBh5I4jpONPQI/gdlD3IMZh\\n4fGSrxSTCk9FtMoMpsEyMnkC/IvB8bhWTLmJaKrVir8fJojhBt8k7cpSJhLxBurP\\n8k9zsT+O3q3MtxH9TyDRQSQD9Md/EinKXH3ObLwttsLDxRuY8pyQ/pRs/DJKzNhh\\n9E0U+CnSqtGqiWGhMNDEFyzHygJ+oQc1UI2MFD/bsnpqqEIf2/fMupWRBZIsElba\\nmioXC4d8O4BKELlTVAROy9msc0Dff2k=\\n-----END CERTIFICATE-----",
      "chain":[
         "-----BEGIN CERTIFICATE-----\\nMIIDczCCAlugAwIBAgIUMNkZOqIO3vHv7WKN66NoRX56hFUwDQYJKoZIhvcNAQEL\\nBQAwLDEqMCgGA1UEAwwhc2VsZi1zaWduZWQtY2VydGlmaWNhdGVzLW9wZXJhdG9y\\nMB4XDTI1MDgwNzEzNTMyNloXDTI1MTEwNTEzNTMyNlowSjEZMBcGA1UEAwwQaGFw\\ncm94eS5pbnRlcm5hbDEtMCsGA1UELQwkYjAyOTMyNzUtOGU0NC00MTY0LTk5OTkt\\nOTVmMjI0NGFlMzZjMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvqAA\\nvchk4gMnkGAaCSRhP6z2xabv1u1KpN7H07ktXt5g3gNhQfcWAhsT3NTPjt3Mkk7m\\nubC/U7mZsGVIGTccv3oxaXfW3z3Rl3OZMYySdMq+TZibJEmMlk4howYToV28w7Yd\\nnaknAeNxAPRThFk6PCke4+3baEzXT1kQN8d85MkwvbrMgi81rJn7HI0PyeuZQ+4j\\nLn/WePYWyvfcNDlZm+cd3jvKDEzdn/LKb+knmUeNFSzazBBToMbOCFq4V0m7k5vK\\n6rs5uLsg43RWvKa6gX/oFm3BrJgh9zxC8d4Rk09SKN4+a7nWhE5KMgnw1EZ6PbIC\\nA/L6O0kgrnYKfxsmKQIDAQABo28wbTAhBgNVHSMEGjAYgBYEFAUusrnXFr44BkyY\\nXKre5h0/2WCUMB0GA1UdDgQWBBTOTrB4WjSKJ2c7eL8Buo8Wqs3gnzAMBgNVHRMB\\nAf8EAjAAMBsGA1UdEQQUMBKCEGhhcHJveHkuaW50ZXJuYWwwDQYJKoZIhvcNAQEL\\nBQADggEBAL2q0G0CTUkw7IIip68gy9QqU+FEuHeJLxmu/eht/a1j9bkDGbc+AN71\\nKLHlmvaAiD7VxyiynYLhLJ1Bu0k8wsoVlP7Cly9CrKBh5I4jpONPQI/gdlD3IMZh\\n4fGSrxSTCk9FtMoMpsEyMnkC/IvB8bhWTLmJaKrVir8fJojhBt8k7cpSJhLxBurP\\n8k9zsT+O3q3MtxH9TyDRQSQD9Md/EinKXH3ObLwttsLDxRuY8pyQ/pRs/DJKzNhh\\n9E0U+CnSqtGqiWGhMNDEFyzHygJ+oQc1UI2MFD/bsnpqqEIf2/fMupWRBZIsElba\\nmioXC4d8O4BKELlTVAROy9msc0Dff2k=\\n-----END CERTIFICATE-----",
         "-----BEGIN CERTIFICATE-----\\nMIIDTTCCAjWgAwIBAgIUY7GquNSsgAafIeaMAjmgfGdf9F0wDQYJKoZIhvcNAQEL\\nBQAwLDEqMCgGA1UEAwwhc2VsZi1zaWduZWQtY2VydGlmaWNhdGVzLW9wZXJhdG9y\\nMB4XDTI1MDgwNzEzNDczM1oXDTI2MDgwNzEzNDczM1owLDEqMCgGA1UEAwwhc2Vs\\nZi1zaWduZWQtY2VydGlmaWNhdGVzLW9wZXJhdG9yMIIBIjANBgkqhkiG9w0BAQEF\\nAAOCAQ8AMIIBCgKCAQEAwt5427KsVz6mAP5xLlwwBXWQCBKvaI4ge91NxPsqzUSA\\nKzl0yAVClaKaxyO0unfurxbFkbEhrD28MLAejm9GD6HR/GXoqbzR39xog9suTBzc\\nL7flPoxvgBMZOQpTsNQ/ovk+3i6jRbCuglm9rCziCEjulmU3nVceYerDlyqoNLQ+\\nYGtaYMY51FKoVHpPs4CTh1EflsWC7uQpBT0i5Qa9aqY8weJtkKPF5WdD2Uc6IFGM\\nbOCEeyXyZRMHTGBZN9J081g+9SgihapfJaBmvs5XDhxyisYMc2nhv/VLecZtWZsT\\nB6kbV4K4mN9/lHjhXzgGoJw7ooaT4FcQVWnySrbW+wIDAQABo2cwZTAfBgNVHQ4E\\nGAQWBBQFLrK51xa+OAZMmFyq3uYdP9lglDAhBgNVHSMEGjAYgBYEFAUusrnXFr44\\nBkyYXKre5h0/2WCUMA4GA1UdDwEB/wQEAwICpDAPBgNVHRMBAf8EBTADAQH/MA0G\\nCSqGSIb3DQEBCwUAA4IBAQApoZGJe3LwKipilFlCG2IT617aWDKSvcvuiDAs429O\\nJqJz5rGnchIb92CCtxHvNbyGlKebk4nCVQfWigabYkq1zdiWgTH4ntQc6DeLjtPp\\ntnxKfvWzaMYS9Y310//ekYGBdP+TwqZOMU69D4D73M1sf49/WDdaXqk18zjOhxCw\\nZn5V+1nTH1qFD2h6ecGLVXGnyaHHlpgu1CEzHM4DuggnI/j2YktAcelxqq9N+EtJ\\nhnooq8DvZ4oHAxSdpFtglIPS+mnYZ8XGvcv4EwP6fPTNwVbPZzLpwPreA/XblSMJ\\ncBeAYONSb1blSyDfrCwoJnI0Fge9xRHjtzvsl7D3loRD\\n-----END CERTIFICATE-----"
      ]
   }
]
"""

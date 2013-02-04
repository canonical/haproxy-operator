import os
import yaml

from testtools import TestCase
from mock import patch

import hooks


class PeerRelationTest(TestCase):

    def setUp(self):
        super(PeerRelationTest, self).setUp()

        self.get_relation_data = self.patch_hook("get_relation_data")
        self.log = self.patch_hook("log")
        self.unit_get = self.patch_hook("unit_get")

    def patch_hook(self, hook_name):
        mock_controller = patch.object(hooks, hook_name)
        mock = mock_controller.start()
        self.addCleanup(mock_controller.stop)
        return mock

    @patch.dict(os.environ, {"JUJU_UNIT_NAME": "haproxy-2"})
    def test_with_peer_same_services(self):
        self.unit_get.return_value = "1.2.4.5"
        self.get_relation_data.return_value = {
            "haproxy-1": {
                "hostname": "haproxy-1",
                "private-address": "1.2.4.4",
                "all_services": yaml.dump([
                    {"service_name": "foo_service",
                     "service_host": "0.0.0.0",
                     "service_options": ["balance leastconn"],
                     "service_port": 4242},
                    ])
                }
            }

        services_dict = {
            "foo_service": {
                "service_name": "foo_service",
                "service_host": "0.0.0.0",
                "service_port": 4242,
                "service_options": ["balance leastconn"],
                "server_options": ["maxconn 4"],
                "servers": [("backend_1__8080", "1.2.3.4",
                             8080, ["maxconn 4"])],
                },
            }

        expected = {
            "foo_service": {
                "service_name": "foo_service",
                "service_host": "0.0.0.0",
                "service_port": 4242,
                "service_options": ["balance leastconn",
                                    "mode tcp",
                                    "option tcplog"],
                "servers": [
                    ("haproxy-1", "1.2.4.4", 4243, ["check"]),
                    ("haproxy-2", "1.2.4.5", 4243, ["check", "backup"])
                    ],
                },
            "foo_service_be": {
                "service_name": "foo_service_be",
                "service_host": "0.0.0.0",
                "service_port": 4243,
                "service_options": ["balance leastconn"],
                "server_options": ["maxconn 4"],
                "servers": [("backend_1__8080", "1.2.3.4",
                             8080, ["maxconn 4"])],
                },
            }
        self.assertEqual(expected, hooks.apply_peer_config(services_dict))

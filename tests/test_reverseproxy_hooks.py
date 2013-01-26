from testtools import TestCase
from mock import patch, call

import hooks


class ReverseProxyRelationTest(TestCase):

    def setUp(self):
        super(ReverseProxyRelationTest, self).setUp()

        self.get_relation_data = self.patch_hook("get_relation_data")
        self.get_config_services = self.patch_hook("get_config_services")
        self.log = self.patch_hook("log")
        self.write_service_config = self.patch_hook("write_service_config")
        self.apply_peer_config = self.patch_hook("apply_peer_config")

    def patch_hook(self, hook_name):
        mock_controller = patch.object(hooks, hook_name)
        mock = mock_controller.start()
        self.addCleanup(mock_controller.stop)
        return mock

    def test_relation_data_returns_none(self):
        self.get_config_services.return_value = {
            "service": {
                "service_name": "service",
                },
            }
        self.get_relation_data.return_value = None
        self.assertIs(None, hooks.create_services())
        self.log.assert_called_once_with("No backend servers, exiting.")
        self.write_service_config.assert_not_called()

    def test_relation_data_returns_no_relations(self):
        self.get_config_services.return_value = {
            "service": {
                "service_name": "service",
                },
            }
        self.get_relation_data.return_value = {}
        self.assertIs(None, hooks.create_services())
        self.log.assert_called_once_with("No backend servers, exiting.")
        self.write_service_config.assert_not_called()

    def test_relation_no_services(self):
        self.get_config_services.return_value = {}
        self.get_relation_data.return_value = {
            "foo": {"port": 4242,
                    "hostname": "backend.1",
                    "private-address": "1.2.3.4"},
        }
        self.assertIs(None, hooks.create_services())
        self.log.assert_called_once_with("No services configured, exiting.")
        self.write_service_config.assert_not_called()

    def test_no_port_in_relation_data(self):
        self.get_config_services.return_value = {
            "service": {
                "service_name": "service",
                },
            }
        self.get_relation_data.return_value = {
            "foo": {"private-address": "1.2.3.4"},
        }
        self.assertIs(None, hooks.create_services())
        self.log.assert_has_calls([call.log(
            "No port in relation data for 'foo', skipping.")])
        self.write_service_config.assert_not_called()

    def test_no_private_address_in_relation_data(self):
        self.get_config_services.return_value = {
            "service": {
                "service_name": "service",
                },
            }
        self.get_relation_data.return_value = {
            "foo": {"port": 4242},
        }
        self.assertIs(None, hooks.create_services())
        self.log.assert_has_calls([call.log(
            "No private-address in relation data for 'foo', skipping.")])
        self.write_service_config.assert_not_called()

    def test_no_hostname_in_relation_data(self):
        self.get_config_services.return_value = {
            "service": {
                "service_name": "service",
                },
            }
        self.get_relation_data.return_value = {
            "foo": {"port": 4242,
                    "private-address": "1.2.3.4"},
        }
        self.assertIs(None, hooks.create_services())
        self.log.assert_has_calls([call.log(
            "No hostname in relation data for 'foo', skipping.")])
        self.write_service_config.assert_not_called()

    def test_relation_unknown_service(self):
        self.get_config_services.return_value = {
            "service": {
                "service_name": "service",
                },
            }
        self.get_relation_data.return_value = {
            "foo": {"port": 4242,
                    "hostname": "backend.1",
                    "service_name": "invalid",
                    "private-address": "1.2.3.4"},
        }
        self.assertIs(None, hooks.create_services())
        self.log.assert_has_calls([call.log(
            "Service 'invalid' does not exist.")])
        self.write_service_config.assert_not_called()

    def test_no_relation_but_has_servers_from_config(self):
        self.get_config_services.return_value = {
            None: {
                "service_name": "service",
                },
            "service": {
                "service_name": "service",
                "servers": [
                    ("legacy-backend", "1.2.3.1", 4242, ["maxconn 42"]),
                    ]
                },
            }
        self.get_relation_data.return_value = {}

        expected = {
            'service': {
                'service_name': 'service',
                'servers': [
                    ("legacy-backend", "1.2.3.1", 4242, ["maxconn 42"]),
                    ],
                },
            }
        self.assertEqual(expected, hooks.create_services())
        self.write_service_config.assert_called_with(expected)

    def test_relation_default_service(self):
        self.get_config_services.return_value = {
            None: {
                "service_name": "service",
                },
            "service": {
                "service_name": "service",
                },
            }
        self.get_relation_data.return_value = {
            "foo": {"port": 4242,
                    "hostname": "backend.1",
                    "private-address": "1.2.3.4"},
        }

        expected = {
            'service': {
                'service_name': 'service',
                'servers': [('backend_1__4242', '1.2.3.4', 4242, [])],
                },
            }
        self.assertEqual(expected, hooks.create_services())
        self.write_service_config.assert_called_with(expected)

    def test_with_service_options(self):
        self.get_config_services.return_value = {
            None: {
                "service_name": "service",
                },
            "service": {
                "service_name": "service",
                "server_options": ["maxconn 4"],
                },
            }
        self.get_relation_data.return_value = {
            "foo": {"port": 4242,
                    "hostname": "backend.1",
                    "private-address": "1.2.3.4"},
        }

        expected = {
            'service': {
                'service_name': 'service',
                'server_options': ["maxconn 4"],
                'servers': [('backend_1__4242', '1.2.3.4',
                             4242, ["maxconn 4"])],
                },
            }
        self.assertEqual(expected, hooks.create_services())
        self.write_service_config.assert_called_with(expected)

    def test_with_service_name(self):
        self.get_config_services.return_value = {
            None: {
                "service_name": "service",
                },
            "foo_service": {
                "service_name": "foo_service",
                "server_options": ["maxconn 4"],
                },
            }
        self.get_relation_data.return_value = {
            "foo": {"port": 4242,
                    "hostname": "backend.1",
                    "service_name": "foo_service",
                    "private-address": "1.2.3.4"},
        }

        expected = {
            'foo_service': {
                'service_name': 'foo_service',
                'server_options': ["maxconn 4"],
                'servers': [('backend_1__4242', '1.2.3.4',
                             4242, ["maxconn 4"])],
                },
            }
        self.assertEqual(expected, hooks.create_services())
        self.write_service_config.assert_called_with(expected)

    def test_no_service_name_unit_name_match_service_name(self):
        self.get_config_services.return_value = {
            None: {
                "service_name": "service",
                },
            "foo": {
                "service_name": "foo",
                "server_options": ["maxconn 4"],
                },
            }
        self.get_relation_data.return_value = {
            "foo-1": {"port": 4242,
                          "hostname": "backend.1",
                          "private-address": "1.2.3.4"},
        }

        expected = {
            'foo': {
                'service_name': 'foo',
                'server_options': ["maxconn 4"],
                'servers': [('backend_1__4242', '1.2.3.4',
                             4242, ["maxconn 4"])],
                },
            }
        self.assertEqual(expected, hooks.create_services())
        self.write_service_config.assert_called_with(expected)

    def test_with_sitenames_match_service_name(self):
        self.get_config_services.return_value = {
            None: {
                "service_name": "service",
                },
            "foo_service": {
                "service_name": "foo_service",
                "server_options": ["maxconn 4"],
                },
            }
        self.get_relation_data.return_value = {
            "foo": {"port": 4242,
                    "hostname": "backend.1",
                    "sitenames": "foo_service bar_service",
                    "private-address": "1.2.3.4"},
        }

        expected = {
            'foo_service': {
                'service_name': 'foo_service',
                'server_options': ["maxconn 4"],
                'servers': [('backend_1__4242', '1.2.3.4',
                             4242, ["maxconn 4"])],
                },
            }
        self.assertEqual(expected, hooks.create_services())
        self.write_service_config.assert_called_with(expected)

import yaml

from testtools import TestCase
from mock import patch

import hooks


class ReverseProxyRelationTest(TestCase):

    def setUp(self):
        super(ReverseProxyRelationTest, self).setUp()

        get_relation_data = patch.object(hooks, "get_relation_data")
        self.get_relation_data = get_relation_data.start()
        self.addCleanup(get_relation_data.stop)

        get_config_services = patch.object(hooks, "get_config_services")
        self.get_config_services = get_config_services.start()
        self.addCleanup(get_config_services.stop)

        log = patch.object(hooks, "log")
        self.log = log.start()
        self.addCleanup(log.stop)

        write_service_config = patch.object(hooks, "write_service_config")
        self.write_service_config = write_service_config.start()
        self.addCleanup(write_service_config.stop)
        

    def test_relation_data_returns_none(self):
        self.get_relation_data.return_value = None
        self.assertIs(None, hooks.create_services())
        self.log.assert_called_once_with("No relation data, exiting.")
        self.write_service_config.assert_not_called()

    def test_relation_data_returns_no_relations(self):
        self.get_relation_data.return_value = ()
        self.assertIs(None, hooks.create_services())
        self.log.assert_called_once_with("No relation data, exiting.")
        self.write_service_config.assert_not_called()
        
    def test_no_port_in_relation_data(self):
        self.get_relation_data.return_value = {
            "foo": {"private-address": "1.2.3.4"},
            }
        self.assertIs(None, hooks.create_services())
        self.log.assert_called_once_with(
            "No port in relation data for 'foo', skipping.")
        self.write_service_config.assert_not_called()

    def test_no_private_address_in_relation_data(self):
        self.get_relation_data.return_value = {
            "foo": {"port": 4242},
            }
        self.assertIs(None, hooks.create_services())
        self.log.assert_called_once_with(
            "No private-address in relation data for 'foo', skipping.")
        self.write_service_config.assert_not_called()

    def test_no_hostname_in_relation_data(self):
        self.get_relation_data.return_value = {
            "foo": {"port": 4242,
                    "private-address": "1.2.3.4"},
            }
        self.assertIs(None, hooks.create_services())
        self.log.assert_called_once_with(
            "No hostname in relation data for 'foo', skipping.")
        self.write_service_config.assert_not_called()

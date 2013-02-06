from testtools import TestCase
from mock import patch

import hooks


class ConfigChangedTest(TestCase):

    def setUp(self):
        super(ConfigChangedTest, self).setUp()
        self.config_get = self.patch_hook("config_get")
        self.get_service_ports = self.patch_hook("get_service_ports")
        self.get_listen_stanzas = self.patch_hook("get_listen_stanzas")
        self.create_haproxy_globals = self.patch_hook(
            "create_haproxy_globals")
        self.create_haproxy_defaults = self.patch_hook(
            "create_haproxy_defaults")
        self.remove_services = self.patch_hook("remove_services")
        self.create_services = self.patch_hook("create_services")
        self.load_services = self.patch_hook("load_services")
        self.construct_haproxy_config = self.patch_hook(
            "construct_haproxy_config")
        self.service_haproxy = self.patch_hook(
            "service_haproxy")
        self.notify_website = self.patch_hook("notify_website")

    def patch_hook(self, hook_name):
        mock_controller = patch.object(hooks, hook_name)
        mock = mock_controller.start()
        self.addCleanup(mock_controller.stop)
        return mock

    def test_config_changed_notify_website_changed_stanzas(self):
        self.service_haproxy.return_value = True
        self.get_listen_stanzas.side_effect = (
            (('foo.internal', '1.2.3.4', 123),),
            (('foo.internal', '1.2.3.4', 123),
             ('bar.internal', '1.2.3.5', 234),))

        hooks.config_changed()

        self.notify_website.assert_called_once_with()

    def test_config_changed_no_notify_website_not_changed(self):
        self.service_haproxy.return_value = True
        self.get_listen_stanzas.side_effect = (
            (('foo.internal', '1.2.3.4', 123),),
            (('foo.internal', '1.2.3.4', 123),))

        hooks.config_changed()

        self.notify_website.assert_not_called()

    def test_config_changed_no_notify_website_failed_check(self):
        self.service_haproxy.return_value = False
        self.get_listen_stanzas.side_effect = (
            (('foo.internal', '1.2.3.4', 123),),
            (('foo.internal', '1.2.3.4', 123),
             ('bar.internal', '1.2.3.5', 234),))

        hooks.config_changed()

        self.notify_website.assert_not_called()

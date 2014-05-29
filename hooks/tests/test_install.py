from mock import patch
import os
from testtools import TestCase

import hooks


class InstallTests(TestCase):

    def setUp(self):
        super(InstallTests, self).setUp()
        self.apt_install = self.patch_hook('apt_install')
        self.ensure_package_status = self.patch_hook('ensure_package_status')
        self.enable_haproxy = self.patch_hook('enable_haproxy')
        self.config_get = self.patch_hook('config_get')
        path_exists = patch.object(os.path, "exists")
        self.path_exists = path_exists.start()
        self.path_exists.return_value = True
        self.addCleanup(path_exists.stop)

    def patch_hook(self, hook_name):
        mock_controller = patch.object(hooks, hook_name)
        mock = mock_controller.start()
        self.addCleanup(mock_controller.stop)
        return mock

    @patch('os.mkdir')
    def test_makes_config_dir(self, mkdir):
        self.path_exists.return_value = False
        hooks.install_hook()
        self.path_exists.assert_called_once_with(
            hooks.default_haproxy_service_config_dir)
        mkdir.assert_called_once_with(
            hooks.default_haproxy_service_config_dir, 0600)

    @patch('os.mkdir')
    def test_config_dir_already_exists(self, mkdir):
        hooks.install_hook()
        self.path_exists.assert_called_once_with(
            hooks.default_haproxy_service_config_dir)
        self.assertFalse(mkdir.called)

    def test_install_packages(self):
        hooks.install_hook()
        self.apt_install.assert_called_once_with(
            ['haproxy', 'python-jinja2'], fatal=True)

    def test_ensures_package_status(self):
        hooks.install_hook()
        self.config_get.assert_called_once_with('package_status')
        self.ensure_package_status.assert_called_once_with(
            hooks.service_affecting_packages, self.config_get.return_value)

    def test_calls_enable_haproxy(self):
        hooks.install_hook()
        self.enable_haproxy.assert_called_once_with()

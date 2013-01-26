from contextlib import contextmanager

from testtools import TestCase
from mock import patch, call, MagicMock

import hooks


class PeerRelationTest(TestCase):

    def setUp(self):
        super(PeerRelationTest, self).setUp()

        self.get_relation_data = self.patch_hook("get_relation_data")
        self.get_config_services = self.patch_hook("get_config_services")
        self.log = self.patch_hook("log")
        self.write_service_config = self.patch_hook("write_service_config")

    def patch_hook(self, hook_name):
        mock_controller = patch.object(hooks, hook_name)
        mock = mock_controller.start()
        self.addCleanup(mock_controller.stop)
        return mock


    

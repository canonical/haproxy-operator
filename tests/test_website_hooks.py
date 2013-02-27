from testtools import TestCase
from mock import patch, call

import hooks


class WebsiteRelationTest(TestCase):

    def setUp(self):
        super(WebsiteRelationTest, self).setUp()
        self.notify_website = self.patch_hook("notify_website")

    def patch_hook(self, hook_name):
        mock_controller = patch.object(hooks, hook_name)
        mock = mock_controller.start()
        self.addCleanup(mock_controller.stop)
        return mock

    def test_website_interface_none(self):
        self.assertEqual(None, hooks.website_interface(hook_name=None))
        self.notify_website.assert_not_called()

    def test_website_interface_joined(self):
        hooks.website_interface(hook_name="joined")
        self.notify_website.assert_called_once_with(
            changed=False, relation_ids=(None,))

    def test_website_interface_changed(self):
        hooks.website_interface(hook_name="changed")
        self.notify_website.assert_called_once_with(
            changed=True, relation_ids=(None,))


class NotifyRelationTest(TestCase):

    def setUp(self):
        super(NotifyRelationTest, self).setUp()

        self.relation_get = self.patch_hook("relation_get")
        self.relation_set = self.patch_hook("relation_set")
        self.config_get = self.patch_hook("config_get")
        self.get_relation_ids = self.patch_hook("get_relation_ids")
        self.get_hostname = self.patch_hook("get_hostname")

    def patch_hook(self, hook_name):
        mock_controller = patch.object(hooks, hook_name)
        mock = mock_controller.start()
        self.addCleanup(mock_controller.stop)
        return mock

    def test_notify_website_relation_no_relation_ids(self):
        hooks.notify_relation("website")
        self.get_relation_ids.return_value = ()
        self.relation_set.assert_not_called()
        self.get_relation_ids.assert_called_once_with("website")

    def test_notify_peer_relation_no_relation_ids(self):
        hooks.notify_relation("peer")
        self.get_relation_ids.return_value = ()
        self.relation_set.assert_not_called()
        self.get_relation_ids.assert_called_once_with("peer")

    def test_notify_website_relation_with_default_relation(self):
        self.get_relation_ids.return_value = ()
        self.get_hostname.return_value = "foo.local"
        self.relation_get.return_value = {}
        self.config_get.return_value = {"services": ""}

        hooks.notify_relation("website", relation_ids=(None,))

        self.get_hostname.assert_called_once_with()
        self.relation_get.assert_called_once_with(relation_id=None)
        self.relation_set.assert_called_once_with(
            relation_id=None, port=80, hostname="foo.local",
            all_services="")
        self.get_relation_ids.assert_not_called()

    def test_notify_peer_relation_with_default_relation(self):
        self.get_relation_ids.return_value = ()
        self.get_hostname.return_value = "foo.local"
        self.relation_get.return_value = {}
        self.config_get.return_value = {"services": ""}

        hooks.notify_relation("peer", relation_ids=(None,))

        self.get_hostname.assert_called_once_with()
        self.relation_get.assert_called_once_with(relation_id=None)
        self.relation_set.assert_called_once_with(
            relation_id=None, port=80, hostname="foo.local",
            all_services="")
        self.get_relation_ids.assert_not_called()

    def test_notify_website_none_relation_data(self):
        self.get_relation_ids.return_value = ()
        self.get_hostname.return_value = "foo.local"
        self.relation_get.return_value = None
        self.config_get.return_value = {"services": ""}

        hooks.notify_relation("website", relation_ids=(None,))

        self.get_hostname.assert_called_once_with()
        self.relation_get.assert_called_once_with(relation_id=None)
        self.relation_set.assert_called_once_with(
            relation_id=None, port=80, hostname="foo.local",
            all_services="")
        self.get_relation_ids.assert_not_called()

    def test_notify_peer_none_relation_data(self):
        self.get_relation_ids.return_value = ()
        self.get_hostname.return_value = "foo.local"
        self.relation_get.return_value = None
        self.config_get.return_value = {"services": ""}

        hooks.notify_relation("peer", relation_ids=(None,))

        self.get_hostname.assert_called_once_with()
        self.relation_get.assert_called_once_with(relation_id=None)
        self.relation_set.assert_called_once_with(
            relation_id=None, port=80, hostname="foo.local",
            all_services="")
        self.get_relation_ids.assert_not_called()

    def test_notify_website_relation_with_relations(self):
        self.get_relation_ids.return_value = ("website:1",
                                              "website:2")
        self.get_hostname.return_value = "foo.local"
        self.relation_get.return_value = {}
        self.config_get.return_value = {"services": ""}

        hooks.notify_relation("website")

        self.get_hostname.assert_called_once_with()
        self.get_relation_ids.assert_called_once_with("website")
        self.relation_get.assert_has_calls([
            call.relation_get(relation_id="website:1"),
            call.relation_get(relation_id="website:2"),
            ])

        self.relation_set.assert_has_calls([
            call.relation_set(
                relation_id="website:1", port=80, hostname="foo.local",
                all_services=""),
            call.relation_set(
                relation_id="website:2", port=80, hostname="foo.local",
                all_services=""),
            ])

    def test_notify_peer_relation_with_relations(self):
        self.get_relation_ids.return_value = ("peer:1",
                                              "peer:2")
        self.get_hostname.return_value = "foo.local"
        self.relation_get.return_value = {}
        self.config_get.return_value = {"services": ""}

        hooks.notify_relation("peer")

        self.get_hostname.assert_called_once_with()
        self.get_relation_ids.assert_called_once_with("peer")
        self.relation_get.assert_has_calls([
            call.relation_get(relation_id="peer:1"),
            call.relation_get(relation_id="peer:2"),
            ])

        self.relation_set.assert_has_calls([
            call.relation_set(
                relation_id="peer:1", port=80, hostname="foo.local",
                all_services=""),
            call.relation_set(
                relation_id="peer:2", port=80, hostname="foo.local",
                all_services=""),
            ])

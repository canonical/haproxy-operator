from testtools import TestCase
from mock import patch

import hooks


class ReverseProxyRelationTest(TestCase):

    def setUp(self):
        super(ReverseProxyRelationTest, self).setUp()

        self.get_relation_data = self.patch_hook("get_relation_data")
        self.get_config_services = self.patch_hook("get_config_services")
        self.log = self.patch_hook("log")
        self.write_service_config = self.patch_hook("write_service_config")

    def patch_hook(self, hook_name):
        mock_controller = patch.object(hooks, hook_name)
        mock = mock_controller.start()
        self.addCleanup(mock_controller.stop)
        return mock

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


class HelpersTest(TestCase):
    def test_log(self):
        with patch('subprocess.call') as call:
            msg = 'some message'

            hooks.log(msg)

            call.assert_called_with(["juju-log", msg])

    def test_gets_config(self):
        json_string = '{"foo": "BAR"}'
        with patch('subprocess.check_output') as check_output:
            check_output.return_value = json_string

            result = hooks.config_get()

            self.assertEqual(result['foo'], 'BAR')
            check_output.assert_called_with(['config-get', '--format=json'])

    def test_gets_config_with_scope(self):
        json_string = '{"foo": "BAR"}'
        with patch('subprocess.check_output') as check_output:
            check_output.return_value = json_string

            result = hooks.config_get(scope='baz')

            self.assertEqual(result['foo'], 'BAR')
            check_output.assert_called_with(['config-get', 'baz',
                                             '--format=json'])

    @patch('subprocess.check_output')
    @patch('hooks.log')
    def test_logs_and_returns_none_if_config_get_fails(self, log,
                                                       check_output):
        check_output.side_effect = RuntimeError('some error')

        result = hooks.config_get()

        log.assert_called_with('some error')
        self.assertIsNone(result)


class RelationsTest(TestCase):
    @patch('subprocess.check_output')
    def test_gets_relation(self, check_output):
        json_string = '{"foo": "BAR"}'
        check_output.return_value = json_string

        result = hooks.relation_get()

        self.assertEqual(result['foo'], 'BAR')
        check_output.assert_called_with(['relation-get', '--format=json', ''])

    @patch('subprocess.check_output')
    def test_gets_relation_with_scope(self, check_output):
        json_string = '{"foo": "BAR"}'
        check_output.return_value = json_string

        result = hooks.relation_get(scope='baz-scope')

        self.assertEqual(result['foo'], 'BAR')
        check_output.assert_called_with(['relation-get', '--format=json',
                                         'baz-scope'])

    @patch('subprocess.check_output')
    def test_gets_relation_with_unit_name(self, check_output):
        json_string = '{"foo": "BAR"}'
        check_output.return_value = json_string

        result = hooks.relation_get(scope='baz-scope', unit_name='baz-unit')

        self.assertEqual(result['foo'], 'BAR')
        check_output.assert_called_with(['relation-get', '--format=json',
                                         'baz-scope', 'baz-unit'])

    @patch('subprocess.check_output')
    def test_gets_relation_with_relation_id(self, check_output):
        json_string = '{"foo": "BAR"}'
        check_output.return_value = json_string

        result = hooks.relation_get(scope='baz-scope', unit_name='baz-unit',
                                    relation_id=123)

        self.assertEqual(result['foo'], 'BAR')
        check_output.assert_called_with(['relation-get', '--format=json', '-r',
                                         123, 'baz-scope', 'baz-unit'])

    @patch('subprocess.check_output')
    @patch('hooks.log')
    def test_logs_and_returns_none_relation_get_fails(self, log,
                                                      check_output):
        check_output.side_effect = RuntimeError('some error')

        result = hooks.relation_get()

        log.assert_called_with('some error')
        self.assertIsNone(result)

    @patch('subprocess.check_output')
    @patch('hooks.log')
    def test_gets_relation_ids(self, log, check_output):
        json_string = '{"foo": "BAR"}'
        check_output.return_value = json_string

        result = hooks.get_relation_ids()

        self.assertEqual(result['foo'], 'BAR')
        check_output.assert_called_with(['relation-ids', '--format=json'])
        log.assert_called_with('Calling: %s' % ['relation-ids',
                                                '--format=json'])

    @patch('subprocess.check_output')
    @patch('hooks.log')
    def test_gets_relation_ids_by_name(self, log, check_output):
        json_string = '{"foo": "BAR"}'
        check_output.return_value = json_string

        result = hooks.get_relation_ids(relation_name='baz')

        self.assertEqual(result['foo'], 'BAR')
        check_output.assert_called_with(['relation-ids', '--format=json',
                                         'baz'])
        log.assert_called_with('Calling: %s' % ['relation-ids',
                                                '--format=json', 'baz'])

    @patch('subprocess.check_output')
    @patch('hooks.log')
    def test_returns_none_when_get_relation_ids_fails(self, log,
                                                      check_output):
        check_output.side_effect = RuntimeError('some error')

        result = hooks.get_relation_ids()

        log.assert_called_with('Calling: %s' % ['relation-ids',
                                                '--format=json'])
        self.assertIsNone(result)

    @patch('subprocess.check_output')
    @patch('hooks.log')
    def test_gets_relation_list(self, log, check_output):
        json_string = '{"foo": "BAR"}'
        check_output.return_value = json_string

        result = hooks.get_relation_list()

        self.assertEqual(result['foo'], 'BAR')
        check_output.assert_called_with(['relation-list', '--format=json'])
        log.assert_called_with('Calling: %s' % ['relation-list',
                                                '--format=json'])

    @patch('subprocess.check_output')
    @patch('hooks.log')
    def test_gets_relation_list_by_id(self, log, check_output):
        json_string = '{"foo": "BAR"}'
        check_output.return_value = json_string

        result = hooks.get_relation_list(relation_id=123)

        self.assertEqual(result['foo'], 'BAR')
        check_output.assert_called_with(['relation-list', '--format=json',
                                         '-r', 123])
        log.assert_called_with('Calling: %s' % ['relation-list',
                                                '--format=json', '-r', 123])

    @patch('subprocess.check_output')
    @patch('hooks.log')
    def test_returns_none_when_get_relation_list_fails(self, log,
                                                       check_output):
        check_output.side_effect = RuntimeError('some error')

        result = hooks.get_relation_list()

        log.assert_called_with('Calling: %s' % ['relation-list',
                                                '--format=json'])
        self.assertIsNone(result)

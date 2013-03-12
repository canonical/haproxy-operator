from testtools import TestCase
from mock import call, patch, MagicMock

import yaml
import hooks


class NRPEHooksTest(TestCase):

    @patch('hooks.notify_local_monitors')
    @patch('nrpe.NRPE')
    def test_update_nrpe_config(self, nrpe, notify_local_monitors):
        nrpe_compat = MagicMock()
        nrpe_compat.checks = [MagicMock(shortname="haproxy"),
                              MagicMock(shortname="haproxy_queue")]
        nrpe.return_value = nrpe_compat

        hooks.update_nrpe_config()

        self.assertEqual(
            nrpe_compat.mock_calls,
            [call.add_check('haproxy', 'Check HAProxy', 'check_haproxy.sh'),
             call.add_check('haproxy_queue', 'Check HAProxy queue depth',
                            'check_haproxy_queue_depth.sh'),
             call.write()])
        self.assertEqual(notify_local_monitors.mock_calls,
                         [call([{'haproxy':
                                 {'command': 'check_haproxy'}},
                                {'haproxy_queue':
                                 {'command': 'check_haproxy_queue'}}])])

    @patch('hooks.relation_set')
    @patch('hooks.get_relation_ids')
    def test_notify_local_monitors(self, get_relation_ids, relation_set):
        get_relation_ids.return_value = ['local-monitors:1']

        nrpe_checks = [{'haproxy':
                        {'command': 'check_haproxy'}},
                       {'haproxy_queue':
                        {'command': 'check_haproxy_queue'}}]
        expected = {"monitors": {"remote": {"nrpe": nrpe_checks}}}
        hooks.notify_local_monitors(nrpe_checks)
        self.assertEqual(relation_set.mock_calls,
                         [call(relation_id="local-monitors:1",
                               monitors=yaml.dump(expected))])

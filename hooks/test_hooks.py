import hooks
import yaml
import unittest
from textwrap import dedent
from mocker import MockerTestCase, ARGS


class CreateServiceTest(MockerTestCase):

    def setUp(self):
        self.config_services = [{
            "service_name": "haproxy_test",
            "service_host": "0.0.0.0",
            "service_port": "88",
            "service_options": ["balance leastconn"],
            "server_options": "maxconn 25"}]
        self.config_services_extended = [
            {"service_name": "unit_service",
            "service_host": "supplied-hostname",
            "service_port": "999",
            "service_options": ["balance leastconn"],
            "server_options": "maxconn 99"}]
        self.relation_services = [
            {"service_name": "foo_service",
            "service_options": ["balance leastconn"],
            "servers": [("A", "hA", "1", "oA1 oA2")]},
            {"service_name": "bar_service",
            "service_options": ["balance leastconn"],
            "servers": [
                ("A", "hA", "1", "oA1 oA2"), ("B", "hB", "2", "oB1 oB2")]}]
        hooks.default_haproxy_config_dir = self.makeDir()
        hooks.default_haproxy_config = self.makeFile()
        hooks.default_haproxy_service_config_dir = self.makeDir()
        obj = self.mocker.replace("hooks.juju_log")
        obj(ARGS)
        self.mocker.count(0, None)
        obj = self.mocker.replace("hooks.unit_get")
        obj("public-address")
        self.mocker.result("test-host.example.com")
        self.mocker.count(0, None)
        self.maxDiff = None
    
    def _expect_config_get(self, **kwargs):
        result = {
            "default_timeouts": "queue 1000, connect 1000, client 1000, server 1000",
            "global_log": "127.0.0.1 local0, 127.0.0.1 local1 notice",
            "global_spread_checks": 0,
            "monitoring_allowed_cidr": "127.0.0.1/32",
            "monitoring_username": "haproxy",
            "default_log": "global",
            "global_group": "haproxy",
            "monitoring_stats_refresh": 3,
            "default_retries": 3,
            "services": yaml.dump(self.config_services),
            "global_maxconn": 4096,
            "global_user": "haproxy",
            "default_options": "httplog, dontlognull",
            "monitoring_port": 10000,
            "global_debug": False,
            "nagios_context": "juju",
            "global_quiet": False,
            "enable_monitoring": False,
            "monitoring_password": "changeme",
            "default_mode": "http"}
        obj = self.mocker.replace("hooks.config_get")
        obj()
        result.update(kwargs)
        self.mocker.result(result)

    def _expect_relation_get_all(self, relation, extra={}):
        obj = self.mocker.replace("hooks.relation_get_all")
        obj(relation)
        relation = {"hostname": "10.0.1.2",
                    "private-address": "10.0.1.2",
                    "port": "10000"}
        relation.update(extra)
        result = {"1": {"unit/0": relation}}
        self.mocker.result(result)
        self.mocker.count(1, None)

    def _expect_relation_get_all_with_services(self, relation, extra={}):
        extra.update({"services": yaml.dump(self.relation_services)})
        return self._expect_relation_get_all(relation, extra)

    def test_generation(self):
        """
        Simplest use case, config stanza seeded in config file, server line
        added through simple relation.  Many servers can join this, but
        multiple services will not be presented to the outside
        """
        self._expect_config_get()
        self._expect_relation_get_all("reverseproxy")
        self.mocker.replay()
        hooks.create_services()
        services = hooks.load_services()
        stanza = """\
            listen haproxy_test 0.0.0.0:88
                balance leastconn
                server 10_0_1_2__10000 10.0.1.2:10000 maxconn 25

        """
        self.assertEquals(services, dedent(stanza))

    def test_generation_extended_with_relation(self):
        """
        This case covers specifying an up-front services file to ha-proxy
        in the config.  The relation then specifies a singular hostname, 
        port and server_options setting which is filled into the appropriate
        haproxy stanza based on multiple criteria.
        """
        self._expect_config_get(
                services=yaml.dump(self.config_services_extended))
        self._expect_relation_get_all("reverseproxy")
        self.mocker.replay()
        hooks.create_services()
        services = hooks.load_services()
        stanza = """\
            listen unit_service supplied-hostname:999
                balance leastconn
                server 10_0_1_2__10000 10.0.1.2:10000 maxconn 99

        """
        self.assertEquals(dedent(stanza), services)

    def test_generation_pure_relation(self):
        """
        In this case, the relation is in control of the haproxy config file.
        Each relation chooses what server it creates in the haproxy file, it
        relies on the haproxy service only for the hostname and front-end port.
        Each member of the relation will put a backend server entry under in
        the desired stanza.  Each realtion can in fact supply multiple
        entries from the same juju service unit if desired.
        """
        self._expect_config_get()
        self._expect_relation_get_all_with_services("reverseproxy")
        self.mocker.replay()
        hooks.create_services()
        services = hooks.load_services()
        stanza = """\
            listen foo_service 0.0.0.0:88
                balance leastconn
                server A hA:1 oA1 oA2
        """
        self.assertIn(dedent(stanza), services)
        stanza = """\
            listen bar_service 0.0.0.0:89
                balance leastconn
                server A hA:1 oA1 oA2
                server B hB:2 oB1 oB2
        """
        self.assertIn(dedent(stanza), services)

    def test_get_config_services_config_only(self):
        """
        Attempting to catch the case where a relation is not joined yet
        """
        self._expect_config_get()
        obj = self.mocker.replace("hooks.relation_get_all")
        obj("reverseproxy")
        self.mocker.result(None)
        self.mocker.replay()
        result = hooks.get_config_services()
        self.assertEquals(result, self.config_services)

    def test_get_config_services_relation_no_services(self):
        """
        If the config specifies services and the realtion does not, just the
        config services should come through.
        """
        self._expect_config_get()
        self._expect_relation_get_all("reverseproxy")
        self.mocker.replay()
        result = hooks.get_config_services()
        self.assertEquals(result, self.config_services)

    def test_get_config_services_relation_with_services(self):
        """
        Testing with both the config and relation providing services should
        yield the just the relation
        """
        self._expect_config_get()
        self._expect_relation_get_all_with_services("reverseproxy")
        self.mocker.replay()
        result = hooks.get_config_services()
        # Just test "servers" since hostname and port and maybe other keys
        # will be added by the hook
        self.assertEquals(result[0]["servers"],
                self.relation_services[0]["servers"])


#!/usr/bin/env python3

import logging
import sys

sys.path.append('lib') # noqa

import subprocess

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus

from haproxy_instance_manager import HaproxyInstanceManager
from tcp_lb import TCPBackendManager
from interface_vrrp_parameters import (
    VRRPParametersProvides,
    VRRPInstance,
    VRRPScript,
)

logger = logging.getLogger(__name__)


class HaproxyCharm(CharmBase):

    tcp_backend_manager_cls = TCPBackendManager

    def __init__(self, *args):
        super().__init__(*args)

        self.framework.observe(self.on.install, self.on_install)
        self.framework.observe(self.on.start, self.on_start)
        self.framework.observe(self.on.stop, self.on_stop)
        self.framework.observe(self.on.config_changed, self.on_config_changed)

        self.tcp_backend_manager = self.tcp_backend_manager_cls(self, 'tcp-load-balancer')
        self.framework.observe(self.tcp_backend_manager.on.pools_changed, self._on_pools_changed)

        self.haproxy_instance_manager = HaproxyInstanceManager(self, 'haproxy_instance_manager',
                                                               self.tcp_backend_manager)

        self.keepalived = VRRPParametersProvides(self, 'vrrp-parameters')
        self.framework.observe(self.keepalived.on.keepalived_available,
                               self.on_keepalived_available)

    def on_install(self, event):
        self.haproxy_instance_manager.install()

    def on_start(self, event):
        self.haproxy_instance_manager.start()
        self.model.unit.status = ActiveStatus()

    def on_stop(self, event):
        self.haproxy_instance_manager.stop()
        self.model.unit.status = BlockedStatus('the haproxy service is stopped')

    def on_remote(self, event):
        self.haproxy_instance_manager.uninstall()

    def on_config_changed(self, event):
        self.reconfigure_haproxy()
        self.reconfigure_keepalived()
        subprocess.check_call(['systemctl', 'restart', 'haproxy'])

    def _on_pools_changed(self, event):
        self.reconfigure_haproxy()
        self.reconfigure_keepalived()

    def reconfigure_haproxy(self):
        self.unit.status = MaintenanceStatus('reconfiguring haproxy')
        self.haproxy_instance_manager.reconfigure()
        self.unit.status = ActiveStatus()

    def on_keepalived_available(self, event):
        if not self.haproxy_instance_manager.is_started:
            event.defer()
        self.reconfigure_keepalived()

    def reconfigure_keepalived(self):
        if not self.keepalived.is_joined:
            return

        # TODO: the check source into a separate file.
        vrrp_scripts = []
        for port in self.tcp_backends.frontend_ports:
            vrrp_scripts.append(VRRPScript(f'haproxy_port_{port}_check',
                                           f'''script "bash -c '</dev/tcp/127.0.0.1/{port}'"'''))
        # TODO: there needs to be a better way to determine an egress-facing network interface
        # on which to configure a virtual IP than this.
        vip_interface = self.model.get_binding('website').network.interfaces[0].name
        virtual_ip = self.model.config.get('virtual-ip')
        if virtual_ip is None:
            self.unit.status = BlockedStatus('Waiting for an administrator to set virtual-ip.')
            return
        vrrp_instance = VRRPInstance(self.app.name,
                                     self.model.config['virtual-router-id'],
                                     [virtual_ip],
                                     vip_interface,
                                     track_interfaces=[vip_interface],
                                     track_scripts=vrrp_scripts)
        self.keepalived.configure_vrrp_instances([vrrp_instance])
        self.unit.status = ActiveStatus()


if __name__ == '__main__':
    main(HaproxyCharm)

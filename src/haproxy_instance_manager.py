import subprocess
import logging

from types import SimpleNamespace
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from ops.framework import (
    Object,
    StoredState,
)

from tcp_lb import BalancingAlgorithm


logger = logging.getLogger(__name__)


class HaproxyInstanceManager(Object):

    _stored = StoredState()
    HAPROXY_ENV_FILE = Path('/etc/default/haproxy')

    def __init__(self, charm, key, tcp_backend_manager, bind_addresses=None):
        super().__init__(charm, key)
        self.tcp_backend_manager = tcp_backend_manager
        self.tcp_pool_adapter = TCPLoadBalancerPoolAdapter(
            self.tcp_backend_manager.pools,
            bind_addresses,
        )

        self._stored.set_default(is_started=False)
        self.haproxy_conf_file = Path(f'/etc/haproxy/juju-{self.model.app.name}.cfg')

    @property
    def is_started(self):
        return self._stored.is_started

    def install(self):
        self._install_haproxy()
        self._update_haproxy_env_file()

    def _install_haproxy(self):
        logger.info('Installing the haproxy package')
        subprocess.check_call(['apt', 'update'])
        subprocess.check_call(['apt', 'install', '-yq', 'haproxy'])

    def _update_haproxy_env_file(self):
        """Update the maintainer-provided environment file.

        This is done to include the config rendered by us in addition to
        the default config provided by the package.
        """
        ctxt = {'haproxy_app_config': self.haproxy_conf_file}
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('haproxy.env.j2')
        rendered_content = template.render(ctxt)
        self.HAPROXY_ENV_FILE.write_text(rendered_content)
        self.haproxy_conf_file.write_text('')

    def start(self):
        if not self._stored.is_started:
            logger.info('Starting the haproxy service')
            self._run_start()
            self._stored.is_started = True

    def _run_start(self):
        subprocess.check_call(['systemctl', 'start', 'haproxy'])

    def stop(self):
        if not self._stored.is_started:
            logger.info('Stopping the haproxy service')
            subprocess.check_call(['systemctl', 'stop', 'haproxy'])
        self.state.is_started = False

    def uninstall(self):
        logger.info('Uninstalling the haproxy service')
        subprocess.check_call(['apt', 'purge', '-yq', 'haproxy'])

    def reconfigure(self):
        logger.info('Reconfiguring the haproxy service')
        self._do_reconfigure()
        self._run_restart()

    def _run_restart(self):
        logger.info('Restarting the haproxy service')
        subprocess.check_call(['systemctl', 'restart', 'haproxy'])

    def _do_reconfigure(self):
        logger.info('Rendering the haproxy config file')
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('haproxy.conf.j2')

        listen_sections = self.tcp_pool_adapter.listen_sections
        rendered_content = template.render({'listen_sections': listen_sections})
        self.haproxy_conf_file.write_text(rendered_content)


class TCPLoadBalancerPoolAdapter:
    """Provides a way to transform interface data structures into haproxy config."""

    # A mapping of interface-specific load-balancing algorithms to the ones
    # specific to the haproxy config.
    BALANCING_ALGORITHMS = {
        BalancingAlgorithm.ROUND_ROBIN: 'roundrobin',
        BalancingAlgorithm.LEAST_CONNECTIONS: 'leastconn',
        BalancingAlgorithm.SOURCE_IP: 'source',
    }

    def __init__(self, backend_pools, bind_addresses):
        self._backend_pools = backend_pools
        self._bind_addresses = bind_addresses

    @property
    def listen_sections(self):
        sections = []
        for pool in self._backend_pools:
            sections.append(self._process_pool(pool))
        return sections

    def _process_pool(self, pool):

        socket_specs = self._bind_socket_specs(self._bind_addresses, pool.listener.port)
        socket_specs_str = ','.join([str(spec) for spec in socket_specs])
        listen_section = SimpleNamespace(
            name=pool.listener.name,
            socket_specs_str=socket_specs_str,
            mode='tcp',
            balance=self.BALANCING_ALGORITHMS[pool.listener.balancing_algorithm],
            servers=self._server_specs(pool.members),
        )
        return listen_section

    def _bind_socket_specs(self, addresses, port):
        """Returns a list of BindSocketSpec instances.

        :param list addresses: a list of addresses to use for socket binding.
        :param str port: a port to use for binding sockets.
        """
        socket_specs = []
        if addresses is None:
            socket_specs.append(BindSocketSpec('', port))
        else:
            for address in addresses:
                socket_specs.append(BindSocketSpec(address, port))
        return socket_specs

    def _server_specs(self, backends):
        server_specs = []
        for backend in backends:
            server_specs.append(ServerSpec(
                name=backend.name,
                port=backend.port,
                address=backend.address,
                check_port=backend.monitor_port,
                weight=backend.weight,
            ))
        return server_specs


class BindSocketSpec(SimpleNamespace):

    def __init__(self, address, port_range):
        """
        :param str address: an address accepted by the haproxy bind directive
            which can be an IPv4, IPv6, unix socket, abstract namespace or file
            descriptor.
        :param str port_range: a port or range of ports: <start_port>[-<end_port>]
        """
        super().__init__(address=address, port_range=port_range)

    def __str__(self):
        return f'{self.address}:{self.port_range}'


class ServerSpec(SimpleNamespace):

    def __init__(self, name, address, port, check_port=None, weight=None):
        self._check_port = check_port
        super().__init__(name=name, address=address, port=port, weight=weight)

    @property
    def check_port(self):
        return self._check_port if self._check_port is not None else self.port

    def __str__(self):
        s = f'server {self.name} {self.address}:{self.port} check port {self.check_port}'
        if self.weight is not None:
            s += f' weight {self.weight}'
        return s

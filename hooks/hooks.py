#!/usr/bin/env python

import glob
import os
import random
import re
import socket
import string
import subprocess
import sys
import yaml

import _pythonpath
_ = _pythonpath  # Silence pyflakes.

from charmhelpers import (
    open_port,
    close_port,
    unit_get,
    )
from charmsupport.hookenv import (
    log,
    config as config_get,
    relation_set,
    relation_ids as get_relation_ids,
    relations_of_type,
    relations_for_id,
    )
from charmsupport import nrpe


###############################################################################
# Global variables
###############################################################################
default_haproxy_config_dir = "/etc/haproxy"
default_haproxy_config = "%s/haproxy.cfg" % default_haproxy_config_dir
default_haproxy_service_config_dir = "/var/run/haproxy"
service_affecting_packages = ['haproxy']

###############################################################################
# Supporting functions
###############################################################################


#------------------------------------------------------------------------------
# apt_get_install( package ):  Installs a package
#------------------------------------------------------------------------------
def apt_get_install(packages=None):
    if packages is None:
        return False
    cmd_line = ['apt-get', '-y', 'install', '-qq']
    cmd_line.append(packages)
    return subprocess.call(cmd_line)


def ensure_package_status(packages, status):
    if status in ['install', 'hold']:
        selections = ''.join(['{} {}\n'.format(package, status)
                              for package in packages])
        dpkg = subprocess.Popen(['dpkg', '--set-selections'],
                                stdin=subprocess.PIPE)
        dpkg.communicate(input=selections)

#------------------------------------------------------------------------------
# enable_haproxy:  Enabled haproxy at boot time
#------------------------------------------------------------------------------
def enable_haproxy():
    default_haproxy = "/etc/default/haproxy"
    with open(default_haproxy) as f:
        enabled_haproxy = f.read().replace('ENABLED=0', 'ENABLED=1')
    with open(default_haproxy, 'w') as f:
        f.write(enabled_haproxy)


#------------------------------------------------------------------------------
# create_haproxy_globals:  Creates the global section of the haproxy config
#------------------------------------------------------------------------------
def create_haproxy_globals():
    config_data = config_get()
    global_log = config_data['global_log'].split(',')
    haproxy_globals = []
    haproxy_globals.append('global')
    for global_log_item in global_log:
        haproxy_globals.append("    log %s" % global_log_item.strip())
    haproxy_globals.append("    maxconn %d" % config_data['global_maxconn'])
    haproxy_globals.append("    user %s" % config_data['global_user'])
    haproxy_globals.append("    group %s" % config_data['global_group'])
    if config_data['global_debug'] is True:
        haproxy_globals.append("    debug")
    if config_data['global_quiet'] is True:
        haproxy_globals.append("    quiet")
    haproxy_globals.append("    spread-checks %d" %
                           config_data['global_spread_checks'])
    return '\n'.join(haproxy_globals)


#------------------------------------------------------------------------------
# create_haproxy_defaults:  Creates the defaults section of the haproxy config
#------------------------------------------------------------------------------
def create_haproxy_defaults():
    config_data = config_get()
    default_options = config_data['default_options'].split(',')
    default_timeouts = config_data['default_timeouts'].split(',')
    haproxy_defaults = []
    haproxy_defaults.append("defaults")
    haproxy_defaults.append("    log %s" % config_data['default_log'])
    haproxy_defaults.append("    mode %s" % config_data['default_mode'])
    for option_item in default_options:
        haproxy_defaults.append("    option %s" % option_item.strip())
    haproxy_defaults.append("    retries %d" % config_data['default_retries'])
    for timeout_item in default_timeouts:
        haproxy_defaults.append("    timeout %s" % timeout_item.strip())
    return '\n'.join(haproxy_defaults)


#------------------------------------------------------------------------------
# load_haproxy_config:  Convenience function that loads (as a string) the
#                       current haproxy configuration file.
#                       Returns a string containing the haproxy config or
#                       None
#------------------------------------------------------------------------------
def load_haproxy_config(haproxy_config_file="/etc/haproxy/haproxy.cfg"):
    if os.path.isfile(haproxy_config_file):
        return open(haproxy_config_file).read()
    else:
        return None


#------------------------------------------------------------------------------
# get_monitoring_password:  Gets the monitoring password from the
#                           haproxy config.
#                           This prevents the password from being constantly
#                           regenerated by the system.
#------------------------------------------------------------------------------
def get_monitoring_password(haproxy_config_file="/etc/haproxy/haproxy.cfg"):
    haproxy_config = load_haproxy_config(haproxy_config_file)
    if haproxy_config is None:
        return None
    m = re.search("stats auth\s+(\w+):(\w+)", haproxy_config)
    if m is not None:
        return m.group(2)
    else:
        return None


#------------------------------------------------------------------------------
# get_service_ports:  Convenience function that scans the existing haproxy
#                     configuration file and returns a list of the existing
#                     ports being used.  This is necessary to know which ports
#                     to open and close when exposing/unexposing a service
#------------------------------------------------------------------------------
def get_service_ports(haproxy_config_file="/etc/haproxy/haproxy.cfg"):
    stanzas = get_listen_stanzas(haproxy_config_file=haproxy_config_file)
    return tuple((int(port) for service, addr, port in stanzas))


#------------------------------------------------------------------------------
# get_listen_stanzas: Convenience function that scans the existing haproxy
#                     configuration file and returns a list of the existing
#                     listen stanzas cofnigured.
#------------------------------------------------------------------------------
def get_listen_stanzas(haproxy_config_file="/etc/haproxy/haproxy.cfg"):
    haproxy_config = load_haproxy_config(haproxy_config_file)
    if haproxy_config is None:
        return ()
    stanzas = re.findall("listen\s+([^\s]+)\s+([^:]+):(.*)", haproxy_config)
    return tuple(((service, addr, int(port))
                  for service, addr, port in stanzas))


#------------------------------------------------------------------------------
# update_service_ports:  Convenience function that evaluate the old and new
#                        service ports to decide which ports need to be
#                        opened and which to close
#------------------------------------------------------------------------------
def update_service_ports(old_service_ports=None, new_service_ports=None):
    if old_service_ports is None or new_service_ports is None:
        return None
    for port in old_service_ports:
        if port not in new_service_ports:
            close_port(port)
    for port in new_service_ports:
        open_port(port)


#------------------------------------------------------------------------------
# pwgen:  Generates a random password
#         pwd_length:  Defines the length of the password to generate
#                      default: 20
#------------------------------------------------------------------------------
def pwgen(pwd_length=20):
    alphanumeric_chars = [l for l in (string.letters + string.digits)
                          if l not in 'Iil0oO1']
    random_chars = [random.choice(alphanumeric_chars)
                    for i in range(pwd_length)]
    return ''.join(random_chars)


#------------------------------------------------------------------------------
# update_sysctl: create a sysctl.conf file from YAML-formatted 'sysctl' config
#------------------------------------------------------------------------------
def update_sysctl(config_data):
    sysctl_dict = yaml.load(config_data.get("sysctl", "{}"))
    if sysctl_dict:
        sysctl_file = open("/etc/sysctl.d/50-haproxy.conf", "w")
        for key in sysctl_dict:
            sysctl_file.write("{}={}\n".format(key, sysctl_dict[key]))
        sysctl_file.close()
        subprocess.call(["sysctl", "-p", "/etc/sysctl.d/50-haproxy.conf"])


#------------------------------------------------------------------------------
# create_listen_stanza: Function to create a generic listen section in the
#                       haproxy config
#                       service_name:  Arbitrary service name
#                       service_ip:  IP address to listen for connections
#                       service_port:  Port to listen for connections
#                       service_options:  Comma separated list of options
#                       server_entries:   List of tuples
#                                         server_name
#                                         server_ip
#                                         server_port
#                                         server_options
#------------------------------------------------------------------------------
def create_listen_stanza(service_name=None, service_ip=None,
                         service_port=None, service_options=None,
                         server_entries=None):
    if service_name is None or service_ip is None or service_port is None:
        return None
    service_config = []
    service_config.append("listen %s %s:%s" %
                          (service_name, service_ip, service_port))
    if service_options is not None:
        for service_option in service_options:
            service_config.append("    %s" % service_option.strip())
    if isinstance(server_entries, (list, tuple)):
        for (server_name, server_ip, server_port,
             server_options) in server_entries:
            server_line = "    server %s %s:%s" % \
                (server_name, server_ip, server_port)
            if server_options is not None:
                server_line += " %s" % " ".join(server_options)
            service_config.append(server_line)
    return '\n'.join(service_config)


#------------------------------------------------------------------------------
# create_monitoring_stanza:  Function to create the haproxy monitoring section
#                            service_name: Arbitrary name
#------------------------------------------------------------------------------
def create_monitoring_stanza(service_name="haproxy_monitoring"):
    config_data = config_get()
    if config_data['enable_monitoring'] is False:
        return None
    monitoring_password = get_monitoring_password()
    if config_data['monitoring_password'] != "changeme":
        monitoring_password = config_data['monitoring_password']
    elif (monitoring_password is None and
          config_data['monitoring_password'] == "changeme"):
        monitoring_password = pwgen()
    monitoring_config = []
    monitoring_config.append("mode http")
    monitoring_config.append("acl allowed_cidr src %s" %
                             config_data['monitoring_allowed_cidr'])
    monitoring_config.append("block unless allowed_cidr")
    monitoring_config.append("stats enable")
    monitoring_config.append("stats uri /")
    monitoring_config.append("stats realm Haproxy\ Statistics")
    monitoring_config.append("stats auth %s:%s" %
                             (config_data['monitoring_username'],
                              monitoring_password))
    monitoring_config.append("stats refresh %d" %
                             config_data['monitoring_stats_refresh'])
    return create_listen_stanza(service_name,
                                "0.0.0.0",
                                config_data['monitoring_port'],
                                monitoring_config)


#------------------------------------------------------------------------------
# get_config_services:  Convenience function that returns a mapping containing
#                       all of the services configuration
#------------------------------------------------------------------------------
def get_config_services():
    config_data = config_get()
    services = {}
    for service in yaml.safe_load(config_data['services']):
        service_name = service["service_name"]
        if not services:
            # 'None' is used as a marker for the first service defined, which
            # is used as the default service if a proxied server doesn't
            # specify which service it is bound to.
            services[None] = {"service_name": service_name}
        if is_proxy(service_name) and ("option forwardfor" not in
                                       service["service_options"]):
            service["service_options"].append("option forwardfor")

        if isinstance(service["server_options"], basestring):
            service["server_options"] = service["server_options"].split()

        services[service_name] = service

    return services


#------------------------------------------------------------------------------
# get_config_service:   Convenience function that returns a dictionary
#                       of the configuration of a given service's configuration
#------------------------------------------------------------------------------
def get_config_service(service_name=None):
    return get_config_services().get(service_name, None)


def is_proxy(service_name):
    flag_path = os.path.join(default_haproxy_service_config_dir,
                             "%s.is.proxy" % service_name)
    return os.path.exists(flag_path)


#------------------------------------------------------------------------------
# create_services:  Function that will create the services configuration
#                   from the config data and/or relation information
#------------------------------------------------------------------------------
def create_services():
    services_dict = get_config_services()
    if len(services_dict) == 0:
        log("No services configured, exiting.")
        return

    relation_data = relations_of_type("reverseproxy")

    for relation_info in relation_data:
        unit = relation_info['__unit__']
        juju_service_name = unit.rpartition('/')[0]

        relation_ok = True
        for required in ("port", "private-address", "hostname"):
            if not required in relation_info:
                log("No %s in relation data for '%s', skipping." %
                    (required, unit))
                relation_ok = False
                break

        if not relation_ok:
            continue

        # Mandatory switches ( hostname, port )
        hostname = relation_info['hostname']
        host = relation_info['private-address']
        port = relation_info['port']
        server_name = ("%s__%s" % (hostname.replace('.', '_'), port))

        # Optional switches ( service_name, sitenames )
        service_names = []
        if 'service_name' in relation_info:
            if relation_info['service_name'] in services_dict:
                service_names.append(relation_info['service_name'])
            else:
                log("Service '%s' does not exist." %
                    relation_info['service_name'])
                continue

        if 'sitenames' in relation_info:
            sitenames = relation_info['sitenames'].split()
            for sitename in sitenames:
                if sitename in services_dict:
                    service_names.append(sitename)

        if juju_service_name + "_service" in services_dict:
            service_names.append(juju_service_name + "_service")

        if juju_service_name in services_dict:
            service_names.append(juju_service_name)

        if not service_names:
            service_names.append(services_dict[None]["service_name"])

        for service_name in service_names:
            service = services_dict[service_name]

            # Add the server entries
            servers = service.setdefault("servers", [])
            servers.append((server_name, host, port,
                            services_dict[service_name].get(
                                'server_options', [])))

    has_servers = False
    for service_name, service in services_dict.iteritems():
        if service.get("servers", []):
            has_servers = True

    del services_dict[None]
    write_service_config(services_dict)

    if not has_servers:
        log("No backend servers, exiting.")
        return

    services_dict = apply_peer_config(services_dict)
    return services_dict


def apply_peer_config(services_dict):
    peer_data = relations_of_type("peer")

    peer_services = {}
    for relation_info in peer_data:
        unit_name = relation_info["__unit__"]
        peer_services_data = relation_info.get("all_services")
        if peer_services_data is None:
            continue
        service_data = yaml.safe_load(peer_services_data)
        for service in service_data:
            service_name = service["service_name"]
            if service_name in services_dict:
                peer_service = peer_services.setdefault(service_name, {})
                peer_service["service_name"] = service_name
                peer_service["service_host"] = service["service_host"]
                peer_service["service_port"] = service["service_port"]
                peer_service["service_options"] = ["balance leastconn",
                                                   "mode tcp",
                                                   "option tcplog"]
                servers = peer_service.setdefault("servers", [])
                servers.append((unit_name.replace("/", "-"),
                                relation_info["private-address"],
                                service["service_port"] + 1, ["check"]))

    if not peer_services:
        return services_dict

    unit_name = os.environ["JUJU_UNIT_NAME"].replace("/", "-")
    private_address = unit_get("private-address")
    for service_name, peer_service in peer_services.iteritems():
        original_service = services_dict[service_name]
        servers = peer_service["servers"]
        # Add ourselves to the list of servers for the peer listen stanza.
        servers.append((unit_name, private_address,
                        original_service["service_port"] + 1,
                        ["check"]))

        # Make all but the first server in the peer listen stanza a backup
        # server.
        servers.sort()
        for server in servers[1:]:
            server[3].append("backup")

        # Remap original service port, will now be used by peer listen stanza.
        original_service["service_port"] += 1

        # Remap original service to a new name, stuff peer listen stanza into
        # it's place.
        be_service = service_name + "_be"
        original_service["service_name"] = be_service
        services_dict[be_service] = original_service
        services_dict[service_name] = peer_service

    return services_dict


def write_service_config(services_dict):
    # Construct the new haproxy.cfg file
    for service_key, service_config in services_dict.items():
        log("Service: %s" % service_key)
        server_entries = service_config.get('servers')

        service_name = service_config["service_name"]
        with open(os.path.join(default_haproxy_service_config_dir,
                               "%s.service" % service_name), 'w') as config:
            config.write(create_listen_stanza(
                service_name,
                service_config['service_host'],
                service_config['service_port'],
                service_config['service_options'],
                server_entries))


#------------------------------------------------------------------------------
# load_services: Convenience function that load the service snippet
#                configuration from the filesystem.
#------------------------------------------------------------------------------
def load_services(service_name=None):
    services = ''
    if service_name is not None:
        if os.path.exists("%s/%s.service" %
                          (default_haproxy_service_config_dir, service_name)):
            with open("%s/%s.service" % (default_haproxy_service_config_dir,
                                         service_name)) as f:
                services = f.read()
        else:
            services = None
    else:
        for service in glob.glob("%s/*.service" %
                                 default_haproxy_service_config_dir):
            with open(service) as f:
                services += f.read()
                services += "\n\n"
    return services


#------------------------------------------------------------------------------
# remove_services:  Convenience function that removes the configuration
#                   snippets from the filesystem.  This is necessary
#                   To ensure sync between the config/relation-data
#                   and the existing haproxy services.
#------------------------------------------------------------------------------
def remove_services(service_name=None):
    if service_name is not None:
        path = "%s/%s.service" % (default_haproxy_service_config_dir,
                                  service_name)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception, e:
                log(str(e))
                return False
        return True
    else:
        for service in glob.glob("%s/*.service" %
                                 default_haproxy_service_config_dir):
            try:
                os.remove(service)
            except Exception, e:
                log(str(e))
                pass
        return True


#------------------------------------------------------------------------------
# construct_haproxy_config:  Convenience function to write haproxy.cfg
#                            haproxy_globals, haproxy_defaults,
#                            haproxy_monitoring, haproxy_services
#                            are all strings that will be written without
#                            any checks.
#                            haproxy_monitoring and haproxy_services are
#                            optional arguments
#------------------------------------------------------------------------------
def construct_haproxy_config(haproxy_globals=None,
                             haproxy_defaults=None,
                             haproxy_monitoring=None,
                             haproxy_services=None):
    if None in (haproxy_globals, haproxy_defaults):
        return
    with open(default_haproxy_config, 'w') as haproxy_config:
        config_string = ''
        for config in (haproxy_globals, haproxy_defaults, haproxy_monitoring,
                       haproxy_services):
            if config is not None:
                config_string += config + '\n\n'
        haproxy_config.write(config_string)


#------------------------------------------------------------------------------
# service_haproxy:  Convenience function to start/stop/restart/reload
#                   the haproxy service
#------------------------------------------------------------------------------
def service_haproxy(action=None, haproxy_config=default_haproxy_config):
    if None in (action, haproxy_config):
        return None
    elif action == "check":
        command = ['/usr/sbin/haproxy', '-f', haproxy_config, '-c']
    else:
        command = ['service', 'haproxy', action]
    return_value = subprocess.call(command)
    return return_value == 0


###############################################################################
# Hook functions
###############################################################################
def install_hook():
    if not os.path.exists(default_haproxy_service_config_dir):
        os.mkdir(default_haproxy_service_config_dir, 0600)

    install_status = apt_get_install('haproxy')
    if install_status == 0:
        ensure_package_status(service_affecting_packages, config_get('package_status'))
        enable_haproxy()


def config_changed():
    config_data = config_get()

    ensure_package_status(service_affecting_packages, config_data['package_status'])

    old_service_ports = get_service_ports()
    old_stanzas = get_listen_stanzas()
    haproxy_globals = create_haproxy_globals()
    haproxy_defaults = create_haproxy_defaults()
    if config_data['enable_monitoring'] is True:
        haproxy_monitoring = create_monitoring_stanza()
    else:
        haproxy_monitoring = None
    remove_services()
    create_services()
    haproxy_services = load_services()
    update_sysctl(config_data)
    construct_haproxy_config(haproxy_globals,
                             haproxy_defaults,
                             haproxy_monitoring,
                             haproxy_services)

    if service_haproxy("check"):
        update_service_ports(old_service_ports, get_service_ports())
        service_haproxy("reload")
        if not (get_listen_stanzas() == old_stanzas):
            notify_website()
            notify_peer()
    else:
        # XXX Ideally the config should be restored to a working state if the
        # check fails, otherwise an inadvertent reload will cause the service
        # to be broken.
        log("HAProxy configuration check failed, exiting.")
        sys.exit(1)


def start_hook():
    if service_haproxy("status"):
        return service_haproxy("restart")
    else:
        return service_haproxy("start")


def stop_hook():
    if service_haproxy("status"):
        return service_haproxy("stop")


def reverseproxy_interface(hook_name=None):
    if hook_name is None:
        return None
    if hook_name in ("changed", "departed"):
        config_changed()


def website_interface(hook_name=None):
    if hook_name is None:
        return None
    # Notify website relation but only for the current relation in context.
    notify_website(changed=hook_name == "changed",
                   relation_ids=(None,))


def get_hostname(host=None):
    my_host = socket.gethostname()
    if host is None or host == "0.0.0.0":
        # If the listen ip has been set to 0.0.0.0 then pass back the hostname
        return socket.getfqdn(my_host)
    elif host == "localhost":
        # If the fqdn lookup has returned localhost (lxc setups) then return
        # hostname
        return my_host
    return host


def notify_relation(relation, changed=False, relation_ids=None):
    config_data = config_get()
    default_host = get_hostname()
    default_port = 80

    for rid in relation_ids or get_relation_ids(relation):
        if not rid:
            continue
        service_names = set()
        for relation_data in relations_for_id(rid):
            if 'service_name' in relation_data:
                service_names.add(relation_data['service_name'])

            if changed:
                if 'is-proxy' in relation_data:
                    remote_service = ("%s__%d" % (relation_data['hostname'],
                                                  relation_data['port']))
                    open("%s/%s.is.proxy" % (
                        default_haproxy_service_config_dir,
                        remote_service), 'a').close()

        service_name = None
        if len(service_names) == 1:
            service_name = service_names.pop()
        elif len(service_names) > 1:
            log("Remote units requested than a single service name."
                "Falling back to default host/port.")

        if service_name is not None:
            # If a specfic service has been asked for then return the ip:port
            # for that service, else pass back the default
            requestedservice = get_config_service(service_name)
            my_host = get_hostname(requestedservice['service_host'])
            my_port = requestedservice['service_port']
        else:
            my_host = default_host
            my_port = default_port

        relation_set(relation_id=rid, port=str(my_port),
                     hostname=my_host,
                     all_services=config_data['services'])


def notify_website(changed=False, relation_ids=None):
    notify_relation("website", changed=changed, relation_ids=relation_ids)


def notify_peer(changed=False, relation_ids=None):
    notify_relation("peer", changed=changed, relation_ids=relation_ids)


def update_nrpe_config():
    nrpe_compat = nrpe.NRPE()
    nrpe_compat.add_check('haproxy', 'Check HAProxy', 'check_haproxy.sh')
    nrpe_compat.add_check('haproxy_queue', 'Check HAProxy queue depth',
                          'check_haproxy_queue_depth.sh')
    nrpe_compat.write()


###############################################################################
# Main section
###############################################################################


def main(hook_name):
    if hook_name == "install":
        install_hook()
    elif hook_name == "config-changed":
        config_changed()
        update_nrpe_config()
    elif hook_name == "start":
        start_hook()
    elif hook_name == "stop":
        stop_hook()
    elif hook_name == "reverseproxy-relation-broken":
        config_changed()
    elif hook_name == "reverseproxy-relation-changed":
        reverseproxy_interface("changed")
    elif hook_name == "reverseproxy-relation-departed":
        reverseproxy_interface("departed")
    elif hook_name == "website-relation-joined":
        website_interface("joined")
    elif hook_name == "website-relation-changed":
        website_interface("changed")
    elif hook_name == "peer-relation-joined":
        website_interface("joined")
    elif hook_name == "peer-relation-changed":
        reverseproxy_interface("changed")
    elif hook_name in ("nrpe-external-master-relation-changed",
                       "local-monitors-relation-changed"):
        update_nrpe_config()
    else:
        print "Unknown hook"
        sys.exit(1)

if __name__ == "__main__":
    hook_name = os.path.basename(sys.argv[0])
    # Also support being invoked directly with hook as argument name.
    if hook_name == "hooks.py":
        if len(sys.argv) < 2:
            sys.exit("Missing required hook name argument.")
        hook_name = sys.argv[1]
    main(hook_name)

#!/usr/bin/env python

import json
import glob
import os
import random
import re
import socket
import string
import subprocess
import sys
import yaml


###############################################################################
# Global variables
###############################################################################
default_haproxy_config_dir = "/etc/haproxy"
default_haproxy_config = "%s/haproxy.cfg" % default_haproxy_config_dir
default_haproxy_service_config_dir = "/var/run/haproxy"
hook_name = os.path.basename(sys.argv[0])

###############################################################################
# Supporting functions
###############################################################################


#------------------------------------------------------------------------------
# config_get:  Returns a dictionary containing all of the config information
#              Optional parameter: scope
#              scope: limits the scope of the returned configuration to the
#                     desired config item.
#------------------------------------------------------------------------------
def config_get(scope=None):
    try:
        config_cmd_line = ['config-get']
        if scope is not None:
            config_cmd_line.append(scope)
        config_cmd_line.append('--format=json')
        config_data = json.loads(subprocess.check_output(config_cmd_line))
    except Exception, e:
        subprocess.call(['juju-log', str(e)])
        config_data = None
    finally:
        return(config_data)


#------------------------------------------------------------------------------
# relation_get:  Returns a dictionary containing the relation information
#                Optional parameters: scope, relation_id
#                scope:        limits the scope of the returned data to the
#                              desired item.
#                unit_name:    limits the data ( and optionally the scope )
#                              to the specified unit
#                relation_id:  specify relation id for out of context usage.
#------------------------------------------------------------------------------
def relation_get(scope=None, unit_name=None, relation_id=None):
    try:
        relation_cmd_line = ['relation-get', '--format=json']
        if relation_id is not None:
            relation_cmd_line.extend(('-r', relation_id))
        if scope is not None:
            relation_cmd_line.append(scope)
        else:
            relation_cmd_line.append('')
        if unit_name is not None:
            relation_cmd_line.append(unit_name)
        relation_data = json.loads(subprocess.check_output(relation_cmd_line))
    except Exception, e:
        subprocess.call(['juju-log', str(e)])
        relation_data = None
    finally:
        return(relation_data)


#------------------------------------------------------------------------------
# apt_get_install( package ):  Installs a package
#------------------------------------------------------------------------------
def apt_get_install(packages=None):
    if packages is None:
        return(False)
    cmd_line = ['apt-get', '-y', 'install', '-qq']
    cmd_line.append(packages)
    return(subprocess.call(cmd_line))


#------------------------------------------------------------------------------
# enable_haproxy:  Enabled haproxy at boot time
#------------------------------------------------------------------------------
def enable_haproxy():
    default_haproxy = "/etc/default/haproxy"
    enabled_haproxy = \
    open(default_haproxy).read().replace('ENABLED=0', 'ENABLED=1')
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
    haproxy_globals.append("    spread-checks %d" % \
    config_data['global_spread_checks'])
    return('\n'.join(haproxy_globals))


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
    return('\n'.join(haproxy_defaults))


#------------------------------------------------------------------------------
# load_haproxy_config:  Convenience function that loads (as a string) the
#                       current haproxy configuration file.
#                       Returns a string containing the haproxy config or
#                       None
#------------------------------------------------------------------------------
def load_haproxy_config(haproxy_config_file="/etc/haproxy/haproxy.cfg"):
    if os.path.isfile(haproxy_config_file):
        return(open(haproxy_config_file).read())
    else:
        return(None)


#------------------------------------------------------------------------------
# get_monitoring_password:  Gets the monitoring password from the
#                           haproxy config.
#                           This prevents the password from being constantly
#                           regenerated by the system.
#------------------------------------------------------------------------------
def get_monitoring_password(haproxy_config_file="/etc/haproxy/haproxy.cfg"):
    haproxy_config = load_haproxy_config(haproxy_config_file)
    if haproxy_config is None:
        return(None)
    m = re.search("stats auth\s+(\w+):(\w+)", haproxy_config)
    if m is not None:
        return(m.group(2))
    else:
        return(None)


#------------------------------------------------------------------------------
# get_service_ports:  Convenience function that scans the existing haproxy
#                     configuration file and returns a list of the existing
#                     ports being used.  This is necessary to know which ports
#                     to open and close when exposing/unexposing a service
#------------------------------------------------------------------------------
def get_service_ports(haproxy_config_file="/etc/haproxy/haproxy.cfg"):
    haproxy_config = load_haproxy_config(haproxy_config_file)
    if haproxy_config is None:
        return(None)
    return(re.findall("listen.*:(.*)", haproxy_config))


#------------------------------------------------------------------------------
# open_port:  Convenience function to open a port in juju to
#             expose a service
#------------------------------------------------------------------------------
def open_port(port=None, protocol="TCP"):
    if port is None:
        return(None)
    return(subprocess.call(['/usr/bin/open-port', "%d/%s" % \
    (int(port), protocol)]))


#------------------------------------------------------------------------------
# close_port:  Convenience function to close a port in juju to
#              unexpose a service
#------------------------------------------------------------------------------
def close_port(port=None, protocol="TCP"):
    if port is None:
        return(None)
    return(subprocess.call(['/usr/bin/close-port', "%d/%s" % \
    (int(port), protocol)]))


#------------------------------------------------------------------------------
# update_service_ports:  Convenience function that evaluate the old and new
#                        service ports to decide which ports need to be
#                        opened and which to close
#------------------------------------------------------------------------------
def update_service_ports(old_service_ports=None, new_service_ports=None):
    if old_service_ports is None or new_service_ports is None:
        return(None)
    for port in old_service_ports:
        if port not in new_service_ports:
            close_port(port)
    for port in new_service_ports:
        if port not in old_service_ports:
            open_port(port)


#------------------------------------------------------------------------------
# pwgen:  Generates a random password
#         pwd_length:  Defines the length of the password to generate
#                      default: 20
#------------------------------------------------------------------------------
def pwgen(pwd_length=20):
    alphanumeric_chars = [l for l in (string.letters + string.digits) \
    if l not in 'Iil0oO1']
    random_chars = [random.choice(alphanumeric_chars) \
    for i in range(pwd_length)]
    return(''.join(random_chars))


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
        return(None)
    service_config = []
    service_config.append("listen %s %s:%s" % \
    (service_name, service_ip, service_port))
    if service_options is not None:
        for service_option in service_options:
            service_config.append("    %s" % service_option.strip())
    if server_entries is not None and type(server_entries) == type([]):
        for (server_name, server_ip, server_port, server_options) \
        in server_entries:
            server_line = "    server %s %s:%s" % \
            (server_name, server_ip, server_port)
            if server_options is not None:
                server_line += " %s" % server_options
            service_config.append(server_line)
    return('\n'.join(service_config))


#------------------------------------------------------------------------------
# create_monitoring_stanza:  Function to create the haproxy monitoring section
#                            service_name: Arbitrary name
#------------------------------------------------------------------------------
def create_monitoring_stanza(service_name="haproxy_monitoring"):
    config_data = config_get()
    if config_data['enable_monitoring'] is False:
        return(None)
    monitoring_password = get_monitoring_password()
    if config_data['monitoring_password'] != "changeme":
        monitoring_password = config_data['monitoring_password']
    elif monitoring_password is None and \
    config_data['monitoring_password'] == "changeme":
        monitoring_password = pwgen()
    monitoring_config = []
    monitoring_config.append("mode http")
    monitoring_config.append("acl allowed_cidr src %s" % \
    config_data['monitoring_allowed_cidr'])
    monitoring_config.append("block unless allowed_cidr")
    monitoring_config.append("stats enable")
    monitoring_config.append("stats uri /")
    monitoring_config.append("stats realm Haproxy\ Statistics")
    monitoring_config.append("stats auth %s:%s" % \
    (config_data['monitoring_username'], monitoring_password))
    monitoring_config.append("stats refresh %d" % \
    config_data['monitoring_stats_refresh'])
    return(create_listen_stanza(service_name, \
                                "0.0.0.0", \
                                config_data['monitoring_port'], \
                                monitoring_config))


#------------------------------------------------------------------------------
# get_config_services:  Convenience function that returns a list
#                       of dictionary entries containing all of the services
#                       configuration
#------------------------------------------------------------------------------
def get_config_services():
    config_data = config_get()
    services_list = yaml.load(config_data['services'])
    return(services_list)

#------------------------------------------------------------------------------
# get_config_service:   Convenience function that returns a dictionary
#                       of the configuration of a given services configuration
#------------------------------------------------------------------------------
def get_config_service(service_name=None):
    services_list = get_config_services()
    for service_item in services_list:
        if service_item['service_name'] == service_name:
            return(service_item)
    return(None)

#------------------------------------------------------------------------------
# create_services:  Function that will create the services configuration
#                   from the config data and/or relation information
#------------------------------------------------------------------------------
def create_services():
    services_list = get_config_services()
    services_dict = {}
    for service_item in services_list:
        service_name = service_item['service_name']
        service_host = service_item['service_host']
        service_port = service_item['service_port']
        service_options = service_item['service_options']
        server_options = service_item['server_options']
        services_dict[service_name] = {'service_name': service_name,
                                         'service_host': service_host,
                                         'service_port': service_port,
                                         'service_options': service_options,
                                         'server_options': server_options}

    try:
        relids = subprocess.Popen(['relation-ids','reverseproxy'], stdout=subprocess.PIPE)
        for relid in [ x.strip() for x in relids.stdout]:
            for unit in json.loads(\
            subprocess.check_output(['relation-list', '--format=json',
                                     '-r', relid])):
                relation_info = relation_get(None, unit, relid)
                if type(relation_info) != type({}):
                    sys.exit(0)
                # Mandatory switches ( hostname, port )
                server_name = "%s__%s" % \
                (relation_info['hostname'].replace('.', '_'), \
                relation_info['port'])
                server_ip = relation_info['hostname']
                server_port = relation_info['port']
                # Optional switches ( service_name )
                if 'service_name' in relation_info:
                    if relation_info['service_name'] in services_dict:
                        service_name = relation_info['service_name']
                    else:
                        subprocess.call([\
                        'juju-log', 'service %s does not exists. ' % \
                        relation_info['service_name']])
                        sys.exit(1)
                else:
                    service_name = services_list[0]['service_name']
                if os.path.exists("%s/%s.is.proxy" % \
                (default_haproxy_service_config_dir, service_name)):
                    if 'option forwardfor' not in service_options:
                        service_options.append("option forwardfor")
                # Add the server entries
                if not 'servers' in services_dict[service_name]:
                    services_dict[service_name]['servers'] = \
                    [(server_name, server_ip, server_port, \
                    services_dict[service_name]['server_options'])]
                else:
                    services_dict[service_name]['servers'].append((\
                    server_name, server_ip, server_port, \
                    services_dict[service_name]['server_options']))
    except Exception, e:
        subprocess.call(['juju-log', str(e)])
    # Construct the new haproxy.cfg file
    for service in services_dict:
        print "Service: ", service
        server_entries = None
        if 'servers' in services_dict[service]:
            server_entries = services_dict[service]['servers']
        with open("%s/%s.service" % (\
        default_haproxy_service_config_dir, \
        services_dict[service]['service_name']), 'w') as service_config:
                service_config.write(\
                create_listen_stanza(services_dict[service]['service_name'],\
                                     services_dict[service]['service_host'],
                                     services_dict[service]['service_port'],
                                     services_dict[service]['service_options'],
                                     server_entries))


#------------------------------------------------------------------------------
# load_services: Convenience function that load the service snippet
#                configuration from the filesystem.
#------------------------------------------------------------------------------
def load_services(service_name=None):
    services = ''
    if service_name is not None:
        if os.path.exists("%s/%s.service" % \
        (default_haproxy_service_config_dir, service_name)):
            services = open("%s/%s.service" % \
            (default_haproxy_service_config_dir, service_name)).read()
        else:
            services = None
    else:
        for service in glob.glob("%s/*.service" % \
            default_haproxy_service_config_dir):
            services += open(service).read()
            services += "\n\n"
    return(services)


#------------------------------------------------------------------------------
# remove_services:  Convenience function that removes the configuration
#                   snippets from the filesystem.  This is necessary
#                   To ensure sync between the config/relation-data
#                   and the existing haproxy services.
#------------------------------------------------------------------------------
def remove_services(service_name=None):
    if service_name is not None:
        if os.path.exists("%s/%s.service" % \
        (default_haproxy_service_config_dir, service_name)):
            try:
                os.remove("%s/%s.service" % \
                (default_haproxy_service_config_dir, service_name))
                return(True)
            except Exception, e:
                subprocess.call(['juju-log', str(e)])
                return(False)
    else:
        for service in glob.glob("%s/*.service" % \
        default_haproxy_service_config_dir):
            try:
                os.remove(service)
            except Exception, e:
                subprocess.call(['juju-log', str(e)])
                pass
        return(True)


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
    if haproxy_globals is None or \
       haproxy_defaults is None:
        return(None)
    with open(default_haproxy_config, 'w') as haproxy_config:
        haproxy_config.write(haproxy_globals)
        haproxy_config.write("\n")
        haproxy_config.write("\n")
        haproxy_config.write(haproxy_defaults)
        haproxy_config.write("\n")
        haproxy_config.write("\n")
        if haproxy_monitoring is not None:
            haproxy_config.write(haproxy_monitoring)
            haproxy_config.write("\n")
            haproxy_config.write("\n")
        if haproxy_services is not None:
            haproxy_config.write(haproxy_services)
            haproxy_config.write("\n")
            haproxy_config.write("\n")


#------------------------------------------------------------------------------
# service_haproxy:  Convenience function to start/stop/restart/reload
#                   the haproxy service
#------------------------------------------------------------------------------
def service_haproxy(action=None, haproxy_config=default_haproxy_config):
    if action is None or haproxy_config is None:
        return(None)
    elif action == "check":
        retVal = subprocess.call(\
        ['/usr/sbin/haproxy', '-f', haproxy_config, '-c'])
        if retVal == 1:
            return(False)
        elif retVal == 0:
            return(True)
        else:
            return(False)
    else:
        retVal = subprocess.call(['service', 'haproxy', action])
        if retVal == 0:
            return(True)
        else:
            return(False)


###############################################################################
# Hook functions
###############################################################################
def install_hook():
    if not os.path.exists(default_haproxy_service_config_dir):
        os.mkdir(default_haproxy_service_config_dir, 0600)
    return (apt_get_install("haproxy") == enable_haproxy() == True)


def config_changed():
    config_data = config_get()
    current_service_ports = get_service_ports()
    haproxy_globals = create_haproxy_globals()
    haproxy_defaults = create_haproxy_defaults()
    if config_data['enable_monitoring'] is True:
        haproxy_monitoring = create_monitoring_stanza()
    else:
        haproxy_monitoring = None
    remove_services()
    create_services()
    haproxy_services = load_services()
    construct_haproxy_config(haproxy_globals, \
                             haproxy_defaults, \
                             haproxy_monitoring, \
                             haproxy_services)

    if service_haproxy("check"):
        updated_service_ports = get_service_ports()
        update_service_ports(current_service_ports, updated_service_ports)
        service_haproxy("reload")


def start_hook():
    if service_haproxy("status"):
        return(service_haproxy("restart"))
    else:
        return(service_haproxy("start"))


def stop_hook():
    if service_haproxy("status"):
        return(service_haproxy("stop"))


def reverseproxy_interface(hook_name=None):
    if hook_name is None:
        return(None)
    if hook_name == "changed":
        config_changed()


def website_interface(hook_name=None):
    if hook_name is None:
        return(None)
    default_port = 80
    relation_data = relation_get()
    # If a specfic service has been asked for then return the ip:port for
    # that service, else pass back the default
    if 'service_name' in relation_data:
        service_name = relation_data['service_name']
        requestedservice = get_config_service(service_name)
        my_host = requestedservice['service_host']
        my_port = requestedservice['service_port']
    else:
        my_host = socket.getfqdn(socket.gethostname())
        my_port = default_port

    # If the listen ip has been set to 0.0.0.0 then pass back the hostname
    if my_host == "0.0.0.0":
        my_host = socket.getfqdn(socket.gethostname())

    # If the fqdn lookup has returned localhost (lxc setups) then return
    # hostname
    if my_host == "localhost":
        my_host = socket.gethostname()
    subprocess.call(['relation-set', 'port=%d' % \
    my_port, 'hostname=%s' % my_host])
    if hook_name == "changed":
        if 'is-proxy' in relation_data:
            service_name = "%s__%d" % \
            (relation_data['hostname'], relation_data['port'])
            open("%s/%s.is.proxy" % \
            (default_haproxy_service_config_dir, service_name), 'a').close()

###############################################################################
# Main section
###############################################################################
if hook_name == "install":
    install_hook()
elif hook_name == "config-changed":
    config_changed()
elif hook_name == "start":
    start_hook()
elif hook_name == "stop":
    stop_hook()
elif hook_name == "reverseproxy-relation-broken":
    config_changed()
elif hook_name == "reverseproxy-relation-changed":
    reverseproxy_interface("changed")
elif hook_name == "website-relation-joined":
    website_interface("joined")
elif hook_name == "website-relation-changed":
    website_interface("changed")
else:
    print "Unknown hook"
    sys.exit(1)

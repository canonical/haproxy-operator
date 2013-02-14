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
import nrpe
import time


###############################################################################
# Global variables
###############################################################################
default_haproxy_config_dir = "/etc/haproxy"
default_haproxy_config = "%s/haproxy.cfg" % default_haproxy_config_dir
default_haproxy_service_config_dir = "/var/run/haproxy"
HOOK_NAME = os.path.basename(sys.argv[0])

###############################################################################
# Supporting functions
###############################################################################

def unit_get(*args):
    """Simple wrapper around unit-get, all arguments passed untouched"""
    get_args = ["unit-get"]
    get_args.extend(args)
    return subprocess.check_output(get_args)

def juju_log(*args):
    """Simple wrapper around juju-log, all arguments are passed untouched"""
    log_args = ["juju-log"]
    log_args.extend(args)
    subprocess.call(log_args)

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

def relation_set(arguments, relation_id=None):
    """
    Wrapper around relation-set
    @param arguments: list of command line arguments
    @param relation_id: optional relation-id (passed to -r parameter) to use
    """
    set_args = ["relation-set"]
    if relation_id is not None:
        set_args.extend(["-r", str(relation_id)])
    set_args.extend(arguments)
    subprocess.check_call(set_args)

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
    haproxy_globals.append("    spread-checks %d" %
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
    return(subprocess.call(['open-port', "%d/%s" %
    (int(port), protocol)]))


#------------------------------------------------------------------------------
# close_port:  Convenience function to close a port in juju to
#              unexpose a service
#------------------------------------------------------------------------------
def close_port(port=None, protocol="TCP"):
    if port is None:
        return(None)
    return(subprocess.call(['close-port', "%d/%s" %
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
    alphanumeric_chars = [l for l in (string.letters + string.digits)
    if l not in 'Iil0oO1']
    random_chars = [random.choice(alphanumeric_chars)
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
    service_config.append("listen %s %s:%s" %
    (service_name, service_ip, service_port))
    if service_options is not None:
        for service_option in service_options:
            service_config.append("    %s" % service_option.strip())
    if server_entries is not None and isinstance(server_entries, list):
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
    monitoring_config.append("acl allowed_cidr src %s" %
    config_data['monitoring_allowed_cidr'])
    monitoring_config.append("block unless allowed_cidr")
    monitoring_config.append("stats enable")
    monitoring_config.append("stats uri /")
    monitoring_config.append("stats realm Haproxy\ Statistics")
    monitoring_config.append("stats auth %s:%s" %
    (config_data['monitoring_username'], monitoring_password))
    monitoring_config.append("stats refresh %d" %
    config_data['monitoring_stats_refresh'])
    return(create_listen_stanza(service_name,
                                "0.0.0.0",
                                config_data['monitoring_port'],
                                monitoring_config))

def get_host_port(services_list):
    """
    Given a services list and global juju information, get a host
    and port for this system.
    """
    host = services_list[0]["service_host"]
    port = int(services_list[0]["service_port"])
    return (host, port)

def get_config_services():
    """
    Return dict of all services in the configuration, and in the relation
    where appropriate.  If a relation contains a "services" key, read
    it in as yaml as is the case with the configuration. Set the host and
    port for any relation initiated service entry as those items cannot be
    known by the other side of the relation. In the case of a
    proxy configuration found, ensure the forward for option is set.
    """
    config_data = config_get()
    config_services_list = yaml.load(config_data['services'])
    (host, port) = get_host_port(config_services_list)
    all_relations = relation_get_all("reverseproxy")
    services_list = []
    if hasattr(all_relations, "iteritems"):
        for relid, reldata in all_relations.iteritems():
            for unit, relation_info in reldata.iteritems():
                if relation_info.has_key("services"):
                    rservices = yaml.load(relation_info["services"])
                    for r in rservices:
                        r["service_host"] = host
                        r["service_port"] = port
                        port += 1
                    services_list.extend(rservices)
    if len(services_list) == 0:
        services_list = config_services_list
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


def relation_get_all(relation_name):
    """
    Iterate through all relations, and return large data structure with the
    relation data set:

    @param relation_name: The name of the relation to check

    Returns:

        relation_id:
            unit:
                key: value
                key2: value
    """
    result = {}
    try:
        relids = subprocess.Popen(
                ['relation-ids', relation_name], stdout=subprocess.PIPE)
        for relid in [x.strip() for x in relids.stdout]:
            result[relid] = {}
            for unit in json.loads(
                subprocess.check_output(
                    ['relation-list', '--format=json', '-r', relid])):
                result[relid][unit] = relation_get(None, unit, relid)
        return result
    except Exception, e:
        subprocess.call(['juju-log', str(e)])

def get_services_dict():
    """
    Transform the services list into a dict for easier comprehension,
    and to ensure that we have only one entry per service type.  If multiple
    relations specify the same server_name, try to union the servers
    entries.
    """
    services_list = get_config_services()
    services_dict = {}

    for service_item in services_list:
        if not hasattr(service_item, "iteritems"):
            juju_log("Each 'services' entry must be a dict: %s" % service_item)
            continue;
        if "service_name" not in service_item:
            juju_log("Missing 'service_name': %s" % service_item)
            continue;
        name = service_item["service_name"]
        options = service_item["service_options"]
        if name in services_dict:
            if "servers" in services_dict[name]:
                services_dict[name]["servers"].extend(service_item["servers"])
        else:
            services_dict[name] = service_item
        if os.path.exists("%s/%s.is.proxy" % (
            default_haproxy_service_config_dir, name)):
            if 'option forwardfor' not in options:
                options.append("option forwardfor")

    return services_dict

def get_all_services():
    """
    Transform a services dict into an "all_services" relation setting expected
    by apache2.  This is needed to ensure we have the port and hostname setting
    correct and in the proper format
    """
    services = get_services_dict()
    all_services = []
    for name in services:
        s = {"service_name": name,
             "service_port": services[name]["service_port"]}
        all_services.append(s)
    return all_services

#------------------------------------------------------------------------------
# create_services:  Function that will create the services configuration
#                   from the config data and/or relation information
#------------------------------------------------------------------------------
def create_services():
    services_list = get_config_services()
    services_dict = get_services_dict()

    # service definitions overwrites user specified haproxy file in
    # a pseudo-template form
    all_relations = relation_get_all("reverseproxy")
    for relid, reldata in all_relations.iteritems():
        for unit, relation_info in reldata.iteritems():
            if not isinstance(relation_info, dict):
                sys.exit(0)
            if "services" in relation_info:
                juju_log("Relation %s has services override defined" % relid)
                continue;
            if "hostname" not in relation_info or "port" not in relation_info:
                juju_log("Relation %s needs hostname and port defined" % relid)
                continue;
            juju_service_name = unit.rpartition('/')[0]
            # Mandatory switches ( hostname, port )
            server_name = "%s__%s" % (
                relation_info['hostname'].replace('.', '_'),
                relation_info['port'])
            server_ip = relation_info['hostname']
            server_port = relation_info['port']
            # Optional switches ( service_name )
            if 'service_name' in relation_info:
                if relation_info['service_name'] in services_dict:
                    service_name = relation_info['service_name']
                else:
                    juju_log("service %s does not exist." % (
                        relation_info['service_name']))
                    sys.exit(1)
            elif juju_service_name + '_service' in services_dict:
                service_name = juju_service_name + '_service'
            else:
                service_name = services_list[0]['service_name']
            # Add the server entries
            if not 'servers' in services_dict[service_name]:
                services_dict[service_name]['servers'] = []
            services_dict[service_name]['servers'].append((
                server_name, server_ip, server_port,
                services_dict[service_name]['server_options']))

    # Construct the new haproxy.cfg file
    for service in services_dict:
        juju_log("Service: ", service)
        server_entries = None
        if 'servers' in services_dict[service]:
            server_entries = services_dict[service]['servers']
        service_config_file = "%s/%s.service" % (
            default_haproxy_service_config_dir,
            services_dict[service]['service_name'])
        with open(service_config_file, 'w') as service_config:
                service_config.write(
                create_listen_stanza(services_dict[service]['service_name'],
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
        if os.path.exists("%s/%s.service" %
        (default_haproxy_service_config_dir, service_name)):
            services = open("%s/%s.service" %
            (default_haproxy_service_config_dir, service_name)).read()
        else:
            services = None
    else:
        for service in glob.glob("%s/*.service" %
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
        if os.path.exists("%s/%s.service" %
        (default_haproxy_service_config_dir, service_name)):
            try:
                os.remove("%s/%s.service" %
                (default_haproxy_service_config_dir, service_name))
                return(True)
            except Exception, e:
                subprocess.call(['juju-log', str(e)])
                return(False)
    else:
        for service in glob.glob("%s/*.service" %
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
        retVal = subprocess.call(
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

def website_notify():
    """
    Notify any webiste relations of any configuration changes.
    """
    juju_log("Notifying all website relations of change")
    all_relations = relation_get_all("website")
    if hasattr(all_relations, "iteritems"):
        for relid, reldata in all_relations.iteritems():
            relation_set("time=%s" % time.time(), relation_id=relid)


###############################################################################
# Hook functions
###############################################################################
def install_hook():
    for f in glob.glob('exec.d/*/charm-pre-install'):
        if os.path.isfile(f) and os.access(f, os.X_OK):
            subprocess.check_call(['sh', '-c', f])
    if not os.path.exists(default_haproxy_service_config_dir):
        os.mkdir(default_haproxy_service_config_dir, 0600)
    return ((apt_get_install("haproxy") == enable_haproxy()) is True)


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
    construct_haproxy_config(haproxy_globals,
                             haproxy_defaults,
                             haproxy_monitoring,
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
    elif hook_name == "changed":
        config_changed()
        website_notify()
    elif hook_name=="departed":
        config_changed()
        website_notify()

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
    subprocess.call(
            ['relation-set', 'port=%d' % my_port, 'hostname=%s' % my_host,
             'all_services=%s' % yaml.dump(get_all_services())])
    if hook_name == "changed":
        if 'is-proxy' in relation_data:
            service_name = "%s__%d" % \
            (relation_data['hostname'], relation_data['port'])
            open("%s/%s.is.proxy" %
            (default_haproxy_service_config_dir, service_name), 'a').close()

def update_nrpe_config():
    nrpe_compat = nrpe.NRPE()
    nrpe_compat.add_check('haproxy','Check HAProxy', 'check_haproxy.sh')
    nrpe_compat.add_check('haproxy_queue','Check HAProxy queue depth', 'check_haproxy_queue_depth.sh')
    nrpe_compat.write()

###############################################################################
# Main section
###############################################################################
if __name__ == "__main__":
    if HOOK_NAME == "install":
        install_hook()
    elif HOOK_NAME == "config-changed":
        config_changed()
        update_nrpe_config()
    elif HOOK_NAME == "start":
        start_hook()
    elif HOOK_NAME == "stop":
        stop_hook()
    elif HOOK_NAME == "reverseproxy-relation-broken":
        config_changed()
    elif HOOK_NAME == "reverseproxy-relation-changed":
        reverseproxy_interface("changed")
    elif HOOK_NAME == "reverseproxy-relation-departed":
        reverseproxy_interface("departed")
    elif HOOK_NAME == "website-relation-joined":
        website_interface("joined")
    elif HOOK_NAME == "website-relation-changed":
        website_interface("changed")
    elif HOOK_NAME == "nrpe-external-master-relation-changed":
        update_nrpe_config()
    else:
        print "Unknown hook"
        sys.exit(1)

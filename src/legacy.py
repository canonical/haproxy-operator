# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# We ignore all lint errors in the legacy charm code as we've decided
# to reuse them for the support of the legacy relations
# flake8: noqa
# pylint: skip-file
# mypy: ignore-errors
# fmt: off
"""Legacy haproxy module.

IMPORTANT: This module contains the code of the legacy haproxy charm with some
modifications to work with the ops framework. It does not match the quality standard
for actively managed charms. However, we are using it here to ensure that the new 
haproxy charm can serve as a drop-in replacement for the legacy haproxy charm and 
that the behavior is the same between the 2.
"""

import textwrap
import yaml
from operator import itemgetter
import os
import logging
from itertools import tee
import base64
import pwd

default_haproxy_lib_dir = "/var/lib/haproxy"
dupe_options = [
    "mode tcp",
    "option tcplog",
    "mode http",
    "option httplog",
]

frontend_only_options = [
    "acl",
    "backlog",
    "bind",
    "capture cookie",
    "capture request header",
    "capture response header",
    "clitimeout",
    "default_backend",
    "http-request",
    "maxconn",
    "monitor fail",
    "monitor-net",
    "monitor-uri",
    "option accept-invalid-http-request",
    "option clitcpka",
    "option contstats",
    "option dontlog-normal",
    "option dontlognull",
    "option http-use-proxy-header",
    "option log-separate-errors",
    "option logasap",
    "option socket-stats",
    "option tcp-smart-accept",
    "rate-limit sessions",
    "redirect",
    "tcp-request content accept",
    "tcp-request content reject",
    "tcp-request inspect-delay",
    "timeout client",
    "timeout clitimeout",
    "use_backend",
]

logger = logging.getLogger()
default_haproxy_service_config_dir = "/var/run/haproxy"

DEFAULT_SERVICE_DEFINITION = textwrap.dedent(
    """
        - service_name: haproxy_service
          service_host: "0.0.0.0"
          service_port: 80
          service_options: [balance leastconn, cookie SRVNAME insert]
          server_options: maxconn 100 cookie S{i} check
    """
)


class InvalidRelationDataError(Exception):
    """Invalid data has been provided in the relation."""


def parse_services_yaml(services, yaml_data): # noqa
    """
    Parse given yaml services data.  Add it into the "services" dict.  Ensure
    that you union multiple services "server" entries, as these are the haproxy
    backends that are contacted.
    """
    yaml_services = yaml.safe_load(yaml_data)
    if yaml_services is None:
        return services

    for service in yaml_services:
        service_name = service["service_name"]
        if not services:
            # 'None' is used as a marker for the first service defined, which
            # is used as the default service if a proxied server doesn't
            # specify which service it is bound to.
            services[None] = {"service_name": service_name}

        if "service_options" in service:
            if isinstance(service["service_options"], str):
                service["service_options"] = comma_split(
                    service["service_options"])

            if is_proxy(service_name) and ("option forwardfor" not in
                                           service["service_options"]):
                service["service_options"].append("option forwardfor")

        if (("server_options" in service and
             isinstance(service["server_options"], str))):
            service["server_options"] = comma_split(service["server_options"])

        services[service_name] = merge_service(
            services.get(service_name, {}), service)

    return services


def is_proxy(service_name): # noqa
    flag_path = os.path.join(default_haproxy_service_config_dir,
                             "%s.is.proxy" % service_name)
    return os.path.exists(flag_path)

def comma_split(value): # noqa
    values = value.split(",")
    return list(filter(None, (v.strip() for v in values)))

def merge_service(old_service, new_service): # noqa
    """
    Helper function to merge two service entries correctly.
    Everything will get trampled (preferring old_service), except "servers"
    which will be unioned across both entries, stripping strict dups.
    """
    service = new_service.copy()
    service.update(old_service)

    # Merge all 'servers' entries of the default backend.
    if "servers" in old_service and "servers" in new_service:
        service["servers"] = _add_items_if_missing(
            old_service["servers"], new_service["servers"])

    # Merge all 'backends' and their contained "servers".
    if "backends" in old_service and "backends" in new_service:
        backends_by_name = {}
        # Go through backends in old and new configs and add them to
        # backends_by_name, merging 'servers' while at it.
        for backend in service["backends"] + new_service["backends"]:
            backend_name = backend.get("backend_name")
            if backend_name is None:
                raise InvalidRelationDataError(
                    "Each backend must have backend_name.")
            if backend_name in backends_by_name:
                # Merge servers.
                target_backend = backends_by_name[backend_name]
                target_backend["servers"] = _add_items_if_missing(
                    target_backend["servers"], backend["servers"])
            else:
                backends_by_name[backend_name] = backend

        service["backends"] = sorted(
            backends_by_name.values(), key=itemgetter('backend_name'))
    return service

def ensure_service_host_port(services): # noqa
    seen = []
    missing = []
    for service, options in sorted(services.items()):
        if "service_host" not in options:
            missing.append(options)
            continue
        if "service_port" not in options:
            missing.append(options)
            continue
        seen.append((options["service_host"], int(options["service_port"])))

    seen.sort()
    last_port = seen[-1][1]
    for options in missing:
        last_port = last_port + 2
        options["service_host"] = "0.0.0.0" # nosec
        options["service_port"] = last_port

    return services

def _add_items_if_missing(target, additions):
    """
    Append items from `additions` to `target` if they are not present already.

    Returns a new list.
    """
    result = target[:]
    for addition in additions:
        if addition not in result:
            result.append(addition)
    return result


def get_services_from_relation_data(relation_data): # noqa
    services_dict = {}
    # Added because we won't support configuring yaml services via config options
    # If "services" key not present across all unit, disable default service
    if all("services" not in relation_info for _, relation_info in relation_data):
        services_dict = parse_services_yaml({}, DEFAULT_SERVICE_DEFINITION)
    
    # Handle relations which specify their own services clauses
    for unit, relation_info in relation_data:
        if "services" in relation_info:
            services_dict = parse_services_yaml(services_dict, relation_info['services'])
        # apache2 charm uses "all_services" key instead of "services".
        if "all_services" in relation_info and "services" not in relation_info:
            services_dict = parse_services_yaml(services_dict,
                                                relation_info['all_services'])
            # Replace the backend server(2hops away) with the private-address.
            for service_name in services_dict.keys():
                if service_name == 'service' or 'servers' not in services_dict[service_name]:
                    continue
                servers = services_dict[service_name]['servers']
                for i, _ in enumerate(servers):
                    servers[i][1] = relation_info['private-address']
                    servers[i][2] = str(services_dict[service_name]['service_port'])

    if len(services_dict) == 0:
        logger.info("No services configured, exiting.")
        return {}

    for unit, relation_info in relation_data:
        logger.info("relation info: %r", relation_info)

        # Skip entries that specify their own services clauses, this was
        # handled earlier.
        if "services" in relation_info:
            logger.info("Unit '%s' overrides 'services', skipping further processing.", unit)
            continue

        juju_service_name = unit.name.rpartition('/')[0]

        relation_ok = True
        for required in ("port", "private-address"):
            if required not in relation_info:
                logger.info("No %s in relation data for '%s', skipping.", required, unit)
                relation_ok = False
                break

        if not relation_ok:
            continue

        # Mandatory switches ( private-address, port )
        host = relation_info['private-address']
        port = relation_info['port']
        server_name = f"{unit.name.replace('/', '-')}-{port}"

        # Optional switches ( service_name, sitenames )
        service_names = set()
        if 'service_name' in relation_info:
            if relation_info['service_name'] in services_dict:
                service_names.add(relation_info['service_name'])
            else:
                logger.info("Service '%s' does not exist.", relation_info['service_name'])
                continue

        if 'sitenames' in relation_info:
            sitenames = relation_info['sitenames'].split()
            for sitename in sitenames:
                if sitename in services_dict:
                    service_names.add(sitename)

        if juju_service_name + "_service" in services_dict:
            service_names.add(juju_service_name + "_service")

        if juju_service_name in services_dict:
            service_names.add(juju_service_name)

        if not service_names:
            service_names.add(services_dict[None]["service_name"])

        for service_name in service_names:
            service = services_dict[service_name]

            # Add the server entries
            servers = service.setdefault("servers", [])
            servers.append((server_name, host, port,
                            services_dict[service_name].get(
                                'server_options', [])))

    has_servers = False
    for service_name, service in services_dict.items():
        if service.get("servers", []):
            has_servers = True

    if not has_servers:
        logger.info("No backend servers, exiting.")
        return {}

    del services_dict[None]
    services_dict = ensure_service_host_port(services_dict)
    return services_dict


def _append_backend(service_config, name, options, errorfiles, server_entries): # noqa
    """Append a new backend stanza to the given service_config.

    A backend stanza consists in a 'backend <name>' line followed by option
    lines, errorfile lines and server line.
    """
    service_config.append("")
    service_config.append("backend %s" % (name,))
    service_config.extend("    %s" % option.strip() for option in options)
    for status, path in errorfiles:
        service_config.append("    errorfile %s %s" % (status, path))
    if isinstance(server_entries, (list, tuple)):
        for i, (server_name, server_ip, server_port,
                server_options) in enumerate(server_entries):
            server_line = "    server %s %s:%s" % \
                (server_name, server_ip, server_port)
            if server_options is not None:
                if isinstance(server_options, str):
                    server_line += " " + server_options
                else:
                    server_line += " " + " ".join(server_options)
            server_line = server_line.format(i=i)
            service_config.append(server_line)
        

def create_listen_stanza(service_name=None, service_ip=None,
                         service_port=None, service_options=None,
                         server_entries=None, service_errorfiles=None,
                         service_crts=None, service_backends=None): # noqa
    if service_name is None or service_ip is None or service_port is None:
        return None
    fe_options = []
    be_options = []
    if service_options is not None:
        # For options that should be duplicated in both frontend and backend,
        # copy them to both.
        for o in dupe_options:
            if any(map(o.strip().startswith, service_options)):
                fe_options.append(o)
                be_options.append(o)
        # Filter provided service options into frontend-only and backend-only.
        results = list(zip(
            (fe_options, be_options),
            (True, False),
            tee((o, any(map(o.strip().startswith,
                            frontend_only_options)))
                for o in service_options)))
        for out, cond, result in results:
            out.extend(option for option, match in result
                       if match is cond and option not in out)
    service_config = []
    # In the legacy charm the frontend name is prefixed with the charm's unit name
    # We changed this to haproxy-<service_port> as JUJU_UNIT_NAME env is no longer supported
    # In newer versions of juju
    service_config.append("frontend haproxy-%s" % service_port)
    bind_stanza = "    bind %s:%s" % (service_ip, service_port)
    if service_crts:
        # Enable SSL termination for this frontend, using the given
        # certificates.
        bind_stanza += " ssl"
        if len(service_crts) == 1 and os.path.isdir(service_crts[0]):
            logger.info("Service configured to use '%s' for certificates in haproxy.cfg." % service_crts[0])
            path = service_crts[0]
            bind_stanza += " crt %s no-sslv3" % path
        else:
            for i, crt in enumerate(service_crts):
                if crt == "DEFAULT":
                    path = os.path.join(default_haproxy_lib_dir, "default.pem")
                else:
                    path = os.path.join(default_haproxy_lib_dir,
                                        "service_%s" % service_name, "%d.pem" % i)
                # SSLv3 is always off, since it's vulnerable to POODLE attacks
                bind_stanza += " crt %s no-sslv3" % path
    service_config.append(bind_stanza)
    service_config.append("    default_backend %s" % (service_name,))
    service_config.extend("    %s" % service_option.strip()
                          for service_option in fe_options)

    # For now errorfiles are common for all backends, in the future we
    # might offer support for per-backend error files.
    backend_errorfiles = []  # List of (status, path) tuples
    if service_errorfiles is not None:
        for errorfile in service_errorfiles:
            path = os.path.join(default_haproxy_lib_dir,
                                "service_%s" % service_name,
                                "%s.http" % errorfile["http_status"])
            backend_errorfiles.append((errorfile["http_status"], path))

    # Default backend
    _append_backend(
        service_config, service_name, be_options, backend_errorfiles,
        server_entries)

    # Extra backends
    if service_backends is not None:
        for service_backend in service_backends:
            _append_backend(
                service_config, service_backend["backend_name"],
                be_options, backend_errorfiles, service_backend["servers"])

    return '\n'.join(service_config)


def generate_service_config(services_dict): # noqa
    generated_config = []
    # Construct the new haproxy.cfg file
    for service_key, service_config in services_dict.items():
        service_name = service_config["service_name"]
        server_entries = service_config.get('servers')
        backends = service_config.get('backends', [])

        errorfiles = service_config.get('errorfiles', [])
        for errorfile in errorfiles:
            path = get_service_lib_path(service_name)
            full_path = os.path.join(
                path, "%s.http" % errorfile["http_status"])
            with open(full_path, 'wb') as f:
                f.write(base64.b64decode(errorfile["content"]))

        # Write to disk the content of the given SSL certificates
        # or use a single path element to search for them.
        
        crts = service_config.get('crts', [])
        if len(crts) == 1 and os.path.isdir(crts[0]):
            logger.info("Service configured to use path to look for certificates in haproxy.cfg.")
        else:
            for i, crt in enumerate(crts):
                if crt == "DEFAULT" or crt == "EXTERNAL":
                    continue
                content = base64.b64decode(crt)
                path = get_service_lib_path(service_name)
                full_path = os.path.join(path, "%d.pem" % i)
                write_ssl_pem(full_path, content)
                with open(full_path, 'w') as f:
                    f.write(content.decode('utf-8'))
        
        generated_config.append(create_listen_stanza(
                service_name,
                service_config['service_host'],
                service_config['service_port'],
                service_config.get('service_options', []),
                server_entries, errorfiles, crts, backends
            )
        )
    return generated_config

def get_service_lib_path(service_name): # noqa
    # Get a service-specific lib path
    path = os.path.join(default_haproxy_lib_dir,
                        "service_%s" % service_name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def write_ssl_pem(path, content): # noqa
    """Write an SSL pem file and set permissions on it."""
    # Set the umask so the child process will inherit it and we
    # can make certificate files readable only by the 'haproxy'
    # user (see below).
    old_mask = os.umask(0o077)
    with open(path, 'w') as f:
        f.write(content.decode('utf-8'))
    os.umask(old_mask)
    uid = pwd.getpwnam('haproxy').pw_uid
    os.chown(path, uid, -1)

# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# We ignore all lint errors in the legacy charm code as we've decided
# to reuse them for the support of the legacy relations
# flake8: noqa
# pylint: skip-file
# mypy: ignore-errors
# fmt: off
"""Legacy haproxy module."""

import textwrap
import yaml
from operator import itemgetter
import os
import logging

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
        options["service_host"] = "0.0.0.0"
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

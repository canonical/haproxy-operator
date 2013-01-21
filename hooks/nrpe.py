import json
import subprocess
import pwd
import grp
import os
import re
import shlex

# This module adds compatibility with the nrpe_external_master
# subordinate charm. To use it in your charm:
#
# 1. Update metadata.yaml
#
#   provides:
#     (...)
#     nrpe-external-master:
#       interface: nrpe-external-master
#           scope: container
#
# 2. Add the following to config.yaml
#
#    nagios_context:
#      default: "juju"
#      type: string
#      description: |
#        Used by the nrpe-external-master subordinate charm.
#        A string that will be prepended to instance name to set the host name
#        in nagios. So for instance the hostname would be something like:
#            juju-myservice-0
#        If you're running multiple environments with the same services in them
#        this allows you to differentiate between them.
#
# 3. Add custom checks (Nagios plugins) to files/nrpe-external-master
#
# 4. Update your hooks.py with something like this:
#
#    import nrpe
#    (...)
#    def update_nrpe_config():
#        nrpe_compat = NRPE("myservice")
#        nrpe_compat.add_check(
#            shortname = "myservice",
#            description = "Check MyService",
#            check_cmd = "check_http -w 2 -c 10 http://localhost"
#            )
#        nrpe_compat.add_check(
#            "myservice_other",
#            "Check for widget failures",
#            check_cmd = "/srv/myapp/scripts/widget_check"
#            )
#        nrpe_compat.write()
#
#    def config_changed():
#        (...)
#        update_nrpe_config()


class ConfigurationError(Exception):
    '''An error interacting with the Juju config'''
    pass


def config_get(scope=None):
    '''Return the Juju config as a dictionary'''
    try:
        config_cmd_line = ['config-get']
        if scope is not None:
            config_cmd_line.append(scope)
        config_cmd_line.append('--format=json')
        return json.loads(subprocess.check_output(config_cmd_line))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        subprocess.call(['juju-log', str(error)])
        raise ConfigurationError(str(error))


class CheckException(Exception):
    pass


class Check(object):
    shortname_re = '[A-Za-z0-9-_]*'
    service_template = """
#---------------------------------------------------
# This file is Juju managed
#---------------------------------------------------
define service {{
    use                             active-service
    host_name                       {nagios_hostname}
    service_description             {nagios_hostname} {shortname} {description}
    check_command                   check_nrpe!check_{shortname}
    servicegroups                   {nagios_servicegroup}
}}
"""

    def __init__(self, shortname, description, check_cmd):
        super(Check, self).__init__()
        # XXX: could be better to calculate this from the service name
        if not re.match(self.shortname_re, shortname):
            raise CheckException("shortname must match {}".format(
                Check.shortname_re))
        self.shortname = shortname
        self.description = description
        self.check_cmd = self._locate_cmd(check_cmd)

    def _locate_cmd(self, check_cmd):
        search_path = (
            '/',
            os.path.join(os.environ['CHARM_DIR'],
                         'files/nrpe-external-master'),
            '/usr/lib/nagios/plugins',
        )
        command = shlex.split(check_cmd)
        for path in search_path:
            if os.path.exists(os.path.join(path, command[0])):
                return os.path.join(path, command[0]) + " " + " ".join(
                    command[1:])
        subprocess.call(['juju-log', 'Check command not found: {}'.format(
            command[0])])
        return ''

    def write(self, nagios_context, hostname):
        for f in os.listdir(NRPE.nagios_exportdir):
            if re.search('.*check_{}.cfg'.format(self.shortname), f):
                os.remove(os.path.join(NRPE.nagios_exportdir, f))

        templ_vars = {
            'nagios_hostname': hostname,
            'nagios_servicegroup': nagios_context,
            'description': self.description,
            'shortname': self.shortname,
        }
        nrpe_service_text = Check.service_template.format(**templ_vars)
        nrpe_service_file = '{}/service__{}_check_{}.cfg'.format(
            NRPE.nagios_exportdir, hostname, self.shortname)
        with open(nrpe_service_file, 'w') as nrpe_service_config:
            nrpe_service_config.write(str(nrpe_service_text))

        nrpe_check_file = '/etc/nagios/nrpe.d/check_{}.cfg'.format(
            self.shortname)
        with open(nrpe_check_file, 'w') as nrpe_check_config:
            nrpe_check_config.write("# check {}\n".format(self.shortname))
            nrpe_check_config.write("command[check_{}]={}\n".format(
                self.shortname, self.check_cmd))

    def run(self):
        subprocess.call(self.check_cmd)


class NRPE(object):
    nagios_logdir = '/var/log/nagios'
    nagios_exportdir = '/var/lib/nagios/export'
    nrpe_confdir = '/etc/nagios/nrpe.d'

    def __init__(self):
        super(NRPE, self).__init__()
        self.config = config_get()
        self.nagios_context = self.config['nagios_context']
        self.unit_name = os.environ['JUJU_UNIT_NAME'].replace('/', '-')
        self.hostname = "{}-{}".format(self.nagios_context, self.unit_name)
        self.checks = []

    def add_check(self, *args, **kwargs):
        self.checks.append(Check(*args, **kwargs))

    def write(self):
        try:
            nagios_uid = pwd.getpwnam('nagios').pw_uid
            nagios_gid = grp.getgrnam('nagios').gr_gid
        except:
            subprocess.call(
                ['juju-log',
                 "Nagios user not set up, nrpe checks not updated"])
            return

        if not os.path.exists(NRPE.nagios_exportdir):
            subprocess.call(['juju-log',
                             'Exiting as {} is not accessible'.format(
                                 NRPE.nagios_exportdir)])
            return

        if not os.path.exists(NRPE.nagios_logdir):
            os.mkdir(NRPE.nagios_logdir)
            os.chown(NRPE.nagios_logdir, nagios_uid, nagios_gid)

        for nrpecheck in self.checks:
            nrpecheck.write(self.nagios_context, self.hostname)

        if os.path.isfile('/etc/init.d/nagios-nrpe-server'):
            subprocess.call(['service', 'nagios-nrpe-server', 'reload'])

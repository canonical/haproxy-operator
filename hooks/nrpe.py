import json
import subprocess
import pwd
import grp
import os
import re
from jinja2 import Environment, FileSystemLoader

nagios_logdir = '/var/log/nagios'
nagios_exportdir = '/var/lib/nagios/export'

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

class NRPECheckException(Exception): pass
class NRPECheck(object):
    shortname_re = '[A-Za-z0-9-_]*'
    def __init__(self, shortname, description, check_cmd):
        super(self, object).__init__()
        # XXX: could be better to calculate this from the service name
        if not re.match(self.shortname_re, shortname):
            raise NRPECheckException("NRPECheck.shortname must match {}".format(self.shortname_re))
        self.shortname = shortname
        self.description = description
        self.check_cmd = check_cmd

class NRPE(object):

    def nagios_hostname(config_data):
        unit_name = os.environ['JUJU_UNIT_NAME'].replace('/', '-')
        return "{}-{}-{}".format(config_data['nagios_context'], config_data['nagios_service_type'], unit_name)

    def update_nrpe_checks(service_name, nrpe_check_list):
        config_data = config_get()
        try:
            nagios_uid = pwd.getpwnam('nagios').pw_uid
            nagios_gid = grp.getgrnam('nagios').gr_gid
        except:
            subprocess.call(['juju-log', "Nagios user not setup, nrpe checks not updated"])
            return

        if not os.path.exists(nagios_exportdir):
            subprocess.call(['juju-log', 'Exiting as {} is not accessible'.format(nagios_exportdir)])
            return

        for nrpecheck in nrpe_check_list:
            update_check(config_data, nrpecheck)

        if not os.path.exists(nagios_logdir):
            os.mkdir(nagios_logdir)
            os.chown(nagios_logdir, nagios_uid, nagios_gid)

        if os.path.isfile('/etc/init.d/nagios-nrpe-server'):
            subprocess.call(['service', 'nagios-nrpe-server', 'reload'])

    def update_check(config_data, nrpecheck):
        for f in os.listdir(nagios_exportdir):
            if re.search('.*check_{}.cfg'.format(nrpecheck.shortname), f):
                os.remove(os.path.join(nagios_exportdir, f))

        template_env = Environment(\
        loader=FileSystemLoader(os.path.join(os.environ['CHARM_DIR'], 'data')))
        templ_vars = {
            'nagios_hostname': nagios_hostname(config_data),
            'nagios_servicegroup': config_data['nagios_context'],
            'service_check': nrpecheck,
        }
        template = template_env.get_template('nrpe_service.tmpl').render(templ_vars)
        nrpe_service_file = '/var/lib/nagios/export/service__{}_check_{}.cfg'.format(nagios_hostname, nrpecheck.shortname)
        with open(nrpe_service_file, 'w') as nrpe_service_config:
            nrpe_service_config.write(str(template))

        nrpe_check_file = '/etc/nagios/nrpe.d/check_{}.cfg'.format(nrpecheck.shortname)
        with open(nrpe_check_file, 'w') as nrpe_check_config:
            nrpe_check_config.write("# check {}\n".format(nrpecheck.shortname))
            nrpe_check_config.write("command[check_{}]={}\n".format(nrpecheck.shortname, nrpecheck.check_command))

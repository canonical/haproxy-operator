# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
import os
import sys
import textwrap

from fabric.api import env, local
from fabric.context_managers import lcd

from .constants import BUILD_DEPENDENCIES, PSYCOPG2_CONFLICTS, VIRTUALENV


def bootstrap(download_cache_path=None):
    """Bootstrap the development environment."""
    _check_bootstrap_dependencies()
    _check_psycopg2_conflicts()

    setup_virtualenv()

    # work around m2crypto
    _link_m2crypto()

    install_dependencies(download_cache_path)
    setup_configuration()


def clean():
    """Clean up compiled and backup files."""
    with lcd('django_project'):
        local("rm -rf .coverage coverage.d coverage.xml")
    local("find . -name '*.~*' -delete")
    local("find . -name '*.pyc' -delete")

def setup_virtualenv():
    """Create the virtualenv."""
    created = False
    virtual_env = os.environ.get('VIRTUAL_ENV', None)
    if virtual_env is None:
        if not os.path.exists(VIRTUALENV):
            _create_virtualenv()
            created = True
        virtual_env = VIRTUALENV
    env.virtualenv = os.path.abspath(virtual_env)
    _activate_virtualenv()
    return created

def install_dependencies(download_cache_path=None):
    """Install all dependencies into the virtualenv."""
    if download_cache_path:
        cwd = os.getcwd()
        with lcd(download_cache_path):
            virtualenv_local(
                'make install PACKAGES="-r %s/requirements.txt"' %
                cwd, capture=False)
    else:
        virtualenv_local('pip install -r requirements.txt', capture=False)

    virtualenv_local('python setup.py develop')

def setup_configuration():
    """Setup the configuration."""
    if not os.path.exists('django_project/local.cfg'):
        _create_local_cfg()

def virtualenv_local(command, capture=True):
    """Run a command inside the virtualenv."""
    prefix = ''
    virtual_env = env.get('virtualenv', None)
    if virtual_env:
        prefix = ". %s/bin/activate && " % virtual_env
    command = prefix + command
    return local(command, capture=capture)


# helpers
# =======

def _check_bootstrap_dependencies():
    """Check dependencies required for bootstrap."""
    required = []
    cmd = "dpkg -l %s 2> /dev/null | grep '^ii' | wc -l"
    for pkg in BUILD_DEPENDENCIES:
        output = local(cmd % pkg, capture=True).strip()
        if output != '1':
            required.append(pkg)
    if required:
        print "Please install the following packages, as they are required"
        print "in order to build some of the dependencies:"
        for pkg in required:
            print pkg
        sys.exit(1)

def _check_psycopg2_conflicts():
    """Check for libraries conflicting with psycopg2."""
    conflicting = []
    cmd = "dpkg -l %s 2> /dev/null | grep '^ii' | wc -l"
    for pkg in PSYCOPG2_CONFLICTS:
        output = local(cmd % pkg, capture=True).strip()
        if output != '0':
            conflicting.append(pkg)
    if conflicting:
        print "Please remove the following packages, as their presence will"
        print "produce the psycopg2 library to be built incorrectly:"
        for pkg in conflicting:
            print pkg
        sys.exit(1)

def _activate_virtualenv():
    """Activate the virtualenv."""
    activate_this = os.path.abspath(
        "%s/bin/activate_this.py" % env.virtualenv)
    execfile(activate_this, dict(__file__=activate_this))

def _create_virtualenv(clear=False):
    """Create the virtualenv."""
    if not os.path.exists(VIRTUALENV) or clear:
        virtualenv_bin_path = local('which virtualenv', capture=True)
        virtualenv_version = local("%s %s --version" % (
            sys.executable, virtualenv_bin_path), capture=True)
        args = '--distribute --clear'
        if virtualenv_version < '1.7':
            args += ' --no-site-packages'
        local("%s %s %s %s" % (sys.executable,
            virtualenv_bin_path, args, VIRTUALENV), capture=False)

def _create_local_cfg():
    config = textwrap.dedent("""
        [__noschema__]
        basedir = %s
        db_host = %s/db

        [__main__]
        includes = config/devel.cfg
    """ % (os.path.abspath(os.curdir), env.virtualenv))
    config += "test_dsn = host=%(db_host)s dbname=%(db_name)s user=%(db_user)s"

    with file('django_project/local.cfg', 'w') as local_cfg:
        local_cfg.write(config)

def _link_m2crypto():
    version = '%d.%d' % sys.version_info[:2]
    with lcd('%s/lib/python%s/site-packages' % (env.virtualenv, version)):
        local('rm -rf M2Crypto*')
        local('ln -s /usr/lib/python%s/dist-packages/M2Crypto* .' % version)

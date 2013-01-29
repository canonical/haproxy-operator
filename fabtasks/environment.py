# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
import os
import sys

from fabric.api import env, local
from fabric.context_managers import lcd

from .constants import VIRTUALENV


def bootstrap(download_cache_path=None):
    """Bootstrap the development environment."""
    setup_virtualenv()
    install_dependencies(download_cache_path)


def clean():
    """Clean up compiled and backup files."""
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


def virtualenv_local(command, capture=True):
    """Run a command inside the virtualenv."""
    prefix = ''
    virtual_env = env.get('virtualenv', None)
    if virtual_env:
        prefix = ". %s/bin/activate && " % virtual_env
    command = prefix + command
    return local(command, capture=capture)


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
                               virtualenv_bin_path, args, VIRTUALENV),
              capture=False)

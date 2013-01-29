import os

from .constants import VIRTUALENV
from .environment import virtualenv_local, clean


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
HOOKS_DIR = os.path.join(ROOT_DIR, 'hooks')
TEST_PREFIX = 'PYTHONPATH=%s' % HOOKS_DIR
TEST_DIR = os.path.join(ROOT_DIR, 'tests')


def test():
    """Run unit tests."""
    test_arguments = [
        '--with-coverage',
        '--cover-package=hooks',
        '--cover-erase',
        '--cover-xml',
        '--with-yanc',
        '--with-xtraceback',
    ]
    cmd = '%s nosetests %s %s' % (
        TEST_PREFIX,
        ' '.join(test_arguments),
        TEST_DIR,
    )
    virtualenv_local(cmd, capture=False)


def lint():
    """Check for code style and other visual organization issues."""
    venv_dir = os.path.join(ROOT_DIR, VIRTUALENV)
    cmd = 'flake8 %s --exclude=%s/*' % (ROOT_DIR, venv_dir)
    virtualenv_local(cmd, capture=False)


def build():
    """Run build."""
    test()
    lint()
    clean()


def watch():
    test_arguments = [
        '--with-notify',
        '--no-start-message',
        '--with-yanc',
        '--with-xtraceback',
    ]
    cmd = '%s tdaemon --custom-args="%s" %s' % (
        TEST_PREFIX,
        ' '.join(test_arguments),
        TEST_DIR,
    )
    virtualenv_local(cmd, capture=False)

import os

from .constants import VIRTUALENV
from .environment import virtualenv_local, clean


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def test():
    """Run unit tests."""
    test_prefix = 'PYTHONPATH=hooks'
    test_arguments = [
        '--with-coverage',
        '--cover-package=hooks',
        '--cover-erase',
        '--with-yanc',
        '--with-xtraceback',
    ]
    tests_dir = os.path.join(ROOT_DIR, 'tests')
    cmd = '%s nosetests %s %s' % (
        test_prefix,
        ' '.join(test_arguments),
        tests_dir,
    )
    virtualenv_local(cmd, capture=False)


def check_style():
    """Check for code style and other visual organization issues."""
    venv_dir = os.path.join(ROOT_DIR, VIRTUALENV)
    cmd = 'flake8 %s --exclude=%s/*' % (ROOT_DIR, venv_dir)
    virtualenv_local(cmd, capture=False)


def build():
    """Run build."""
    test()
    check_style()
    clean()

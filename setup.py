#!/usr/bin/env python
import os
import sys

vi = sys.version_info
if vi.major != 2 or vi.minor not in (6, 7):
    raise Exception("Enversion requires either Python 2.6 or 2.7.")

try:
    from setuptools import setup
    has_setuptools = True
except ImportError:
    has_setuptools = False
    from distutils.core import setup

def find_packages(dir_):
    packages = []
    for pkg in ['evn']:
        for _dir, subdirectories, files in (
                os.walk(os.path.join(dir_, pkg))
            ):
            if '__init__.py' in files:
                lib, fragment = _dir.split(os.sep, 1)
                packages.append(fragment.replace(os.sep, '.'))
    return packages

def run_setup():
    setup(
        name='enversion',
        version='0.1',
        license=open('LICENSE').read(),
        description='Enterprise Subversion Framework',
        author='Trent Nelson',
        author_email='trent@snakebite.org',
        url='http://www.enversion.org/',
        packages=find_packages(''),
        package_dir={'evn': 'evn'},
        scripts=['scripts/evnadmin'],
    )

if __name__ == '__main__':
    run_setup()

# vim:set ts=8 sw=4 sts=4 tw=78 et:

"""Instalation script."""
import os
import sys
import version


from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

pyversion = sys.version[:3]

def read_requirements():
    requirements = []
    with open(os.path.join(os.path.dirname(__file__), 'requirements.txt')) as req:
        for line in req:
            nline = line.replace("\n", "")
            if nline != "":
                requirements.append(line.replace("\n", ""))
    return requirements

install_requires = read_requirements()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='monitorClient',
    version=version.__version__,
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    license='MIT License',
    description='Data loading tools for large scale monitoring systems. Client side.',
    long_description=README,
    url='https://github.com/erobredo/monitor-server',
    author=(
        'Everardo Gustavo Robredo Esquivelzeta'
    ),
    author_email=(
        'erobredo@conabio.gob.mx'
    ),
    install_requires=install_requires,
    classifiers=[
        'Programming Language :: Python :: 3.11',
    ],
)

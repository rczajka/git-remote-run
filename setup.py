#!/usr/bin/env python
#
from setuptools import setup, find_packages
import git_remote_run


setup(
    name='git-remote-run',
    version=git_remote_run.__version__,
    author='Radek Czajka',
    author_email='rczajka@rczajka.pl',
    url='https://github.com/rczajka/git-remote-run',
    packages=find_packages(),
    entry_points={
        'console_scripts': ['git-remote-run=git_remote_run:run']
    },
    python_requires='>=3.3',
    license='MIT',
    description='Allows running custom commands on a git remote.',
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Version Control :: Git',
    ],
)

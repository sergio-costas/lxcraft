#!/usr/bin/env python3

import os
import sys
from glob import glob
from setuptools import setup

setup(
    name='lxcraft',

    version='0.2',

    author_email='sergio.costas@canonical.com',

    license='GPLv3',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        # 1 - Planning
        # 2 - Pre-Alpha
        # 3 - Alpha
        # 4 - Beta
        # 5 - Production/Stable
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
    ],
    data_files=[
        ('/etc/bash_completion.d', ['lxcraft.completion']),
        ('share/lxcraft', ['lxcraft_gen_container_env.py', 'lxcraft.completion', 'lxcraft_process_folder.py']),
    ],
    scripts=['lxcraft.py'],
)

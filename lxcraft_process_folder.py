#!/usr/bin/env python3

import os
import sys

main_folder = sys.argv[1]

if os.path.exists(os.path.join(main_folder, ".git")):
    os.system(f'cd {main_folder} && git config --global --add safe.directory {main_folder}')

#!/usr/bin/env python3

import os
import glob
import sys

last_log = None
last_date = None
for log in glob.glob('/root/.cache/snapcraft/log/*.log'):
    file_date = os.path.getmtime(log)
    if (last_date is None) or (last_date < file_date):
        last_log = log
        last_date = file_date
if last_log is None:
    print("No log found. Working environment not generated")
    sys.exit(0)
with open(last_log, "r") as log_file:
    log_data = [line.strip() for line in log_file.readlines()]

env_lines = []
total_lines = len(log_data)
do_copy = False
for line in log_data:
    if line == '# Environment':
        if do_copy:
            continue
        do_copy = True
        env_lines = []
    if not do_copy:
        continue
    if len(line) == 0:
        continue
    if line[0] == '#':
        continue
    if line.startswith("export "):
        env_lines.append(line)
        continue
    do_copy = False
with open("/envi.sh", "w") as envifile:
    for line in env_lines:
        envifile.write(line+"\n")
print("To activate the working environment, just type 'source /envi.sh'.")


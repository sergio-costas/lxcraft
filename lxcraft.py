#!/usr/bin/env python3

# Copyright 2022 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import yaml
import getopt
import os
import glob
import logging
import hashlib

if (len(sys.argv) > 1) and (sys.argv[1] == 'snapcraft'):
    options = [[], sys.argv]
else:
    options = getopt.gnu_getopt(sys.argv, "v", [])

def print_options():
    print("Usage: lxcraft [init|destroy|update|build|clean|shell| snapcraft XXXX ] [-v]")
    print("  init: initializes the container and installs the needed .deb packages")
    print("  destroy: destroys the container")
    print("  update: updates the .deb packages")
    print("  build: builds the .snap file")
    print("  clean: deletes all the files in the build folder, to start over")
    print("  snapcraft XXXX: executes the command XXXX with snapcraft inside the container")
    print("  shell: opens a shell inside the container")
    print("  installdeps: installs in the local system the snap dependencies")
    print("  help: shows this help")


if len(options[1]) == 1:
    print_options()
    sys.exit(-1)

debug_param = False
for o in options[0]:
    if o[0] == '-v':
        debug_param = True

command = options[1][1]

data = yaml.safe_load(open("lxcraft.yaml", "r"))
vmname = data['vmname']

main_folder = f"craft_{hashlib.md5(vmname.encode('utf-8')).hexdigest()}"

if 'debs' in data:
    debs = data['debs']
else:
    debs = []

if ('force_debug' in data) and (data['force_debug']):
    debug_param = True

logging.basicConfig(level=logging.INFO)

def find_gen_container_env():
    path_list = [ '/usr', '/usr/local', os.path.join(os.path.expanduser('~'), '.local') ]
    last_date = None
    last_file = None
    for path in path_list:
        file_name = os.path.join(path, 'share', 'lxcraft', 'lxcraft_gen_container_env.py')
        if not os.path.exists(file_name):
            continue
        file_date = os.path.getmtime(file_name)
        if (last_date is None) or (last_date < file_date):
            last_date = file_date
            last_file = file_name
    return last_file

def copy_gen_container_env():
    filepath = find_gen_container_env()
    if filepath is None:
        return
    run_in_vm('rm /usr/bin/lxcraft_gen_container_env.py')
    copy_file_into(filepath, '/usr/bin')
    run_in_vm('chmod 755 /usr/bin/lxcraft_gen_container_env.py')

def copy_file_into(file, destination):
    global vmname

    if (destination[0] != '/'):
        destination = '/' + destination
    run_in_vm(f'-- sh -c "mkdir -p {destination}"')
    retval = os.system(f"lxc file push {file} {vmname}{destination}/")


def run_in_vm(command):
    global vmname
    return os.system(f"lxc exec {vmname} {command}")


def run_in_vm_raise(command):
    retval = run_in_vm(command)
    if (retval != 0):
        logging.error(f"Error while executing '{command}' inside the VM")
        sys.exit(retval)

def run_shell_in_vm(command):
    return run_in_vm(f'-- sh -c "{command}"')

def run_shell_in_vm_raise(command):
    retval = run_shell_in_vm(command)
    if (retval != 0):
        logging.error(f"Error while executing '{command}' inside the VM in a shell")
        sys.exit(retval)

def update_vm():
    run_in_vm_raise("-- apt update")
    run_in_vm_raise("-- apt dist-upgrade -yy")


def get_snap(snap):
    if ('*' in snap) or ('?' in snap):
        # expand the name and get the most recent snap
        last_date = None
        last_snap = None
        for f in glob.glob(snap):
            file_date = os.path.getmtime(f)
            if (last_date is None) or (last_date < file_date):
                last_snap = f
                last_date = file_date
        if last_snap is None:
            logging.error(f"No snap found at {snap}")
            return None
        snap = last_snap
    if not os.path.exists(snap):
        logging.error(f"The snap file {snap} doesn't exist")
        return None
    else:
        return snap


def install_snaps():
    global data
    global vmname
    global debs

    deblist = 'snapd build-essential coreutils rsync'
    for deb in debs:
        deblist += " " + deb
    logging.info(f"Installing packages {deblist}")
    run_in_vm_raise(f"-- apt install -yy " + deblist)

    if 'snaps' not in data:
        return 0
    run_shell_in_vm('mkdir -p /local_snaps')
    for snap in data['snaps']:
        local = False
        name = snap
        params = data['snaps'][snap]
        command = "-- snap install "
        if 'local' in params:
            logging.info(f"Installing local snap: {snap}")
            snap = get_snap(snap)
            if snap is None:
                sys.exit(-1)
            copy_file_into(snap, '/local_snaps')
            local = True
            name = f'/local_snaps/{os.path.basename(snap)}'
        else:
            if 'edge' in params:
                command += '--edge '
        if local:
            command += "--dangerous "
        if 'classic' in params:
            command += "--classic "
        command += name
        run_in_vm_raise(command)
    run_shell_in_vm('rm -rf /local_snaps')


def check_syntax():
    global data
    global main_folder

    for snap in data['snaps']:
        params = data['snaps'][snap]
        if params is None:
            logging.error(f"Snap {snap} lacks parameters. Aborting.")
            sys.exit(-1)
        if ('local' not in params) and ('store' not in params):
            logging.critical(f"Snap {snap} lacks 'store' or 'local' definition. Aborting.")
            sys.exit(-1)
    snap_path = None
    for path in ['./', './snap']:
        full_file = os.path.join(path, 'snapcraft.yaml')
        if os.path.exists(full_file):
            snap_path = full_file
            break
    if snap_path is None:
        logging.critical("Snapcraft.yaml file not found")
        sys.exit(-1)
    linenum = 0
    with open(snap_path, "r") as snapcraft_file:
        for line in snapcraft_file.readlines():
            linenum += 1
            if main_folder in line:
                logging.error(f"Found the LXCraft's main folder, {main_folder}, at line {linenum} of the snapcraft.yaml file.")

check_syntax()

if (command == 'init'):
    retval = os.system(f"lxc launch images:{data['image']} {vmname}")
    if retval != 0:
        sys.exit(retval)
    update_vm()
    sys.exit(0)

elif command == 'destroy':
    logging.info(f"Stopping {vmname}")
    retval = os.system(f"lxc stop {vmname}")
    logging.info(f"Destroying {vmname}")
    retval = os.system(f"lxc delete {vmname}")
    sys.exit(retval)

elif command == 'update':
    update_vm()
    sys.exit(0)

elif command == 'build':
    install_snaps()
    os.system('rm -f data_for_vm.tar')
    if 'files' in data:
        tarlist = ""
        for f in data['files']:
            tarlist += ' ' + f
    else:
        tarlist = ' *'
    os.system(f"tar cf data_for_vm.tar {tarlist}")
    run_shell_in_vm_raise('rm -rf /tartmp')
    run_shell_in_vm_raise(f'mkdir -p /{main_folder}')
    run_shell_in_vm_raise('mkdir -p /tartmp')
    copy_file_into('data_for_vm.tar', '/tartmp')
    os.system('rm -f data_for_vm.tar')
    os.system('rm -f created_snaps.tar')
    run_shell_in_vm_raise("cd /tartmp && tar xf data_for_vm.tar")
    run_shell_in_vm_raise(f"rsync -a /tartmp/ /{main_folder}/")
    run_shell_in_vm_raise('rm -rf /tartmp')
    run_shell_in_vm_raise('mkdir -p /root/.cache/snapcraft/log/old_logs')
    run_shell_in_vm_raise('mv /root/.cache/snapcraft/log/*.log /root/.cache/snapcraft/log/old_logs/')
    run_shell_in_vm_raise(f'cd /{main_folder} && rm -f data_for_vm.tar && rm -f *.snap && snapcraft {"-v" if debug_param else ""} --destructive-mode')
    run_shell_in_vm_raise(f'cd /{main_folder} && rm -f created_snaps.tar && tar cf created_snaps.tar *.snap')
    os.system(f'lxc file pull {vmname}/{main_folder}/created_snaps.tar .')
    run_shell_in_vm_raise('rm -f created_snaps.tar')
    os.system('tar xf created_snaps.tar')
    os.system('rm -f created_snaps.tar')

    sys.exit(0)

elif command == 'clean':
    run_shell_in_vm_raise(f"rm -rf /{main_folder}")
    sys.exit(0)

elif command == 'shell':
    # keep it updated
    copy_gen_container_env()
    run_in_vm('lxcraft_gen_container_env.py')
    run_in_vm('bash')
    sys.exit(0)

elif command == 'help':
    print_options()
    sys.exit(-1)

elif sys.argv[1] == 'snapcraft':
    if len(sys.argv) == 2:
        logging.error("The snapcraft command requires at least one parameter.")
        sys.exit(-1)

    cmd = f'cd /{main_folder} && snapcraft {"-v" if debug_param else ""}'
    for p in sys.argv[2:]:
        cmd += " " + p

    cmd += " --destructive-mode"
    run_shell_in_vm_raise(cmd)
    sys.exit(0)

elif sys.argv[1] == 'installdeps':
    for snap in data['snaps']:
        local = False
        name = snap
        params = data['snaps'][snap]
        command = "snap install "
        if 'local' in params:
            logging.info(f"Installing local snap: {snap}")
            snap = get_snap(snap)
            if snap is None:
                sys.exit(-1)
            copy_file_into(snap, '/local_snaps')
            local = True
            name = snap
        else:
            if 'edge' in params:
                command += '--edge '
        if local:
            command += "--dangerous "
        if 'classic' in params:
            command += "--classic "
        command += name
        os.system(command)

else:
    print(f"Unknown command {command}")
    print()
    print_options()
    sys.exit(-1)

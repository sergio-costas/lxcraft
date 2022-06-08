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

options = getopt.gnu_getopt(sys.argv, "", [])

def print_options():
    print("Usage: lxcraft [init|destroy|update|build|clean|shell]")
    print("  init: initializes the container and installs the needed .deb packages")
    print("  destroy: destroys the container")
    print("  update: updates the .deb packages")
    print("  build: builds the .snap file")
    print("  clean: deletes all the files in the build folder, to start over")
    print("  shell: opens a shell inside the container")


if len(options[1]) == 1:
    print_options()
    sys.exit(-1)

command = options[1][1]

data = yaml.safe_load(open("lxcraft.yaml", "r"))
vmname = data['vmname']

if 'debs' in data:
    debs = data['debs']
else:
    debs = []

def copy_file_into(file, destination):
    global vmname

    if (destination[0] != '/'):
        destination = '/' + destination
    run_in_vm(f'-- sh -c "mkdir -p {destination}"')
    retval = os.system(f"lxc file push {file} {vmname}{destination}/")
    run_in_vm(f"ls {destination}")


def run_in_vm(command):
    global vmname
    return os.system(f"lxc exec {vmname} {command}")


def run_in_vm_raise(command):
    retval = run_in_vm(command)
    if (retval != 0):
        print(f"Error while executing '{command}' inside the VM")
        sys.exit(retval)

def run_shell_in_vm(command):
    return run_in_vm(f'-- sh -c "{command}"')

def run_shell_in_vm_raise(command):
    retval = run_shell_in_vm(command)
    if (retval != 0):
        print(f"Error while executing '{command}' inside the VM in a shell")
        sys.exit(retval)

def update_vm():
    run_in_vm_raise("-- apt update")
    run_in_vm_raise("-- apt dist-upgrade -yy")


def install_snaps():
    global data
    global vmname
    global debs

    deblist = 'snapd build-essential coreutils rsync'
    for deb in debs:
        deblist += " " + deb
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
            print(f"Installing local snap: {snap}")
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
                    continue
                snap = last_snap
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

    for snap in data['snaps']:
        params = data['snaps'][snap]
        if params is None:
            print(f"Snap {snap} lacks parameters. Aborting.")
            sys.exit(-1)
        if ('local' not in params) and ('store' not in params):
            print(f"Snap {snap} lacks 'store' or 'local' definition. Aborting.")
            sys.exit(-1)


check_syntax()

if (command == 'init'):
    retval = os.system(f"lxc launch images:{data['image']} {vmname}")
    if retval != 0:
        sys.exit(retval)
    update_vm()
    sys.exit(0)

elif command == 'destroy':
    print(f"Stopping {vmname}")
    retval = os.system(f"lxc stop {vmname}")
    if (retval == 0):
        print(f"Destroying {vmname}")
        retval = os.system(f"lxc delete {vmname}")
    sys.exit(retval)

elif command == 'update':
    update_vm()
    sys.exit(0)

elif command == 'build':
    install_snaps()
    os.system('rm -f data_for_vm.tar')
    os.system(f"tar cf data_for_vm.tar *")
    run_shell_in_vm_raise('rm -rf /tartmp')
    run_shell_in_vm_raise('mkdir -p /src')
    run_shell_in_vm_raise('mkdir -p /tartmp')
    copy_file_into('data_for_vm.tar', '/tartmp')
    os.system('rm -f data_for_vm.tar')
    os.system('rm -f created_snaps.tar')
    run_shell_in_vm_raise("cd /tartmp && tar xf data_for_vm.tar")
    run_shell_in_vm_raise("rsync -a /tartmp/ /src/")
    run_shell_in_vm_raise(f'cd /src && rm -f *.snap && snapcraft pack --destructive-mode')
    run_shell_in_vm_raise('cd /src && rm -f created_snaps.tar && tar cf created_snaps.tar *.snap')
    os.system(f'lxc file pull {vmname}/src/created_snaps.tar .')
    run_shell_in_vm_raise('rm -f created_snaps.tar')
    os.system('tar xf created_snaps.tar')
    os.system('rm -f created_snaps.tar')

    sys.exit(0)

elif command == 'clean':
    run_shell_in_vm_raise("rm -rf /src")
    sys.exit(0)

elif command == 'shell':
    run_in_vm('sh')
    sys.exit(0)

elif command == 'help':
    print_options()
    sys.exit(-1)

elif command == 'snapcraft':
    if len(sys.argv) == 2:
        print("The snapcraft command requires at least one parameter.")
        sys.exit(-1)

    cmd = "cd /src && snapcraft"
    for p in sys.argv[2:]:
        cmd += " " + p

    cmd += " --destructive-mode"
    run_shell_in_vm_raise(cmd)
    sys.exit(0)

else:
    print(f"Unknown command {command}")
    print()
    print_options()
    sys.exit(-1)

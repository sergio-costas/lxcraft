# lxcraft

Simplifies building snap files that depend on locally modified snap files.

It builds the snap inside a LXC container using "--destructive-mode", which
allows to do it in a safe way. Everything is defined with a YAML file.

## Uninstalling old, non-pip versions of LXCraft

If the installer says that it can't uninstall lxcraft because it is a
distutils-installed program, you must first manually remove it from the
system with the 'uninstall-old.sh' script.

Also, if it was installed locally in your $HOME folder, then you should
delete any file or folder that contains 'lxcraft' that is located in
your *$HOME/.local* folder.

## Installing LXCraft

Just run at the source folder:

    python3 -m pip install .

If you receive an error, ensure that the source folder doesn't have any of
these folders:

    build
    dist
    lxcraft.egg-info

If they do exist, delete them and try again. Also, ensure that no old, pre-pip
versions are installed, removing them with the 'uninstall-old.sh' script.

## BASH completion

If you installed lxcraft without SUDO, you won't have bash completion support.
To fix this, just add to your ~/.bashrc file, at the end:

    source "$HOME/.local/share/lxcraft/lxcraft.completion"

and any new shell will have completion.

## YAML format

This is an example configuration file:

    vmname: gtk3test
    image: ubuntu/jammy

    force_debug: False

    snaps:
      core22:
        - store
        - edge
      gtk-common-themes:
        - store
      /home/raster/workspace/snapcraft/snapcraft*.snap:
        - classic
        - local
      /home/raster/workspace/gnome-sdk/gnome-sdk.snap:
        - local

    debs:
      - cmake
      - lint

    files:
      - meta/snapcraft.yaml
      - icon.png

* vmname contains the name for the LXC container

* image: the image from which generate the container

* snaps: an optional list with the snaps to install inside the
container before building the snap. They can be obtained from the
store or from a local file. If it is local, the name can contain
wildcards, in which case the most recent file matching the expression
will be installed. An important detail is that the order is preserved,
so it is possible to specify a local snap to be installed before
another from the store that depends on that, thus ensuring that
the local will be installed. Each snap can have these elements:

  * store: it means that the snap must be downloaded from the SNAP store

  * local: the snap is located in the local drive, in the specified path

  * classic: the snap requires the --classic parameter to be installed

  * edge: only for 'store' snaps, specifies to install from latest/edge

* debs: contains a list of .deb files to be installed inside the
container before building the snap. It is optional.

* files: contains a list of files and/or folders to copy into the working
folder inside the container. It is optional; if it isn't specified, all
the files and folders will be copied inside.

* force_debug: if it is *True*, it will pass always the *-v* parameter to
*snapcraft*.


## Using lxcraft

Just create a configuration file called *lxcraft.yaml* in your project's
folder and then run:

    lxcraft.py init
    lxcraft.py build

It will create the container, install the snaps and .deb files, copy
all the files in the current folder into the container, create the
snap, and copy it outside the container.

To update the packages inside the container, just use *lxcraft.py update*.
It will do:

    apt update
    apt dist-upgrade -yy

inside the container.

To destroy the container, just use *lxcraft.py destroy*. It can be
regenerated with *lxcraft.py init* again if needed.

You can user *lxcraft.py clean* to fully remove the working directory
inside the container, thus allowing to start from the beginning
with *snapcraft* but without having to destroy and re-recreate the
container from scratch.

Also, you can run specific *snapcraft* commands inside the container
with *lxcraft.py snapcraft command ...*. This allows to clean an
specific part, or to just execute one part...

Finally, it is possible to run a shell inside the container just
with *lxcraft.py shell*.

You can also pass the *-v* parameter, which will be added to *snapcraft*
when called.

## Accessing the container data

The files specified in the *list* part of the configuration file are
copied inside the container into the */craft_XXXXXXXXX* folder, where
XXXXXXX is the MD5 hash of the project's name. This is done to ensure
that the specific lxcraft folder isn't used in a *snapcraft.yaml*
file, and that only the $CRAFT_XXXXX environment variables are used
(in fact, lxcraft will check if the folder appears inside the
*snapcraft.yaml* file, and show an error in that case).

It is also in this folder where the snapcraft folders (like *parts*,
*stage* or *prime*) are located, so it is easy to enter inside and
check the status of the files after a failed building.

## Activating the build environment

When a shell is launched, *lxcraft* will check the last *.log* file
for the last build environment used, and will generate a file called
*/envi.sh* with it. If you need to try to build something, just run:

    source /envi.sh

and the last build environment will be configured in the shell.

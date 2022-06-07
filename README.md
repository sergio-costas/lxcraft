# lxcraft

Simplifies building snap files that depend on locally modified snap files.

It builds the snap inside a LXC container, and everything is defined with
a YAML file.

## YAML format

This is an example configuration file:

    vmname: gtk3test
    image: ubuntu/jammy

    snaps:
      core22:
        - store
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

* vmname contains the name for the LXC container
* image: the image from which generate the container
* snaps: a list with the snaps to install inside the container before
building the snap. They can be obtained from the store or from a
local file. If it is local, the name can contain wildcards, in
which case the most recent file matching the expression will be
installed. An important detail is that the order is preserved,
so it is possible to specify a local snap to be installed before
another from the store that depends on that, thus ensuring that
the local will be installed.
* debs: contains a list of .deb files to be installed inside the
container before building the snap.

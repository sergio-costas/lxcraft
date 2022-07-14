#!/bin/sh

PYTHONVER=3.10
PREFIX=/usr/local

echo Presuming that you have Python ${PYTHONVER}, and lxcraft was intalled at ${PREFIX}. If not, modify this script.

rm -rf ${PREFIX}/lib/python${PYTHONVER}/dist-packages/lxcraft*
rm ${PREFIX}/bin/lxcraft.py
rm -rf ${PREFIX}/share/lxcraft
rm /etc/bash_completion.d/lxcraft.completion

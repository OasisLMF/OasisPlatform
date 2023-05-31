#!/bin/bash

pkg_list=(
    'celery==5.*'
    'django==3.*'
    oasislmf
    ods-tools
)

if [ "$#" -gt 0 ]; then
    pkg_list=( "$@" )
fi     

PKG_UPDATE=''
for pk in "${pkg_list[@]}"; do
    PKG_UPDATE=$PKG_UPDATE" --upgrade-package $pk"
done

set -e
pip-compile $PKG_UPDATE requirements-worker.in
pip-compile $PKG_UPDATE requirements-server.in
pip-compile $PKG_UPDATE requirements.in

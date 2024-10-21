#!/bin/bash

pkg_list=(
    'ods-tools==3.*'
    'oasislmf==2.*'
    'django==3.*'
    'djangorestframework==3.14.*'
    'celery==5.*'
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
pip-compile $PKG_UPDATE kubernetes/worker-controller/requirements.in

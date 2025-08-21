#!/bin/bash

if [ "$#" -gt 0 ]; then
    pkg_list=( "$@" )

    PKG_UPDATE=''
    for pk in "${pkg_list[@]}"; do
        PKG_UPDATE=$PKG_UPDATE" --upgrade-package $pk"
    done

else
  PKG_UPDATE='--upgrade'
fi     

set -e
pip-compile $PKG_UPDATE requirements-worker.in
pip-compile $PKG_UPDATE requirements-server.in
pip-compile $PKG_UPDATE requirements.in

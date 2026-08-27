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
uv pip compile $PKG_UPDATE requirements-worker.in --output-file requirements-worker.txt
uv pip compile $PKG_UPDATE requirements-server.in --output-file requirements-server.txt
uv pip compile $PKG_UPDATE requirements.in --output-file requirements.txt
uv pip compile $PKG_UPDATE kubernetes/worker-controller/requirements.in --output-file kubernetes/worker-controller/requirements.txt

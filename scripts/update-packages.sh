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
uv pip compile $PKG_UPDATE --python-version 3.12  --no-strip-extras requirements-worker.in --output-file requirements-worker.txt
uv pip compile $PKG_UPDATE --python-version 3.12  --no-strip-extras requirements-server.in --output-file requirements-server.txt
uv pip compile $PKG_UPDATE --python-version 3.12  --no-strip-extras requirements.in --output-file requirements.txt
uv pip compile $PKG_UPDATE --python-version 3.12  --no-strip-extras kubernetes/worker-controller/requirements.in --output-file kubernetes/worker-controller/requirements.txt

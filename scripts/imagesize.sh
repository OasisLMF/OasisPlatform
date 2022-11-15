#!/usr/bin/env bash
IMAGE_NAME=$1
REPORT_NAME=$2
CWD=$(pwd)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR; cd ..

# set default values if not given 
[[ -z $DIVE_HIGHEST_USER_WASTED ]] && export DIVE_HIGHEST_USER_WASTED='0.20'
[[ -z $DIVE_HIGHEST_WASTED_BYTES ]] && export DIVE_HIGHEST_WASTED_BYTES='50mb'
[[ -z $DIVE_LOWSET_EFFICIENCY ]] && export DIVE_LOWSET_EFFICIENCY='0.95'

env | grep DIVE_

set -e 
docker run -v /var/run/docker.sock:/var/run/docker.sock wagoodman/dive $IMAGE_NAME \
  --highestUserWastedPercent $DIVE_HIGHEST_USER_WASTED \
  --highestWastedBytes $DIVE_HIGHEST_WASTED_BYTES \
  --lowestEfficiency $DIVE_LOWSET_EFFICIENCY \
  --ci | tee $CWD/$REPORT_NAME

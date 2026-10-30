#!/bin/bash
# Build the platform docker images (api_server, model_worker, worker_controller)
#
# Usage: ./scripts/build-images.sh [IMAGE_TAG] [--push] [--oasislmf-branch BRANCH]
#                                  [--ods-branch BRANCH] [--odm-branch BRANCH]
#
#   IMAGE_TAG                 tag to apply to all images (default: short git sha of HEAD)
#   --push                    push the built images to docker hub
#   --oasislmf-branch BRANCH  install OasisLMF from git branch (model_worker)
#   --ods-branch BRANCH       install ODS-Tools from git branch (api_server, model_worker)
#   --odm-branch BRANCH       install Oasis-Data-Manager from git branch (api_server, model_worker)

set -e

usage() {
    echo "Usage: $0 [IMAGE_TAG] [--push] [--oasislmf-branch BRANCH] [--ods-branch BRANCH] [--odm-branch BRANCH]"
    echo "  IMAGE_TAG                 tag for the images (default: short git sha)"
    echo "  --push                    push images to docker hub after building"
    echo "  --oasislmf-branch BRANCH  install OasisLMF from git branch (model_worker)"
    echo "  --ods-branch BRANCH       install ODS-Tools from git branch (api_server, model_worker)"
    echo "  --odm-branch BRANCH       install Oasis-Data-Manager from git branch (api_server, model_worker)"
}

# Value for a '--flag VALUE' option, errors if missing
require_value() {
    if [ -z "$2" ] || [[ "$2" == -* ]]; then
        echo "Option $1 requires a value"
        usage
        exit 1
    fi
}

# cd to repo root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR/..

IMAGE_TAG=''
PUSH=false
LMF_BRANCH=''
ODS_BRANCH=''
ODM_BRANCH=''
while [ $# -gt 0 ]; do
    case $1 in
        --push)
            PUSH=true
            ;;
        --oasislmf-branch)
            require_value "$1" "$2"; LMF_BRANCH=$2; shift
            ;;
        --oasislmf-branch=*)
            LMF_BRANCH=${1#*=}
            ;;
        --ods-branch)
            require_value "$1" "$2"; ODS_BRANCH=$2; shift
            ;;
        --ods-branch=*)
            ODS_BRANCH=${1#*=}
            ;;
        --odm-branch)
            require_value "$1" "$2"; ODM_BRANCH=$2; shift
            ;;
        --odm-branch=*)
            ODM_BRANCH=${1#*=}
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            if [ -n "$IMAGE_TAG" ]; then
                echo "Only one IMAGE_TAG can be given"
                usage
                exit 1
            fi
            IMAGE_TAG=$1
            ;;
    esac
    shift
done

if [ -z "$IMAGE_TAG" ]; then
    IMAGE_TAG=$(git rev-parse --short HEAD)
fi

BUILD_ARGS_WORKER=()
BUILD_ARGS_SERVER=()
if [ -n "$LMF_BRANCH" ]; then
    BUILD_ARGS_WORKER+=(--build-arg "oasislmf_branch=${LMF_BRANCH}")
fi
if [ -n "$ODS_BRANCH" ]; then
    BUILD_ARGS_WORKER+=(--build-arg "ods_tools_branch=${ODS_BRANCH}")
    BUILD_ARGS_SERVER+=(--build-arg "ods_tools_branch=${ODS_BRANCH}")
fi
if [ -n "$ODM_BRANCH" ]; then
    BUILD_ARGS_WORKER+=(--build-arg "odm_branch=${ODM_BRANCH}")
    BUILD_ARGS_SERVER+=(--build-arg "odm_branch=${ODM_BRANCH}")
fi

SERVER_IMG="coreoasis/api_server:${IMAGE_TAG}"
WORKER_IMG="coreoasis/model_worker:${IMAGE_TAG}"
CONTROLLER_IMG="coreoasis/worker_controller:${IMAGE_TAG}"

echo "Building images with tag: ${IMAGE_TAG}"
[ -n "$LMF_BRANCH" ] && echo "  oasislmf branch:  ${LMF_BRANCH}"
[ -n "$ODS_BRANCH" ] && echo "  ods-tools branch: ${ODS_BRANCH}"
[ -n "$ODM_BRANCH" ] && echo "  odm branch:       ${ODM_BRANCH}"

docker build -f Dockerfile.api_server "${BUILD_ARGS_SERVER[@]}" -t $SERVER_IMG .
docker buildx build --platform linux/amd64 --load -f Dockerfile.model_worker "${BUILD_ARGS_WORKER[@]}" -t $WORKER_IMG .
docker build -f kubernetes/worker-controller/Dockerfile -t $CONTROLLER_IMG kubernetes/worker-controller/

if [ "$PUSH" = true ]; then
    echo "Pushing images to docker hub"
    docker push $SERVER_IMG
    docker push $WORKER_IMG
    docker push $CONTROLLER_IMG
fi

echo "Done:"
echo "  $SERVER_IMG"
echo "  $WORKER_IMG"
echo "  $CONTROLLER_IMG"

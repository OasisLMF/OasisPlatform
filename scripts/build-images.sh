#!/bin/bash
# Build the platform docker images (api_server, model_worker, worker_controller)
#
# Usage: ./scripts/build-images.sh [IMAGE_TAG] [--push]
#
#   IMAGE_TAG   tag to apply to all images (default: short git sha of HEAD)
#   --push      push the built images to docker hub

set -e

usage() {
    echo "Usage: $0 [IMAGE_TAG] [--push]"
    echo "  IMAGE_TAG   tag for the images (default: short git sha)"
    echo "  --push      push images to docker hub after building"
}

# cd to repo root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR/..

IMAGE_TAG=''
PUSH=false
for arg in "$@"; do
    case $arg in
        --push)
            PUSH=true
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo "Unknown option: $arg"
            usage
            exit 1
            ;;
        *)
            if [ -n "$IMAGE_TAG" ]; then
                echo "Only one IMAGE_TAG can be given"
                usage
                exit 1
            fi
            IMAGE_TAG=$arg
            ;;
    esac
done

if [ -z "$IMAGE_TAG" ]; then
    IMAGE_TAG=$(git rev-parse --short HEAD)
fi

SERVER_IMG="coreoasis/api_server:${IMAGE_TAG}"
WORKER_IMG="coreoasis/model_worker:${IMAGE_TAG}"
CONTROLLER_IMG="coreoasis/worker_controller:${IMAGE_TAG}"

echo "Building images with tag: ${IMAGE_TAG}"
docker build -f Dockerfile.api_server -t $SERVER_IMG .
docker buildx build --platform linux/amd64 --load -f Dockerfile.model_worker -t $WORKER_IMG .
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

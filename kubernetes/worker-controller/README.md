# Oasis worker controller

This application controls the number of workers in a kubernetes cluster based on analyses currently running, worker
deployments available and autoscaling configuration for each worker deployment.

The types of autoscaling configurations supported at the moment are:

- Fixed number of workers. When one or more analyses are running a fixed number of workers will be started. When no more
  analysis is running all workers are shutdown.
- Dynamic scaling based on number of analyses running.
- Dynamic scaling based on tasks size. The number of workers to start is based on the tasks size of all running analysis
  per model. A max worker limit is required to be set to not start too many.

Read the oasis-models chart documentation for more details on how to configure each worker deployment.

## Worker controller settings

Settings can be passed to the application by either using the command line or environment variables.

Argument     | Env. var. name     | Default     | Description
-------------|--------------------|-------------|------------
`--api-host` | `OASIS_API_HOST`   | `localhost` | The hostname of the oasis API
`--api-port` | `OASIS_API_PORT`   | `8000`      | The port of the oasis API
`--secure`   | `OASIS_API_SECURE` | `false`     | Use TLS in web socket communication
`--username` | `OASIS_ADMIN_USER` | `admin`     | The username of the user to use for authentication against the API
`--password` | `OASIS_ADMIN_PASS` | `password`  | The password of the user to use for authentication against the API
`--cluster`  | `CLUSTER`          | `in`        | How to connect to the kubernetes cluster. Either `local` to connect to a cluster on the same machine (development), or `in` to connect to a cluster hosting this container.

## Development

### Build image

Ordinary build:

```
docker build -t coreoasis/worker_controller:dev .
```

If you are behind a proxy and can't verify certificates and want to build locally:

```
docker build -t coreoasis/worker_controller:dev --build-arg PIP_TRUSTED_HOSTS="pypi.org files.pythonhosted.org" .
```

### Access image in your kubernetes cluster

To be able to build and use the image in your kubernets cluster you need to use docker image registry accessible both by
your docker build and the kubernets cluster. In case you don't already have a registry like that you could try one of
these options:

**Windows docker desktop kubernetes**

Create a local image registry and points kubernetes to it:

```
# Setup your local image registry:
docker run -d -p 5000:5000 --restart=always --name registry registry:2

# Publish the image to the registry:
docker tag coreoasis/worker_controller:dev localhost:5000/coreoasis/worker_controller:dev
docker push localhost:5000/coreoasis/worker_controller:dev
```

The image `localhost:5000/coreoasis/worker_controller:dev` will be accessible by kubernetes.

**Minikube**

Before you build your image set the environment variables to use kubernetes docker settings:

```
eval $(minikube docker-env)

docker build -f Dockerfile.api_server -t coreoasis/api_server:dev .
```

The image will be published directly into Minikubes image registry and kubernets can access it as `coreoasis/api_server:
dev`. But we also first need prevent kubernetes from pulling the images by
setting `images.oasis.platform.imagePullPolicy`
and `images.oasis.worker_controller.imagePullPolicy` to `Never` in the oasis-platform chart values.

### Run image in local docker

```
# docker run --rm <-e settings=value ...> coreoasis/worker_controller:dev
docker run --rm \
  -e OASIS_API_HOST=localhost \
  -e OASIS_API_PORT=8000 \
  -e OASIS_ADMIN_USER=admin \
  -e OASIS_ADMIN_PASS=password \
  -e CLUSTER=local \
  coreoasis/worker_controller:dev
```


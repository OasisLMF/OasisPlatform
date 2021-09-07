# Overview

There are three [Helm](https://helm.sh) charts to manage your Oasis deployment on [Kubernetes](https://kubernetes.io/):

* oasis-platform - The platform (Databases, API, UI etc.).
* oasis-models - To manage model deployments.
* oasis-monitoring - Deploys prometheus and Grafana to monitor the cluster.

# Requirements

Before you start make sure all requirements are meet:

* A [Kubernetes](https://kubernetes.io/) cluster - For test purposes it doesn't matter how it is hosted. It can either be local with [Docker desktop](https://www.docker.com/products/docker-desktop) / [Minikube](https://minikube.sigs.k8s.io/docs/) or in a cloud such as [Azure](https://azure.microsoft.com/), [AWS](https://aws.amazon.com/) or [Openshift](https://www.redhat.com/en/technologies/cloud-computing/openshift).  
* [Helm](https://helm.sh) - The package management system we will use to manage our Oasis deployment in Kubernetes.
* [kubectl](https://kubernetes.io/docs/tasks/tools/) - Kubernetes CLI. Required by Helm and necessary to work with our Kubernetes cluster.
* Setup kubectl to point to your Kubernetes cluster.
* Make your model data available on your kubernetes node (more details below).

## Model data

Since this is a pure Kubernetes deployment we need to make sure our Kubernetes node(s) has access to the model data on its filesystem. Then we can mount this data in the worker pod for it to use.

### Script for uploading PiWind

I would recommend using the script to upload the PiWind model data if this is the first deployment and you like to test PiWind:

```
# Clone PiWind git repository
git clone https://github.com/OasisLMF/OasisPiWind.git

# Upload to kubernetes node
./scripts/k8s/upload_piwind_model_data.sh OasisPiWind/
```

The script can easily be modified to upload other models as well.

### Customize the path

If you already have your data available on the node(s) or want to place it in another path you need to change the path in `oasis-models/values.yaml`:

```
modelVolumes:
  - name: piwind-model-data-pv # Name is used to mount the volume in the worker pods
    storageCapacity: 1Gi
    hostPath: /data/model-data/piwind/ # This is the model data path on the kubernetes node
```

# Help scripts

Some clusters run Kubernetes in virtual machines that might be a bit tricky to access. Checkout `scripts/k8s/` for a few scripts to get access to the host node filesystem to modify it or reset it.


# Quick start

To deploy Oasis Platform with a PiWind model:

1. Deploy platform and the PiWind model to the `default` namespace in your cluster: 

    ```
    # In kubernetes/charts/
    helm install platform oasis-platform
    helm install models oasis-models
   
    # If you want monitoring tools
    helm dependency update oasis-monitoring
    helm install monitoring oasis-monitoring
    ```

1. Open a connection to the UI:

    ```
    kubectl port-forward deployment/oasis-ui 8080:3838
    ```

1. Open [http://localhost:8080](http://localhost:8080) in your web browser

# Helm and customization

Helm installation requires a `<name>` parameter. This name can be anything you like and helm will use this name to store metadata about the installation in the cluster. You need to refer to this name in future upgrades.

## Customization

All default settings for a chart are stored in `<chart>/values.yaml`. There are a few ways to change them:

* Use helm with `--set` to override specific values. For example `--set generatePasswords=true` at installation to generate all passwords.
* Make a copy of `<chart>/values.yaml`, edit your copy and then use `-f values-copy.yaml` as parameter to helm.
* Edit `<chart>/values.yaml` directly.

# Installation

Install the platform and then add models.

## Platform

Deployment:

```
# Usage: helm install <name> oasis-platform
# Example:
helm install platform oasis-platform

# Make sure all launched pods get status Running
kubectl get pods
```

Access UI:

```
# API - Make it available on localhost:8000
kubectl port-forward deployment/oasis-server 8000:8000

# UI - Make it available on localhost:8080
kubectl port-forward deployment/oasis-ui 8080:3838
```

## Models

Some settings need to be in sync with values in oasis-platform. In case you customized names or shared-fs path please make sure models are deployed with same settings. Read oasis-models/values.yaml for more details.

The chart will install/update/remove models based on what is defined in your `values.yaml` file. If you remove a model from `values.yaml` next upgrade will remove it from your cluster.

Deployment:

```
# Usage: helm install <name> oasis-models
# Example:
helm install models oasis-models

# Make sure all launched pods get status Running
kubectl get pods
```

## Monitoring

Deployment:

```
# First download chart dependencies
helm dependency update oasis-monitoring

# Then install
helm install monitoring oasis-monitoring

# Make sure all launched pods get status Running
kubectl get pods
```

Access UI:

```
# Grafana UI - login with admin/password
kubectl port-forward deployment/monitoring-grafana 3000:3000
kubectl port-forward statefulset/prometheus-monitoring-kube-prometheus-prometheus 9090
```

Default credentials are admin/password - change after login.

## Ingress

To be implemented

```
helm dependency update oasis-ingress
helm install ingress oasis-ingress
```

# Helm list, upgrade and uninstall

To list Helm deployments in your cluster:

```
helm ls
```

All charts are upgrades and uninstalled in the same way:

```
# Upgrade
# Usage: helm upgrade <name> [oasis-platform|oasis-models|oasis-monitoring]
# Example:
helm upgrade platform oasis-platform

# Uninstall
# Usage: helm uninstall <name1, name2, ...>
# Example:
helm uninstall models monitoring platform
```

Make sure any pending volume termination has finished before you install any new chart again:

```
kubectl get pv
```

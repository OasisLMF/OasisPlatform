# Overview

There are three [Helm](https://helm.sh) charts to manage your Oasis deployment on [Kubernetes](https://kubernetes.io/):

* oasis-platform - The Oasis platform (Databases, API, UI etc.).
* oasis-models - To manage model and worker deployments.
* oasis-monitoring - Deploys [Prometheus](https://prometheus.io/)
  , [Alert manager](https://prometheus.io/docs/alerting/latest/alertmanager/) and [Grafana](https://grafana.com/) to
  monitor the cluster.

# Requirements

Before you start make sure all requirements are meet:

* A [Kubernetes](https://kubernetes.io/) cluster - For test purposes it doesn't matter how it is hosted. It can either
  be local with [Docker desktop](https://www.docker.com/products/docker-desktop)
  / [Minikube](https://minikube.sigs.k8s.io/docs/) or in a cloud such as [Azure](https://azure.microsoft.com/)
  , [AWS](https://aws.amazon.com/) or [Openshift](https://www.redhat.com/en/technologies/cloud-computing/openshift).
* [Helm](https://helm.sh) - The package management system we will use to manage our Oasis deployment in Kubernetes.
* [kubectl](https://kubernetes.io/docs/tasks/tools/) - Kubernetes CLI. Required by Helm and necessary to view/edit/debug
  our Kubernetes cluster.
* Setup kubectl to point to your Kubernetes cluster.
* Make your model data available on your kubernetes node (more details below).

## Model data

Since this is a pure Kubernetes deployment (no cloud yet), we need to make sure our Kubernetes node(s) has access to the model data on
its filesystem. Then we can mount this data in the worker pod for it to use.

### Script for uploading PiWind

The easiest way to get started with PiWind is to use the `scripts/k8s/upload_piwind_model_data.sh`. It will upload all
necessary model files for PiWind to the kubernetes node and place them in `/data/model-data/piwind/`.

```
# Clone PiWind git repository
git clone https://github.com/OasisLMF/OasisPiWind.git

# Upload to kubernetes node
./scripts/k8s/upload_piwind_model_data.sh OasisPiWind/
```

The script can easily be modified to upload other models as well.

### Customize the path

If you already have your model data available on the node(s) or want to place it in another path you need to change the
path in `oasis-models/values.yaml` for each worker:

```
modelVolumes:
  - name: piwind-model-data-pv # Name is used to mount the volume in the worker pods
    storageCapacity: 1Gi
    hostPath: /data/model-data/piwind/ # This is the model data path on the kubernetes host node
```

# Quick start

Make sure you have set everything up correctly by reading [Requirements](#requirements) and [Model data](#model-data).

To deploy the Oasis Platform with a PiWind model (default settings):

1. Deploy platform and the PiWind model to the `default` namespace in your cluster:

    ```
    # If you are in the root of this repository
    cd charts/
   
    helm install platform oasis-platform
    helm install models oasis-models
   
    # If you want monitoring tools
    helm install monitoring oasis-monitoring
    ```

2. Wait for all pods to get either `Running` or `Completed` as status, then everything is up and running!

   ```
   # Manually check
   kubectl get pods
   
   # Or using kubectl wait to block until the everything is ready.
   kubectl wait --for=condition=available --timeout=120s --all deployments
   kubectl wait --for=condition=complete --timeout=120s --all jobs
   ```

3. Open a connection to the UI:

    ```
    kubectl port-forward deployment/oasis-ui 8080:3838
    ```

4. Open [http://localhost:8080](http://localhost:8080) in your web browser

5. Continue to [Accessing user interfaces](#accessing-user-interfaces)
   or [Helm and customization](#helm-and-customization).

# Accessing user interfaces

A kubernetes cluster is by default not accessible from the outside, but there are 3 ways to access the oasis deployment.

## Ingress

The oasis-platform deploys an [ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/) to expose
oasis UI, oasis API, Prometheus, Alert manager and Grafana. To enable it we need to bind the ingress to 2 fake hostnames
and if you run this locally you can fake them and have them redirected to localhost.

Default hostnames are ui.oasis.local and api.oasis.local. You can change them by customizing your deployments.

**Add hostnames on linux:**

```
sudo sh -c 'echo "\n# Oasis Kubernetes cluster hostnames\n127.0.0.1 ui.oasis.local\n127.0.0.1 api.oasis.local\n" >> /etc/hosts'
```

**Add hostnames on Windows:**

1. Open start menu and type `notepad`.
2. Right click on `notepad` and select `Run as administrator`.
3. Open file `File` menu and select `Open`.
4. Paste `c:\windows\system32\drivers\etc\hosts` into the `File name` text field and click `Open`.
5. Append this at the end of the file:

    ```
    # Oasis Kubernetes cluster hostnames
    127.0.0.1 ui.oasis.local
    127.0.0.1 api.oasis.local
    ```

6. Save the file and close notepad.

Now you should be able to access the following pages:

- Oasis API - [https://api.oasis.local](https://api.oasis.local)
- Oasis UI - [https://ui.oasis.local](https://ui.oasis.local)
- Prometheus - [https://ui.oasis.local/prometheus/](https://ui.oasis.local/prometheus/)
- Alert manager - [https://ui.oasis.local/alert-manager/](https://ui.oasis.local/alert-manager/)
- Grafana - [https://ui.oasis.local/grafana/](https://ui.oasis.local/grafana/)

## Port forwarding

Kubectl comes with a built-in port forwarding feature to open a tunnel between your computer and a specific pod:

```
# Access Oasis API on http://localhost:8000
kubectl port-forward deployment/oasis-server 8000:8000

# Access Oasis UI on http://localhost:8080
kubectl port-forward deployment/oasis-ui 8080:3838

# Access Prometheus on http://localhost:9090
kubectl port-forward statefulset/prometheus-monitoring-kube-prometheus-prometheus 9090

# Access Alert manager on http://localhost:90903
kubectl port-forward statefulset/alertmanager-monitoring-kube-prometheus-alertmanager 9093:9093

# Access Grafana on http://localhost:3000
kubectl port-forward deployment/monitoring-grafana 3000:3000
```

## Port forwarding by script

The last option is to use the `scripts/k8s/port-forward.sh` script to bring up a tunnel for every service and close
them on ctrl-c.

# Helm and customization

Helm installation requires a `<name>` parameter. This name can be anything you like, and helm will use this name to store
metadata about the installation in the cluster. You need to refer to this name in future upgrades.

```
helm install <name> <chart>
```

You can also list all your helm installations by `helm ls`.

## Chart settings

All default settings for a chart are stored and described in `<chart>/values.yaml`. There are a few ways to change them:

* Make a copy of `<chart>/values.yaml`, edit your copy and then use `-f values-copy.yaml` as parameter to helm.
* Use helm with `--set` to override specific values. For example `--set ingress.uiHostname=ui.oasis.local` at
  installation to generate the ingress with a specific hostname.
* Edit `<chart>/values.yaml` directly.

The first option is usually the best. It will let you edit all settings easily and keep them to be used for all future
upgrades.

### Example 1 - Set custom credentials

Most default credentials are set to something similar to admin/password, but we probably want to change that. You can
change credentials for everything from databases to UIs but in this example we will change them for Oasis and Grafana
only.

1. First we make a copy of the default values files. We need to change both oasis-platform and oasis-monitoring since
   Oasis exists in platform and Grafana in monitoring:

   ```
   # Make a copy of platform values
   cp oasis-platform/values.yaml platform-values.yaml
   
   # Make a copy of montoring values
   cp oasis-montoring/values.yaml monitoring-values.yaml
   ```
3. Then we need to edit our value files to change the credentials:
    1. Edit `platform-values.yaml` and set the `oasisServer.user` and `oasisServer.password` to your new credentials:
       
       ```
       oasisServer:
         user: oasis
         password: password123
       ```
    2. Edit `monitoring-values.yaml` and set your new password for Grafana (we can't change the username):

       ```
       kube-prometheus-stack:
         grafana:
           adminPassword: password123
 
       ```
4. Apply changes
    1. If this is a first time installation:
       ```
       helm install platform oasis-platform -f platform-values.yaml
       helm install monitoring oasis-monitoring -f platform-values.yaml
       ```
    2. If you already have installed the charts, you can update them:
       ```
       # Check what names you used to install the charts with
       helm ls
       
       # Upgrade charts
       helm upgrade <platform-name> oasis-platform -f platform-values.yaml
       helm upgrade <monitoring-name> oasis-monitoring -f monitoring-values.yaml
       ```
5. You should now be able to use your new credentials in the oasis UI/API and Grafana.


### Example 2 - Set custom ingress hostnames

Let's say we like to set custom hostnames for our ingress. The default values are `ui.oasis.local` and `api.oasis.local`
, but let's change them to `ui.oasis` and `api.oasis`.

Please note that we need two different hostnames since both oasis UI and oasis API needs to be placed in the root.

1. First we make a copy of the default values files:

   ```
   # Make a copy of platform values
   cp oasis-platform/values.yaml platform-values.yaml
   
   # Make a copy of montoring values (not necessary if you don't want to install it)
   cp oasis-montoring/values.yaml monitoring-values.yaml
   ```
2. Then we need to edit our files to change the ingress hostnames.
   1. Edit `platform-values.yaml` and set the `ingress.uiHostname` and `ingress.apiHostname`:

      ```
      ingress:
        # Hostname for Oasis UI, Prometheus, Alert manager and Grafana
        uiHostname: ui.oasis
    
        # Hostname for the Oasis API
        apiHostname: api.oasis
      ```
   2. Edit `monitoring-values.yaml` ingress values for Prometheus, Alert manager and Grafana:

      ```
      kube-prometheus-stack:
        prometheus:
          prometheusSpec:
            externalUrl: 'https://ui.oasis/prometheus/' # Change this
          ingress:
            hosts:
              # Change this
              - ui.oasis.local  # Change this

        alertmanager:
          ingress:
            hosts:
              - ui.oasis.local  # Change this

        grafana:
          ingress:
            hosts:
              - ui.oasis.local # Change this

      ```
   3. Optional: If you also want to change the paths for Prometheus, Alert manager and Grafana you can update these:
      ```
      kube-prometheus-stack:
        prometheus:
          prometheusSpec:
            routePrefix: '/prometheus/' # Change this
          ingress:
            paths:
              - /prometheus/ # Change this

        alertmanager:
          alertmanagerSpec:
            routePrefix: /alert-manager/ # Change this
          ingress:
            paths:
              - /alert-manager/ # Change this

        grafana:
          ingress:
            path: /grafana/ # Change this

      ```
3. Apply changes
   1. If this is a first time installation:
      ```
      helm install platform oasis-platform -f platform-values.yaml
      helm install monitoring oasis-monitoring -f platform-values.yaml
      ```
   2. If you already have installed the charts, you can update them:
      ```
      # Check what names you used to install the charts with
      helm ls
      
      # Upgrade charts
      helm upgrade <platform-name> oasis-platform -f platform-values.yaml
      helm upgrade <monitoring-name> oasis-monitoring -f monitoring-values.yaml
      ```
4. If needed - update your `hosts` file: [Ingress](#ingress)
5. You should now be able to access your ingress on your custom hostnames: https://ui.oasis/, https://ui.oasis/prometheus/, https://ui.oasis/alert-manager/, https://ui.oasis/grafana and https://api.oasis/


## Helm list, upgrade and uninstall

To list Helm deployments in your cluster:

```
helm ls
```

All charts are upgraded and uninstalled in the same way:

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


# Chart details

Make sure to install the platform first before you add models to get them successfully registered.

## oasis-platform

If you want to install the platform with standard settings:

```
# Usage: helm install <name> oasis-platform
# Example:
helm install platform oasis-platform

# Make sure all launched pods get status Running Or Complete
kubectl get pods
```

Once ready you can access Oasis UI and API by reading [Accessing user interfaces](#accessing-user-interfaces).

## Models

Some settings need to be in sync with values in oasis-platform. In case you customized names or shared-fs path please
make sure models are deployed with same settings. Read `oasis-models/values.yaml` for more details.

The chart will install/update/remove models based on what is defined in your `values.yaml` file. If you remove a model
from `values.yaml` next upgrade will remove it from your cluster.

Deployment:

```
kc delete jobs --field-selector status.successful=1 -l oasislmf/type=model-registration

# Usage: helm install <name> oasis-models
# Example:
helm install models oasis-models

# Make sure all launched pods (worker-*) get status Running
kubectl get pods

# Each models deployment will leave a model registration job behind, we can remove finished ones
kubectl delete jobs --field-selector status.successful=1 -l oasislmf/type=model-registration
```

## Monitoring

Deployment:

```
# Usage: helm install <name> oasis-monitoring
# Example:
helm install monitoring oasis-monitoring

# Make sure all launched pods get status Running or Complete
kubectl get pods

# Each models deployment will leave a model registration job behind, we can remove finished ones
kubectl delete jobs --field-selector status.successful=1 -l oasislmf/type=set-grafana-default-dashboard-job
```

Once ready you can access Prometheus, Alert manager och Grafna by reading [Accessing user interfaces](#accessing-user-interfaces).

Default credentials are admin/password.

!!! Please note that upgrading this chart might reset changes in Prometheus, Alert manager and Grafana. Always make a backup of your changes before your upgrade.

# Help scripts

Some clusters run Kubernetes in virtual machines that might be a bit tricky to access. Checkout `scripts/k8s/` for a few
scripts to get access to the host node filesystem to modify it or reset it.

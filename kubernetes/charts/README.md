# Table of contents

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Build images](#build-images)
4. [Quick start](#quick-start)
5. [Accessing user interfaces](#accessing-user-interfaces)
6. [Helm and customization](#helm-and-customization)
7. [Chart details](#chart-details)
8. [Keycloak](#keycloak)
9. [Help scripts](#help-scripts)

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

Since this is a pure Kubernetes deployment (no cloud yet), we need to make sure our Kubernetes node(s) has access to the
model data on its filesystem. Then we can mount this data in the worker pod for it to use.

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

# Build images

We need to build two images from this branch and publish the images in image registry:

- api_server - read the `/README.md` for more details.
- worker_controller - read the `../worker-controller/README.md` for more details.

You need to push these images to an image registry available to your kubernetes system. Docker desktops internal image
registry won't work since it isn't accessible by kubernetes. Check out the worker_controllers README.md for instructions
how to easily setup one locally.

Make sure to upload update your chart settings before upgrade. Default images points to:

```
images:
  oasis:
    platform:
      image: localhost:5000/coreoasis/api_server
      version: dev
    worker_controller:
      image: localhost:5000/coreoasis/worker_controller
      version: dev
```

# Quick start

Make sure you have set everything up correctly by reading [Requirements](#requirements), [Build images](#build-images)
and [Model data](#model-data).

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
oasis UI, oasis API, Prometheus, Alert manager and Grafana. To enable it we need to bind the ingress to a hostnames and
if you run this locally you can fake one (details below) and have them redirected to your kubernetes cluster.

Default hostname is `ui.oasis.local`. You can change it by setting a different one in your chart settings.

### Identify cluster IP

Before we can add our fake host we need to find our cluster ip which depends on what type of kubernetes cluster you are
running.

Here is a short summary of two klusters:

| Type                      | IP                                                                                                                                                                                                 |
|---------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Docker desktop on Windows | 127.0.0.1                                                                                                                                                                                          |
| Minikube                  | <ol><li>Run `minikube tunnel` to expose cluster IP</li><li>Run `kubectl get svc --template="{{range .items}}{{range .status.loadBalancer.ingress}}{{.ip}}{{end}}{{end}}"` to get the IP.</li></ol> |

### Add hostnames

**Add hostname on linux:**

Add the hostname and IP to your `/etc/hosts` file:

```
# Oasis Kubernetes cluster hostname
<IP> ui.oasis.local
```

Or run the `scripts/k8s/set_ingress_ip.sh` script to add and update the IP for you.

**Add hostnames on Windows:**

1. Open start menu and type `notepad`.
2. Right click on `notepad` and select `Run as administrator`.
3. Open file `File` menu and select `Open`.
4. Paste `c:\windows\system32\drivers\etc\hosts` into the `File name` text field and click `Open`.
5. Append this at the end of the file:

    ```
    # Oasis Kubernetes cluster hostname
    127.0.0.1 ui.oasis.local
    ```

6. Save the file and close notepad.

### URLs

Now you should be able to access the following pages:

- Oasis API - [https://ui.oasis.local/api/](https://api.oasis.local/api/)
- Oasis UI - [https://ui.oasis.local](https://ui.oasis.local)
- Keycloak - [https://ui.oasis.local/auth/admin](https://ui.oasis.local/admin/auth/)
- Prometheus - [https://ui.oasis.local/prometheus/](https://ui.oasis.local/prometheus/)
- Alert manager - [https://ui.oasis.local/alert-manager/](https://ui.oasis.local/alert-manager/)
- Grafana - [https://ui.oasis.local/grafana/](https://ui.oasis.local/grafana/)

You might also need to [add](https://www.pico.net/kb/how-do-you-get-chrome-to-accept-a-self-signed-certificate/) the
generated self signed certificate to your browsers trusted certificates
or [add a valid certificate](#set-custom-tls-certificate).

## Port forwarding

Kubectl comes with a built-in port forwarding feature to open a tunnel between your computer and a specific pod:

```
# Access Oasis API on http://localhost:8000
kubectl port-forward deployment/oasis-server 8000:8000

# Access Oasis UI on http://localhost:8080
kubectl port-forward deployment/oasis-ui 8080:3838

# Access Keycloak UI on http://localhost:8081
kubectl port-forward deployment/keycloak 8081:8080

# Access Prometheus on http://localhost:9090
kubectl port-forward statefulset/prometheus-monitoring-kube-prometheus-prometheus 9090

# Access Alert manager on http://localhost:90903
kubectl port-forward statefulset/alertmanager-monitoring-kube-prometheus-alertmanager 9093:9093

# Access Grafana on http://localhost:3000
kubectl port-forward deployment/monitoring-grafana 3000:3000
```

## Port forwarding by script

The last option is to use the `scripts/k8s/port-forward.sh` script to bring up a tunnel for every service and close them
on ctrl-c.

# Helm and customization

Helm installation requires a `<name>` parameter. This name can be anything you like, and helm will use this name to
store metadata about the installation in the cluster. You need to refer to this name in future upgrades.

```
helm install <name> <chart>
```

You can also list all your helm installations by `helm ls`.

## Chart settings

All default settings for a chart are stored and described in `<chart>/values.yaml`. There are a few ways to change them:

* Recommended way: Create your own values.yaml file by merging all chart values into one file:

    ```
    # cd kubernetes/charts/

    for chart in oasis-models oasis-platform oasis-monitoring; do
        echo $chart
        echo -e "###\n### Begin of $chart chart settings ###\n###\n" >> values.yaml
        helm show values $chart | sed '/^## Values/,/^## End/d' >> values.yaml
        echo -e "###\n### End of $chart chart settings ###\n###\n" >> values.yaml
    done
    ```
  Pass the file to all helm operations by `-f values.yaml` and keep the file for future upgrades.

* Make a copy of a specific charts values(`<chart>/values.yaml`), edit your copy and then
  use `-f chart-values-copy.yaml` as parameter to helm.
  If you do not wish to deploy the Oasis PiWind demo model, you will need to add `--set
  workers.piwind_demo=null` to explicitly disable it when deploying models.
* Use helm with `--set` to override specific values. For example `--set ingress.uiHostname=ui.oasis.local` at
  installation to generate the ingress with a specific hostname.
* Edit `<chart>/values.yaml` directly. This is not recommended since the file is part of the repository and might be
  overwritten by accident.

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

Let's say we like to set a custom hostname for our ingress. The default hostname is `ui.oasis.local`, but let's change it to `ui.oasis`.

1. First we make a copy of the default values files:

   ```
   # Make a copy of platform values
   cp oasis-platform/values.yaml platform-values.yaml

   # Make a copy of montoring values (not necessary if you don't want to install it)
   cp oasis-montoring/values.yaml monitoring-values.yaml
   ```
2. Then we need to edit our files to change the ingress hostnames.
    1. Edit `platform-values.yaml` and set the `ingress.uiHostname`:

       ```
       ingress:
         # Hostname for Oasis UI, API, Prometheus, Alert manager and Grafana
         uiHostname: ui.oasis
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
5. You should now be able to access your ingress on your custom hostnames: https://ui.oasis/
   , https://ui.oasis/prometheus/, https://ui.oasis/alert-manager/, https://ui.oasis/grafana and https://api.oasis/

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

### Set custom TLS certificate

The ingress controller will generate a self signed certificate on deployment which your browser will warn you about.
This might be enough for a local or isolated environment but please change this for production.

To use your own certificate:

1. Create a TLS secret of your certificate:

   ```
   # Usage: kubectl create secret tls <name> --key <key file> --cert <cert/pem file>
   kubectl create secret tls oasis-ingress-tls --key certificate.key --cert certificate.crt
   ```

2. Enable chart values to enable your certificate:

    - Set `ingress.tls.providedCertificate` to `true`
    - Set `ingress.tls.providedCertificateSecret` to your secret name.

3. Upgrade your platform:

   ```
   helm upgrade <name> oasis-platform
   ```

### Upgrade

The ingress chart used in the oasis-platform chart sometime fails on upgrade. The workaround when this happens is to run
this before the `helm upgrade`:

```
kubectl delete -A ValidatingWebhookConfiguration platform-ingress-nginx-admission
```

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

Once ready you can access Prometheus, Alert manager och Grafana by
reading [Accessing user interfaces](#accessing-user-interfaces).

Default credentials are admin/password.

!!! Please note that upgrading this chart might reset changes in Prometheus, Alert manager and Grafana. Always make a
backup of your changes before your upgrade.

# Keycloak

[Keycloak](https://keycloak.org) is now the default user manager and authentication service (can be disabled by chart
settings). Read more about Keycloak [here](https://www.keycloak.org/docs/latest/getting_started/index.html).

You can pick your preferred authentication by changing `oasisServer.apiAuthType` to either `keycloak` or `simple` for
the standard simple jwt authentication.

```
oasisServer:
  apiAuthType: keycloak
  oidc:
    endpoint: <open connect endpoint url>
    clientName: <client name>
    clientSecret: <client secret>
```

## Administration console

Read [Accessing user interfaces](#accessing-user-interfaces) on how to access keycloak the administration console or use
the default ingress link:

[https://ui.oasis.local/auth/admin/](https://ui.oasis.local/auth/admin/)

The keycloak administrator user is defined in your oasis-platform chart values:

```
keycloak:
  user: keycloak
  password: password
```

Full admin console documentation is found
on [keycloak.org](https://www.keycloak.org/docs/latest/server_admin/#admin-console).

### Realm Settings

Contains generic settings for the realm. The most interesting one is probably the `Token` tab to set different timeouts.

### Authentication

From here you control the supported authentication methods. You can set password policies such as length and number of
special characters required from the `Password Policy` tab.

### Users

Users are managed in the menu option `Manage / Users`. The user list is not loaded by default but once you
click `View all users`. You can now edit and delete users. New passwords can be set from the Credentials tab of an
opened user.

Create a new user by clicking 'Add user' to the right.

### Groups

Manage groups from here and then add them to each user in the `Manage / Users` page.

## Default settings

The oasis-platform chart creates a default realm (keycloak security context) on the first deployment to manage all
users, credentials, roles etc. for the oasis REST API.

A default REST API user is created on `helm install` and to change the username and password edit the values:

```
keycloak:
  oasisRestApi:
    users:
      # A default user is created at first deployment.
      - username: oasis
        password: password
        admin: true
```

Default username is `oasis` with password `password`.

## Groups

Groups are now supported by creating them in Keycloak and assign them to users. A user can then set groups on objects
like portfolio, model and data files. A user can set all or a subset of the groups the user belongs to and if no group
is set it will automatically get all the users groups.

Users can only modify objects which have the same group.

Analysis will inherit the groups from the portfolio, but for a user to run the analysis it requires the user to be
member of at least one of the models groups.

Empty groups are treated as a group. If a user for example belongs to a group it won't be able to access objects that
belongs to a group and vice versa.

# Help scripts

Some clusters run Kubernetes in virtual machines that might be a bit tricky to access. Checkout `scripts/k8s/` for a few
scripts to get access to the host node filesystem to modify it or reset it.

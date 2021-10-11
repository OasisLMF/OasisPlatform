Local Testing of Platform 2.0
=============================

This is a short guide to get the Kubernetes based Oasis platform up and running on a Linux machine using MiniKube.

* [Helm Chart documentation - Sprint 1](https://github.com/OasisLMF/OasisPlatform/tree/platform-2.0-k8s-as/kubernetes/charts)
* [Worker controller documentation - Sprint 2](https://github.com/OasisLMF/OasisPlatform/tree/platform-2.0-k8s-as/kubernetes/worker-controller)
* [Worker controller - Test cases](https://github.com/OasisLMF/OasisPlatform/blob/platform-2.0-k8s-as-tests/kubernetes/worker-controller/TEST-CASES.md)

## Install dependencies

* [Helm](https://helm.sh/docs/helm/helm_install/)
* [MiniKube](https://minikube.sigs.k8s.io/docs/start/)
* [Kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/#install-using-native-package-management)


## Clone the Oasis repositories


**Platform**
```
git clone https://github.com/OasisLMF/OasisPlatform.git -b platform-2.0-k8s-as-tests
```

**PiWind Model**
```
git clone https://github.com/OasisLMF/OasisPiWind.git
```


## Starting A local Cluster in minikube

### 1. Initialize new cluster
```
$ minikube start
```

### 2. Set cluster permissions for the worker controller
```
kubectl create clusterrolebinding serviceaccounts-cluster-admin \
  --clusterrole=cluster-admin \
  --group=system:serviceaccounts
```

### 3. (Optional) Start the minikube Dashboard
Track the cluster using a web based GUI
```
minikube dashboard
```


## Deploying the Helm charts

### 1. (Optional) Edit the Helm script to set the Oasis Image versions

Update **kubernetes/charts/oasis-platform/values.yaml**
```
# Images and versions used for all deployments
images:
  oasis:
    platform:
      image: <image_name>
      version: <image_tag>
    ui:
      image: <image_name>
      version: <image_tag>
    worker_controller:
      image: <image_name>
      version: <image_tag>

     ...
```

**Example**
```
images:
  oasis:
    platform:
      image: coreoasis/api_server
      version: 2.0.0-rc3
    ui:
      image: coreoasis/oasisui_app
      version: 1.9.0
    worker_controller:
      image: coreoasis/worker_controller
      version: 2.0.0-rc3
       ...
```


### 2. (Optional) Add auto-scaller metadata files

There are two new json files which control the model's scaling parameters these can be uploaded on model registration
If added in the model's mete-data directory

* `meta-data/chunking_configuration.json`
* `meta-data/scaling_configuration.json`

**chunking_configuration.json**
```
{
  "lookup_strategy":              "FIXED_CHUNKS",
  "loss_strategy":                "FIXED_CHUNKS",
  "fixed_analysis_chunks":        20,
  "fixed_lookup_chunks":          5
}
```


**scaling_configuration.json**
```
{
  "scaling_strategy":   "FIXED_WORKERS",
  "worker_count_fixed": 3,
  "worker_count_max":   10,
  "chunks_per_worker":  5
}
```

### 3. Upload Model data
```
cd OasisPlatform/kubernetes/scripts/k8s
./upload_piwind_model_data.sh <path to piwind repo>
```


### 4. Start the Oasis Platform

```
cd OasisPlatform/kubernetes/charts

helm install platform oasis-platform
helm install models oasis-models
helm install monitoring oasis-monitoring
```



## Accessing user interfaces (via Ingress)


### 1. Bind MiniKube to Local host

Connect to LoadBalancer so it can assign an external IP
```
minikube tunnel &> /dev/null &
```

### 2. Check the assigned external IP

kubectl get service platform-ingress-nginx-controller

**Output**
```
$ kubectl get service platform-ingress-nginx-controller
NAME                                TYPE           CLUSTER-IP     EXTERNAL-IP    PORT(S)                      AGE
platform-ingress-nginx-controller   LoadBalancer   10.99.233.36   10.99.233.36   80:30321/TCP,443:32017/TCP   67m
```

### 3. Update the local hosts file

In the example below replace `<EXTERNAL-IP>` with the IP from step 2, `10.99.233.36`
```
sudo sh -c 'echo "\n# Oasis Kubernetes cluster hostnames\n<EXTERNAL-IP> ui.oasis.local\n<EXTERNAL-IP> api.oasis.local\n" >> /etc/hosts'
```

### 4. Access the cluster services

Now you should be able to access the following pages:

*  Oasis API - https://api.oasis.local
*  Oasis UI - https://ui.oasis.local
*  Prometheus - https://ui.oasis.local/prometheus/
*  Alert manager - https://ui.oasis.local/alert-manager/
*  Grafana - https://ui.oasis.local/grafana/




## Accessing user interfaces (Via IP)

### 1. Create a script to forward all the ports

**cluster-port-forwarding.sh**
```
#!/bin/bash

# Access Oasis API on http://localhost:8000
kubectl port-forward deployment/oasis-server 8000:8000 &

# Access Oasis UI on http://localhost:8080
kubectl port-forward deployment/oasis-ui 8080:3838 &

# Access Prometheus on http://localhost:9090
kubectl port-forward statefulset/prometheus-monitoring-kube-prometheus-prometheus 9090 &

# Access Alert manager on http://localhost:9093
kubectl port-forward statefulset/alertmanager-monitoring-kube-prometheus-alertmanager 9093:9093 &

# Access Grafana on http://localhost:3000
kubectl port-forward deployment/monitoring-grafana 3000:3000 &
```

### 2. Run the script in an open terminal

```
$ ./cluster-port-forwarding.sh
Forwarding from 127.0.0.1:8000 -> 8000
Forwarding from [::1]:8000 -> 8000
Forwarding from 127.0.0.1:8080 -> 3838
Forwarding from [::1]:8080 -> 3838

```

### 3. Access the cluster via

*  Oasis API - https://localhost:8000
*  Oasis UI - https://localhost:8080
*  Prometheus - https://localhost:9090
*  Alert manager - https://localhost:9093
*  Grafana - https://localhost:3000


## Docker image Versions

| Image Name  | Tags | Feature Description  |
|---|:---|:---|
| coreoasis/api_server | `2.0.0-sprint2` | First implementation of auto scaler |
| &nbsp; | &nbsp; | &nbsp; |
| coreoasis/worker_controller | `2.0.0-sprint2` | First implementation of auto scaler |
| &nbsp; | &nbsp; | &nbsp; |
| coreoasis/model_worker | `2.0.0-sprint2` | Fixed chunking only |
| &nbsp; | &nbsp; | &nbsp; |




## Misc helpful commands

1. View running pods
```
kubectl get pods
```

2. View pod logs
```
kubectl logs -f <pod-name>
```

3. Shell access to debug a running pod
```
kubectl exec --stdin --tty <pod-name> -- /bin/bash
```

4. Update helm config
```
helm upgrade platform oasis-platform
```

5. Wipe cluster
```
minikube delete
```

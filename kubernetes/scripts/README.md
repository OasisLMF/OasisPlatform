## Bash Scripts

A few helpful scripts for development

### Requirements

 - jq - a command line json parser (Ubuntu: `apt install jq`)

### Overview

| Path                            | Description                                                                                                                           |
|---------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| api/                            | Scripts for the Oasis API                                                                                                             |
| api/api.sh                      | A few basic commands to query the Oasis API and list, run and cancel runs                                                             |
| api/setup_env.sh                | Creates a portfolio and an analysis                                                                                                   |
| k8s/                            | Scripts for the kubernetes API                                                                                                        |
| k8s/upload_piwind_model_data.sh | Upload PiWind model data to the k8s host node (in case it is virtual and difficult to reach)                                          |
| k8s/host_volume_shell.sh        | Creates a pod with a bash shell and mounts the host node /data path. Convenient for reaching the kubernetes host node filesystem.     |
| k8s/clean_host_volume.sh        | Mounts the host nodes volume path and erases everything within - handy to clean the environment, but make sure to uninstall it first. |
| k8s/port-forward.sh             | Sets up port forwarding to access UI, API, Prometheus and Grafana.                                                                    |
| k8s/set_ingress_ip.sh           | For `minikube` on linux - updates your /etc/hosts file with the ingress IP used by `minikube tunnel`                                  |

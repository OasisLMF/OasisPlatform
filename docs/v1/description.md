# API

## On this page

-   `intro_api`{.interpreted-text role="ref"}
-   `oasis_api`{.interpreted-text role="ref"}
-   `deployment_api`{.interpreted-text role="ref"}
-   `links_api`{.interpreted-text role="ref"}

| 

------------------------------------------------------------------------

------------------------------------------------------------------------

Oasis has a full REST API for managing exposure data and operating
modelling workflows. API Swagger documentation can be found
[here](http://api.oasislmfdev.org/swagger/). An evaluation version of
the Oasis platform and using can be deployed using the [Oasis evaluation
repository](https://github.com/OasisLMF/OasisEvaluation). This includes
a Jupyter notebook that illustrates the basic operation of the API,
using the Python API client.

| 

### Oasis API {#oasis_api}

------------------------------------------------------------------------

The Oasis Platform release now includes a full API for operating
catastrophe models and a general consolidation of the platform
architecture. Windows SQL server is no longer a strict requirement. The
platform can be run via docker containers on a single machine or, if
required, scaled up to run on a cluster.

Docker support is the main requirement for running the platform. A Linux
based installation is the main focus of this example deployment. Running
the install script from this repository automates install process of the
OasisPlatform API v1, User Interface and example PiWind model.

The **Oasis API** is the components of the Oasis platform that manages
all the elements of the plaform that are required to build, run, and
test models. The diagram below shows how the **Oasis API** sits behind
the `Oasis-UI`{.interpreted-text role="doc"}, that you use to operate
your catastrophe models.

*Oasis docker componets*:

| 

![Oasis docker componets](../images/oasis_containers.png){.align-center
width="600px"}

| 

### API deployment in the Oasis Enterprise Platform {#deployment_api}

------------------------------------------------------------------------

The **Oasis Enterprise Platform** is an open source
[Kubernetes](https://kubernetes.io/docs/concepts/overview/) based, cloud
computing cluster, which is deployable in [Microsoft Azure
\<https://azure.microsoft.com/en-gb/resources/
cloud-computing-dictionary/what-is-azure/\>]() via [Helm
charts](https://helm.sh/docs/topics/charts/) and [Bicep
scripts](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deployment-script-bicep)
to setup the Azure cloud services. The diagram below sets out the
**Oasis Enterprise Platform** architecture:

![Oasis Enterprise Platform Architecture](../images/diag_oasis_components.png){.align-center
width="600px"}

| 

### Links for further information {#links_api}

------------------------------------------------------------------------

There is more information availible in the [Oasis
GitHub](https://github.com/OasisLMF).

This includes detailed walkthorughs on:

| 

1.  Oasis implementation of [Microsoft
    Azure](https://azure.microsoft.com/en-gb/resources/cloud-computing-dictionary/what-is-azure/).

This guide takes you through the [requirements
\<https://github.com/OasisLMF/OasisAzureDeployment/blob/
master/README.md#1-Requirements\>]() for using this platform, how to
[setup the enviroment \<https://github.com/OasisLMF/
OasisAzureDeployment/blob/master/README.md#2-Setup-environment\>](), how
to [use the platform \<https://github.com/OasisLMF/
OasisAzureDeployment/blob/master/README.md#3-Use-the-platform\>](), how
to [manage resource groups \<https://github.com/
OasisLMF/OasisAzureDeployment/blob/master/README.md#4-Manage-resource-groups\>](),
[deployment without the pipeline \<https://
github.com/OasisLMF/OasisAzureDeployment/blob/master/README.md#5-Deploy-without-the-pipeline\>](),
[securing the
plaform](https://github.com/OasisLMF/OasisAzureDeployment/blob/master/README.md#6-Secure-the-platform),
[troubleshooting \<https://
github.com/OasisLMF/OasisAzureDeployment/blob/master/README.md#7-Troubleshooting\>](),
and it answers some additional [questions about the
design](https://github.com/OasisLMF/OasisAzureDeployment/blob/master/README.md#8-Questions-about-design).

More information can be found
[here](https://github.com/OasisLMF/OasisAzureDeployment/blob/master/README.md#8-Questions-about-design).

| 

2.  How to implement
    [Kubernetes](https://kubernetes.io/docs/concepts/overview/).

This guide takes you through [requirements
\<https://github.com/OasisLMF/OasisPlatform/blob/platform-2.0/kubernetes/charts/
README.md#requirements\>](), how to [build images
\<https://github.com/OasisLMF/OasisPlatform/blob/platform-2.0/kubernetes/
charts/README.md#build-images\>](), a [quick start
\<https://github.com/OasisLMF/OasisPlatform/blob/platform-2.0/kubernetes/
charts/README.md#quick-start\>]() tutorial, how to [access the user
interfaces \<https://github.com/OasisLMF/OasisPlatform/
blob/platform-2.0/kubernetes/charts/README.md#accessing-user-interfaces\>](),
and introduction to [helm and
customisation](https://github.com/OasisLMF/OasisPlatform/blob/platform-2.0/kubernetes/charts/README.md#helm-and-customization),
[chart
details](https://github.com/OasisLMF/OasisPlatform/blob/platform-2.0/kubernetes/charts/README.md#chart-details),
and
[keycloak](https://github.com/OasisLMF/OasisPlatform/blob/platform-2.0/kubernetes/charts/README.md#keycloak),
and how to access [help
scripts](https://github.com/OasisLMF/OasisPlatform/blob/platform-2.0/kubernetes/charts/README.md#help-scripts).

More information can be found
[here](https://github.com/OasisLMF/OasisPlatform/blob/platform-2.0/kubernetes/charts/README.md#helm-and-customization).

| 

3.  How to deploy and manage the Oasis platform on a
    [Kubernetes](https://kubernetes.io/docs/concepts/overview/) cluster.

More information can be found
[here](https://github.com/OasisLMF/OasisPlatform/blob/platform-2.0/kubernetes/README.md).

| 

4.  Oasis Worker Controller.

This application controls the number of workers in a kubernetes cluster
based on analyses currently running, worker deployments available and
autoscaling configuration for each worker deployment.

More information can be found
[here](https://github.com/OasisLMF/OasisPlatform/blob/platform-2.0/kubernetes/worker-controller/README.md).


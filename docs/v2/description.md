# Introduction 

Oasis has a full REST API for managing exposure data and operating
modelling workflows. API Swagger documentation can be found
[here](http://api.oasislmfdev.org/swagger/). An evaluation version of
the Oasis platform and using can be deployed using the [Oasis evaluation
repository](https://github.com/OasisLMF/OasisEvaluation). This includes
a Jupyter notebook that illustrates the basic operation of the API,
using the Python API client.

# Oasis API

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

<img src="https://github.com/OasisLMF/GenerateDocs/blob/feature/update_docs/src/images/oasis_containers.png" alt="Oasis docker componets" style="align-center; width:600px;"/>


# API deployment in the Oasis Enterprise Platform

The **Oasis Enterprise Platform** is an open source
[Kubernetes](https://kubernetes.io/docs/concepts/overview/) based, cloud
computing cluster, which is deployable in [Microsoft Azure](https://azure.microsoft.com/en-gb/resources/cloud-computing-dictionary/what-is-azure/) via 
[Helm charts](https://helm.sh/docs/topics/charts/) and [Bicep scripts](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deployment-script-bicep)
to setup the Azure cloud services. The diagram below sets out the

**Oasis Enterprise Platform** architecture:

<img src="https://github.com/OasisLMF/GenerateDocs/blob/feature/update_docs/src/images/diag_oasis_components.png" alt="Oasis Enterprise Platform Architecture" style="align-center; width:600px;"/>

# Links for further information

There is more information availible in the [Oasis GitHub](https://github.com/OasisLMF).

This includes detailed walkthorughs on:

1.  Oasis implementation of [Microsoft Azure](https://azure.microsoft.com/en-gb/resources/cloud-computing-dictionary/what-is-azure/).
2.  How to implement [Kubernetes](https://kubernetes.io/docs/concepts/overview/).
3.  How to deploy and manage the Oasis platform on a [Kubernetes](https://kubernetes.io/docs/concepts/overview/) cluster.

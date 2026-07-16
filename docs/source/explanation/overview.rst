Overview
========

.. _introduction:

:doc:`/explanation/overview` | :doc:`/explanation/platform_architecture` | :doc:`/how-to/container_configuration` | :doc:`/reference/rest_api` | :doc:`/how-to/distributed_execution` | :doc:`/how-to/distributed_configuration`

Introduction
------------

The **Oasis Loss Modelling Framework (OasisLMF)** is an open-source platform designed for the **development, deployment, and execution of catastrophe models**. These models are crucial for assessing financial risks associated with natural disasters like earthquakes, hurricanes, or floods.

The OasisPlatform Repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^

This repository provides a **reference technical stack** and versioned **Docker images**. The goal is to make the installation process as **quick and easy**, allowing users to get up and running with the Oasis Loss Modelling software without significant setup hurdles.

Key Use Cases for OasisPlatform:

1. Single-Machine Operation for Development and Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For individual users, model developers, or those focused on testing new catastrophe models, OasisLMF can be efficiently run on a single machine. This is achieved using **Docker Compose**, a tool for defining and running multi-container Docker applications. This setup is perfect for:

* **Model Development:** Iterating on new model logic, algorithms, and data sets.
* **Testing and Validation:** Rigorously evaluating the accuracy and performance of models before wider deployment.

You can find more details and guidance on this setup at the `OasisEvaluation GitHub repository <https://github.com/OasisLMF/OasisEvaluation>`_.

2. Cloud-Hosted Loss Modelling Environment for Scalability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For organizations requiring a more robust, scalable, and collaborative environment, OasisLMF can be hosted as a **cloud-based loss modelling platform**. This approach leverages **Kubernetes**, an open-source system for automating the deployment, scaling, and management of containerized applications. Cloud hosting is ideal for:

* **Large-Scale Risk Analysis:** Processing vast amounts of data and running complex simulations that would overwhelm a single machine.
* **Collaborative Workflows:** Enabling multiple teams or users to access and work with catastrophe models simultaneously.
* **Production Environments:** Providing a reliable and highly available platform for critical business operations.

For information on deploying OasisLMF in a cloud environment, specifically on Azure, you can refer to the `OasisAzureDeployment GitHub repository <https://github.com/OasisLMF/OasisAzureDeployment>`_.

Platform Versions and Compatibility
-----------------------------------

The OasisPlatform has evolved over time, offering different approaches to handling catastrophe model workloads. Understanding these versions is key to understanding the two major versions of the platform.

OasisPlatform 1.x.x: Single Server Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The original iteration of the OasisPlatform, versions starting with 1.x.x, was designed for 'single server' execution. In this model, the entire Oasis model workload, including the processing of events, runs within a single container as one large job. The events are distributed across all available cores on that single machine.

It's important to note that this architecture does not support horizontal scaling for execution. This means you can't easily add more machines to distribute the processing load. Additionally, the REST API endpoints in these versions are more limited; for example, they don't offer job prioritization.

This includes the following stable OasisLMF versions where 'x' represents any patch number (e.g., 1.28.0, 1.28.1, etc.):

* 1.15.x
* 1.23.x
* 1.26.x
* 1.27.x
* 1.28.x

OasisPlatform 2.x.x: Distributed and Scalable Workflows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The **second major iteration of the OasisPlatform, with images starting from 2.x.x**, brought about a fundamental rewrite of the execution workflow, introducing significant enhancements for scalability and flexibility. Key improvements in this version include:

* **Distributed Execution:** Workloads can now be **distributed across multiple running workers**, allowing for much greater processing power and efficiency.
* **Automated Scaling:** The platform gained the ability to **automatically scale workers based on system load**, ensuring resources are optimally utilized.
* **Kubernetes Deployment:** The introduction of **Helm charts** facilitates easy deployment of Oasis to **Kubernetes**, making cloud-hosted, scalable environments much more manageable.
* **Enhanced Authentication:** Authentication was extended to use **OpenID Connect (OIDC)**, commonly implemented with solutions like **Keycloak**, replacing the simpler **Simple JWT** for more robust security.
* **Granular Permissions:** **Group permissions** were added for models, portfolios, and analyses, providing finer control over access and collaboration.
* **Job Prioritization:** A **queue priority for analysis jobs** was introduced, allowing users to prioritize critical workloads.

With stable versions like **2.3.x and 2.4.x**, the OasisPlatform now **supports both 'single server' and 'distributed' workflows**. This means you have the flexibility to choose the execution model that best suits your project's scale and requirements.

Docker Images and Version Compatibility
---------------------------------------

The Oasis Platform uses two primary Docker images to operate:

* **coreoasis/model_worker:<version tag>**: This image serves as the base for model suppliers to build upon. Its purpose is to provide an standardized oasis execution environment, that vendors can then customize to their specific model. An Oasis model fundamentally consists of three elements:

  * **A model worker Docker image**: This is the coreoasis/model_worker base image combined with vendor-specific code.
  * **Model metadata**: This defines the model's capabilities, supported perils, and other descriptive information.
  * **Model data**: Model execution data, which is either mounted into or copied onto the running container, as detailed in the Oasis-model-data-formats.html documentation.

* **coreoasis/api_server:<version tag>**: This server image encapsulates all other components necessary to run the Oasis Platform. In **2.x.x platform versions**, this image powers several critical OasisPlatform server components:

  * **API Server**: The RESTful interface for managing exposure data, executing model analyses, and downloading results.
  * **Task Controller**: Responsible for distributing execution workloads across multiple worker nodes (used exclusively in distributed workflows).
  * **Worker Monitor**: Stores results from completed loss analyses.
  * **Websocket**: Reports on the status of the Oasis system to the autoscaling component.

Image Version Compatibility Guidelines
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Oasis Platform is engineered and tested for **backward compatibility** between server and worker images.

This means that if your system is configured to use coreoasis/api_server:2.4.5, it can deployed with any stable model worker image based on a version **equal to or below 2.4.x**.

Specifically, this includes stable worker image bases from versions: 1.15.x, 1.23.x, 1.26.x, 1.27.x, 1.28.x, 2.3.x, and 2.4.x.

Important Exceptions and Limitations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **Unsupported Versions**: Versions 2.1.x and 2.2.x of the worker image are not supported by newer 2.x.x platform versions. We strongly advise against using these.
* **Forward Compatibility**: It is important to understand that servers and workers are **not guaranteed to be forward compatible**. For example, running coreoasis/api_server:1.28.x with worker images from newer versions, such as 2.3.x or 2.4.x is untested by our release process and has a strong possibility of not working. For situations like these we recommend updating the server components to match the version of the most recent model worker version you wish to run.

Platform Architecture
====================

.. _platform_architecture:

:doc:`/explanation/overview` | :doc:`/explanation/platform_architecture` | :doc:`/how-to/container_configuration` | :doc:`/reference/rest_api` | :doc:`/how-to/distributed_execution` | :doc:`/how-to/distributed_configuration`

There is flexibility within the provided tech stack, which is intended to be viewed as a **recommendation** rather than definitive. On the cloud computing side, this is intended to **avoid vendor lock-in** and ensure the platform remains as **portable as possible**, allowing you to deploy OasisLMF across various cloud providers without being tied to a single ecosystem.

This generally applies to third party non-oasis components, like data storage solutions, message brokers and identity providers. As an example, **PostgreSQL** is the default database choice for both **Azure** deployments and **Docker Compose** setups, but this isn't a rigid requirement. You're free to swap it out for any other database or cloud-managed database service that **Django** supports.

Oasis Components
----------------

.. figure:: /_static/images/platform/platform_img_1.svg
    :alt: Oasis platform Components diagram
    :width: 700
    :align: center
|



Purple Boxes: Worker Images
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**coreoasis/model_worker:<version tag>**

These images contain all the necessary OasisLMF software and vendor code to execute a model run. Generally, each model has its own Docker image, built upon the Oasis base. The exception is purely data-driven models, which exclusively use Oasis code.

Red Boxes: Server Images
^^^^^^^^^^^^^^^^^^^^^^^^

**coreoasis/api_server:<version tag>**

These images contain Python packages and Oasis code written for Django and Celery. While they are all based on the same core image, they are configured to fulfill different roles within the system.

Orange Boxes: Optional Oasis Images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These images represent optional components that serve as main ingress points into the system.

* **coreoasis/oasisui_app:<version>**: This image provides a basic web-based graphical user interface (GUI) that interacts with the REST API.
* **coreoasis/worker_controller:<version>**: (Kubernetes deployment only) This container connects to the websocket, monitors for analysis execution requests, and scales the replica set for each model. By default, each worker pod maps to a single node, meaning each requested worker pod runs in its own virtual machine. The exact number of virtual machines depends on the auto-scaling settings.

Roles of Each OASIS Container within the Platform
-------------------------------------------------

The OASIS Platform operates as a microservices-based system, with each container type specializing in a particular function to ensure the scalable, efficient, and reliable execution of loss modeling tasks.

Model Workers - Execution Environment for Oasis Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Model Worker containers are Ubuntu-based Docker images that provide a self-contained Python environment capable of executing Oasis models. They encapsulate all necessary packages and their dependencies to perform the core computational tasks.

The core oasislmf package version and docker image versions are (almost) always matched. So if a worker image is tagged **<version>** then the main python package should also be that same version.

This can be checked in the logs, when a worker connects it self-reports its versions and sends that data back to api server (assessed via **models/{id}/versions**):

.. code-block:: text

    [log timestamp] versions: {'oasislmf': '2.4.5', 'ktools': '3.12.4', 'platform': '2.4.5', 'ods-tools': '4.0.2', 'oed-schema': '4.0.0'}

Key Python packages are:

* **oasislmf** (https://pypi.org/project/oasislmf/): This package provides the core execution kernel for Oasis models, including intermediate file preparation logic and the Financial Module (FM) responsible for calculating financial losses.
* **ods-tools** (https://pypi.org/project/ods-tools/): A package for handling input data. It implements the Open Data Standards (OED) specification to facilitate the loading, validation, and transformation of exposure portfolio data, as well as financial terms and conditions.
* **oasis-data-manager** (https://pypi.org/project/oasis-data-manager/): This component handles the loading and persistent storage of data, interacting with various object storage solutions such as AWS S3 or Azure Blob Storage.

API Server - Centralized Interaction and Core Logic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The API Server container hosts the main RESTful API, serving as the interface for all external interactions with the OASIS cluster, particularly when deployed in a distributed environment. It is hosted by a Gunicorn WSGI (Web Server Gateway Interface) server, ensuring robust handling of concurrent requests. This server exclusively accepts HTTP traffic, providing endpoints for submitting analysis requests, retrieving results, managing model resources, and other platform operations. It acts as the central orchestrator, translating external requests into internal task dispatches.

Worker Monitors - Execution Status and Result Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Worker Monitor containers are dedicated to tracking and reporting the status of Celery-based execution tasks dispatched from the API server. There is typically one Worker Monitor instance per workflow type (e.g., a v1-worker-monitor and a v2-worker-monitor), each responsible for the specific set of queues it observes. Once a Model Worker completes its assigned task (regardless of success or failure), the relevant Worker Monitor is responsible for tasks like:

* Updating the analysis status in the API server's database to RUN_COMPLETED upon successful execution and storing the computed results.
* Updating the analysis status to RUN_ERROR if the execution failed, and diligently saving the associated error logs for diagnostic purposes.

This ensures that the API server always reflects the most current state of ongoing and completed analyses, providing critical feedback to users and other platform components.

Web-Socket Server - Real-time Status Updates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Web-Socket Server container uses the same underlying Django framework and shares access to the same database as the REST API Server. Its function is to push real-time or near real-time status updates to connected clients and other scalable components, such as the Worker Controller, providing insights into model worker availability and overall compute capacity. These status updates are pushed either at a configurable periodic interval (defaulting to once per minute) or immediately triggered by significant events, such as the submission of a new analysis request or the completion of an existing one. This enables dynamic adjustments and a responsive user experience.

Worker Controller - Dynamic Cluster Autoscaling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Worker Controller is the component responsible for the dynamic autoscaling of Model Worker containers within a cluster. It continuously monitors the state of Celery queues and pending tasks. Each Oasis model installed on the platform has its own configurable scaling policy. By default, a model's associated workers scale to 0 when idle (no queued or running analyses) and automatically scale up to a single worker when analyses are queued or actively executing. This scaling behavior is tunable on a per-model basis, allowing administrators to optimize resource allocation for different models based on their anticipated workload and performance requirements.

Celery Beat - Scheduler for Periodic Status Updates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Celery Beat container acts as the scheduler for periodic tasks within the OASIS Celery ecosystem. Its main responsibility is to control the frequency at which the Web-Socket Server pushes its periodic status updates. By default, Celery Beat is configured to trigger these updates once per minute, ensuring a regular heartbeat of information regarding the platform's status.

Task Controller - Distributed Workflow Management (V2 Only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Task Controller is required for **distributed workflows (V2 run_mode)**. Its primary role is to orchestrate the parallelization of analysis tasks. It operates by:

* Reading a **chunking configuration**, which can be defined either at a per-model level or customized for each individual analysis submission. This configuration determines how many discrete "chunks" or sub-tasks each parallelizable part of an execution should be broken into.
* Constructing a Celery **chord** – a Celery primitive that represents an overall workflow containing all interconnected sub-jobs an analysis needs to run. This ensures that dependent sub-tasks are executed in the correct sequence and that all parts of a parallel operation complete before the next stage begins.
* Creates individual analysis-task-statuses records in the API's database for each sub-task, accessible via /v2/analysis-task-statuses/{id}/. These sub-task statuses are linked back to the main analysis record through /v2/analyses/{id}/sub_task_list/, providing granular visibility into the progress of each workflow segment.
* Finally, placing these generated sub-tasks onto the appropriate model-specific Celery queue for execution by the Model Workers.

Core External software Components
---------------------------------

As mentioned above, the OASIS Platform is designed with a degree of flexibility regarding its underlying infrastructure, where possible, using open protocols and standards that allow for component swaps.

For instance, the default message broker, RabbitMQ, can theoretically be replaced by any alternative broker that fully supports the Advanced Message Queuing Protocol (AMQP). Similarly, Keycloak, our chosen identity provider, could be exchanged for another OpenID Connect (OIDC) compliant solution, and PostgreSQL, our relational database, could be substituted with any other database system compatible with both Django and Celery.

It is important to note, however, that while these alternatives may be technically feasible, implementing such swaps might need additional development effort, including potential code changes within the platform itself and the exposure of more granular configuration options and functionality.

The following components represent our current, proven, and well-performing choices, forming the 'reference' oasis stack.

**Django with Django REST Framework (DRF) for Web API:**

* **Django REST Framework (DRF)** extends Django to build powerful and flexible Web APIs. It simplifies the creation of RESTful endpoints by providing serializers, viewsets, and routers, significantly accelerating API development while ensuring adherence to REST principles. This combination is ideal for exposing application logic and data to various clients, such as front-end applications or other services.

**Django Channels for Autoscaler Communication:**

* **Django Channels** extends Django's capabilities beyond traditional HTTP, enabling it to handle WebSockets, chat protocols, IoT protocols, and more.
* **Redis** acts as the channel layer backend for Django Channels. It provides an in-memory data store that allows different Django Channels consumers and producers (even across multiple servers) to communicate and share state efficiently.
* In this stack, Django Channels is specifically utilized to establish a **WebSocket connection** for pushing the current state of the system to an autoscaler. This real-time data push allows the autoscaler to dynamically adjust resources based on live system metrics, ensuring optimal performance and cost efficiency.

**Celery with RabbitMQ as a Broker for Asynchronous Tasks:**

* **Celery** is a powerful distributed task queue system for Python. It allows the application to offload long-running, resource-intensive, or time-consuming tasks from the main request-response cycle, preventing timeouts and improving user experience. Examples include complex calculations, data processing, email sending, or report generation.
* **RabbitMQ** serves as the message broker for Celery. It acts as an intermediary, reliably queuing tasks sent by the Django application and distributing them to available Celery worker processes. This ensures tasks are processed even if the primary application is busy or restarted, providing robust message delivery guarantees.

**Keycloak as an Authentication Provider:**

* **Keycloak** is an open-source Identity and Access Management (IAM) solution. It provides robust features for user authentication, authorization, single sign-on (SSO), and identity brokering.
* Integrating Keycloak means the application offloads the complexities of user management and security to a dedicated, enterprise-grade system. This enhances security by centralizing identity management, supports various authentication protocols (like OpenID Connect), and simplifies user onboarding and access control.

**PostgreSQL as the Central Database:**

* **PostgreSQL** is a powerful, open-source, object-relational database system known for its strong reliability, feature robustness, and performance.
* In this stack, PostgreSQL acts as the **primary backing database for all major components**:

  * **Django**: Stores all application data managed by Django's ORM, including user data (if not fully managed by Keycloak), application configurations, and operational data.
  * **Keycloak**: Stores Keycloak's internal data, including user identities, roles, clients, and authentication sessions.
  * **Celery Results Backend**: Used by Celery to store the results and states of completed asynchronous tasks, allowing the application to query the status or retrieve the output of a task.

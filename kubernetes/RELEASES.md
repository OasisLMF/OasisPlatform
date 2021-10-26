# Release notes

## Sprint 1

Released on 2021-09-17

**Features included:**

* Helm charts to deploy, upgrade and manage services in Kubernetes.
* Helm chart for the platform. This includes:
    * Oasis server, agent, controller, worker monitor and UI.
    * Broker and databases (redis & postgres).
    * Keycloak (for new authentication and user management to be implemented later).
    * Prometheus (collects metrics).
    * Grafana (a complement to Prometheus for a better and easier way to visualize metrics and dashboards).
* Helm chart for models and workers.
* Helm chart for monitoring with Prometheus and Grafana.
    * Includes a custom Oasis dashboard in Grafana to monitor kubernetes nodes, pods and workers.
* Ingress.
* Deployment instructions.

**This covers the following in the functional summary:**

* Most of Kubernetes architecture (1.1) except for:
    * Ingress & API - ingress supported but split over two hostnames. Using one will require changes in either oasis ui
      or oasis server.
    * Health checks - basic checks in place, works very well but will be improved.
    * RabbitMQ / Mysql support - Current helm charts use redis / postgres.
* Model deployment (1.3)

## Sprint 2

Released on 2021-10-01

**Features included:**

* Autoscaler
    * New application located in kubernetes/worker_controller/.
    * Supports three scaling configurations:
        * Fixed number of workers.
        * Dynamic scaling based on the number of analyses currently running. One worker is started per analysis.
        * Dynamic scaling based on the sum of all submitted tasks per model.
* Platform chart improvements:
    * Autoscaler added.
    * Ingress controller supports custom tls certificate.
* Platform improvements:
    * Swagger fix to support https if access through the kubernetes ingress.
* Updated documentation.

**This covers the following in the functional summary:**

* Implement Autoscaling in kubernetes (1.2)

**Important notes:**

Ticket: https://github.com/OasisLMF/OasisPlatform/issues/542

Two issues were found with the websocket response and will impact testing before resolved. The autoscaler might shutdown
workers incorrectly before these are fixed, but I think this mostly affects parallel runs.

## Sprint 3

Released on 2021-10-15

**Features included:**

* Platform chart improvements:
  * Authentication setting: keycloak (default) or simple jwt
  * Default oasis keycloak realm setup on install (default accounts, settings etc.)
* Platform improvements:
  * Support Keycloak as authentication backend (extended mozilla_django_oidc).
  * Replicates Keycloak user/roles on the fly to Django user/groups.
  * Swagger keycloak support with instructions.
  * Auth endpoints works with Keycloak enabled for backward compatibility.
* Updated documentation.

**This covers the following in the functional summary:**

* Most of Improved security and user-management (1.4) except for:
  * Role isolation.

## Sprint 4

Released on 2021-10-27

**Features included:**

* Platform chart improvements:
  * The default user account gets group **admin**
  * A new service account is created also with group **admin**. This account is used by the model registration to update models.
* Platform improvements:
  * Groups in Keycloak are migrated to Django groups.
  * POST/PATCH/PUT endpoints for portfolios, models and data files now accepts a `groups` parameter
  * user without group
    * Support Keycloak as authentication backend (extended mozilla_django_oidc).
    * Replicates Keycloak user/roles on the fly to Django user/groups.
    * Swagger keycloak support with instructions.
    * Auth endpoints works with Keycloak enabled for backward compatibility.
* Updated documentation.

**This covers the following in the functional summary:**

* Second part of Improved security and user-management (1.4):
  * Group/role isolation.

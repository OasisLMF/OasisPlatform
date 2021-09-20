# Release notes

## Sprint 1

Released on 2021-09-17

Features included:

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

This covers the following in the functional summary:

* Most of Kubernetes architecture (1.1) except for:
    * Ingress & API - ingress supported but split over two hostnames. Using one will require changes in either oasis ui
      or oasis server.
    * Health checks - basic checks in place, works very well but will be improved.
    * RabbitMQ / Mysql support - Current helm charts use redis / postgres.
* Model deployment (1.3)

## Sprint 2

TODO

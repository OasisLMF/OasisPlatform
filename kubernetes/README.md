# Oasis on Kubernetes

This directory contains resources to deploy and manage the Oasis platform on a [Kubernetes](https://kubernetes.io)
cluster.

Read [charts/README.md](charts/README.md) for more details about how to deploy.

Read [RELEASES.md](RELEASES.md) for an overview of what has delivered.

# Analysis / job prioritization

A priority is set on each analysis either by the default value of 6 or by giving the `priority' attribute. Allowed
values are from 1-10:

| Priority | Comment                             |
|----------|-------------------------------------|
| 10       | The highest priority                |
| 8-10     | Can only be set by administrators   |
| 4        | Default if no priority is specified |
| 1        | The lowest priority                 |

When an analysis is started (input gen or run) tasks put on celery queues will get the same priority as the analysis
has.

Workers of the same model will consume tasks from the queue in the prioritized order.

When the worker controller detects runs with different priorities the default configuration is to create workers for the
2 models with the highest prioritized runs, to focus on finish those first. Let's say we have 4 analyses running:

| Analysis | Model | Priority |
|----------|-------|----------|
| A1       | 20    | 8        |
| A2       | 21    | 7        |
| A3       | 22    | 6        |
| A4       | 23    | 5        |

In this case the worker controller detects multiple runs with different prioritize (8, 7, 6, 5) and limits the number of
models to 2, which means only workers for A1 and A2 are created. This is controlled by
the `workerController.priority.modelsLimit` setting and can also be disabled completely.

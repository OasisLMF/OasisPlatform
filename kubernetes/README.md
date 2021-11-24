# Oasis on Kubernetes

This directory contains resources to deploy and manage the Oasis platform on a [Kubernetes](https://kubernetes.io)
cluster.

Read [charts/README.md](charts/README.md) for more details about how to deploy.

Read [RELEASES.md](RELEASES.md) for an overview of what has delivered.

# Analysis / job prioritization

A priority is set on each analysis either by the default value of 6 or by giving the `priority' attribute. Allowed
values are from 0-9:

| Priority | Comment
|----------|--------
| 0        | The highest priority
| 0-2      | Can only be set by administrators
| 6        | Default if no priority is specified
| 9        | The lowest priority

When an analysis is started (input gen or run) tasks put on celery queues will get the same priority as the analysis
has.

Workers of the same model will consume tasks from the queue in the prioritized order.

If the worker controller detects runs with different prioritize the default configuration is to focus the workers
created to at most 2 models. Let's say we have 4 analyses running:

| Analysis | Model | Priority |
|----------|-------|----------|
| A1       | 20    | 1        |
| A2       | 21    | 2        |
| A3       | 22    | 3        |
| A4       | 23    | 4        |

In this case the worker controller detects multiple runs with different prioritize (1, 2, 3, 4) and limits the number of
models to 2, which means only workers for A1 and A2 is created. This is controlled by
the `workerController.priority.modelsLimit` setting and can be disabled.

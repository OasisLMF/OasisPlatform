
Configuration for Distribution and Scaling
==========================================

.. _distributed_configuration:

:doc:`/explanation/overview` | :doc:`/explanation/platform_architecture` | :doc:`/how-to/container_configuration` | :doc:`/reference/rest_api` | :doc:`/how-to/distributed_execution` | :doc:`/how-to/distributed_configuration`

The efficiency of an distributed execution is dependent on its underlying scaling and chunking configurations. These settings are tuned per model to match specific workload characteristics, resource availability, and performance objectives.

Scaling Configuration
~~~~~~~~~~~~~~~~~~~~~

Each deployed Oasis model has its own independent scaling configuration, which is accessible and adjustable via the API at models/{id}/scaling_configuration/. When the WorkerController component initializes or receives updates, it reads these specific options for each active Oasis model deployment in the system.

Idle State and Minimum Worker Count (worker_count_min)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For all scaling strategies, the default idle state for a model's worker pool is **0 worker pods running**. This means that when a model's main Celery queue is empty (i.e., no tasks are waiting or in progress for that model), all associated worker instances will be shut down to conserve resources.

This default idle behavior can be overridden by setting worker_count_min = <integer>. When this parameter is specified, the system will ensure that at least that many worker pods are continuously provisioned and running, even when the queue is idle. This option is particularly useful for:

* **Debugging:** Maintaining a persistent worker for easier inspection.
* **High Responsiveness:** Eliminating the spin-up time typically required to provision and ready new virtual machines or containers when a task arrives, thus reducing latency for the first task.

Default Scaling Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If no explicit scaling configuration is provided for a model, the system defaults to the following settings:

.. code-block:: text

    scaling_strategy = FIXED_WORKERS
    worker_count_fixed = 1
    worker_count_min = 0

Scaling Strategies (scaling_strategy)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are three distinct modes of scaling operation, controlled by the scaling_strategy key, theses are FIXED_WORKERS, QUEUE_LOAD and DYNAMIC_TASKS.

A design principle for scaling configuration is that only the control values directly connected to the selected scaling_strategy have an effect. Any parameters not relevant to the chosen strategy (e.g., chunks_per_worker when FIXED_WORKERS is selected) will be ignored and will not influence the number of workers started.

**FIXED_WORKERS (Strategy 1)**

**Description:** When one or more tasks (main analysis requests) are placed on a model's queue, the system will launch a fixed number of workers. This number is controlled by the integer value specified in worker_count_fixed. Once all pending sub-tasks for the analyses on that queue have completed, the worker deployment will revert to its idle state (or worker_count_min if set).

**Control Parameters:** Only worker_count_fixed is active and influences the number of workers.

**Ignored Parameters:** worker_count_max and chunks_per_worker have no effect when this strategy is selected.

**QUEUE_LOAD (Strategy 2)**

**Description:** This strategy scales the number of workers based on the number of *analysis execution requests* waiting on a model's queue. If 'm' distinct analysis requests are submitted, 'm' worker pods will be started to process them concurrently.

**Control Parameters:** The scaling will occur up to a defined upper limit, specified by worker_count_max.

**Key Distinction:** This strategy focuses on the number of concurrent top-level analysis requests, not the granular sub-tasks or chunks within each analysis.

**DYNAMIC_TASKS (Strategy 3)**

**Description:** This is the most granular scaling strategy, directly linking worker provisioning to the number of individual sub-tasks (chunks) waiting on the model queue. The number of workers launched is calculated by dividing the total sum of all pending sub-tasks across all queued analyses by the chunks_per_worker value. This aims to ensure optimal worker utilization by aligning workers with the actual parallel workload units.

**Formula:** Number of Workers = (Total Pending Sub-tasks / chunks_per_worker)

**Example:** If three loss analysis requests are submitted, and each is broken into 15 chunks, with chunks_per_worker set to 5, the calculation would be: (3 analyses * 15 chunks/analysis) / 5 chunks/worker = 45 / 5 = 9 workers.

**Control Parameters:** chunks_per_worker dictates the worker-to-chunk ratio, and worker_count_max still applies as a hard upper limit on the total number of workers that can be spun up.

Chunking Configuration
~~~~~~~~~~~~~~~~~~~~~~

The 'chunking' configuration defines how a single analysis (both 'lookup' and 'loss' stages) is broken down into parallel sub-tasks. This can be configured at two levels, allowing for both system-wide defaults and analysis-specific overrides:

1. **Model-Level Default:**

   * **Location:** models/{id}/chunking_configuration/
   * **Behavior:** Settings here become the default for all analyses associated with this specific Oasis model.

2. **Analysis Override:**

   * **Location:** analyses/{id}/chunking_configuration/
   * **Behavior:** An individual analysis can have its chunking independently set at this endpoint. These settings take precedence over the model-level defaults and apply only to that specific analysis.

Chunking Strategies (lookup_strategy and loss_strategy)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are two independent chunking strategies that can be applied separately, controlled by lookup_strategy and loss_strategy respectively. Each with two modes of either **FIXED_CHUNKS**, which creates <n> analyses chunks or DYNAMIC_CHUNKS which has some limited scaling options based on the input size.

**FIXED_CHUNKS (Strategy 1)**

**Description:** This strategy specifies a fixed, absolute number of chunks into which the respective stage of the analysis will be split, regardless of the input data size.

**Control Parameters:**

* fixed_lookup_chunks: (int) The fixed number of chunks for the lookup stage.
* Fixed_analysis_chunks: (int) The fixed number of chunks for the loss generation (analysis) stage.

**Example Configuration:**

.. code-block:: json

    {
      "lookup_strategy": "FIXED_CHUNKS",
      "fixed_lookup_chunks": 10,
      "loss_strategy": "FIXED_CHUNKS",
      "fixed_analysis_chunks": 20
    }

In this example, every analysis run will be broken into 10 lookup chunks and 20 event batches for losses generation.

**Ignored Parameters:** Any fields prefixed with dynamic\_ (e.g., dynamic_events_per_analysis) are ignored when this strategy is active.

**Minimum Chunking Rule:** A practical minimum chunking rule applies: if the calculated (or fixed) chunk size results in more chunks than there are actual discrete items to process (e.g., a 4-line location file requested to be split into 5 chunks), then only the actual number of available items will be used as chunks (e.g., 4 chunks for the 4 lines).

**DYNAMIC_CHUNKS (Strategy 2)**

**Description:** This strategy dynamically scales the number of sub-tasks based on the size of the input data for that particular analysis run. In theory this allows chunking by adapting to variable workload sizes. However in practice breaking up an analysis into chunks based on the event set / location file size alone dosn't yield the best performance (further work required here)

**Control Parameters:**

* dynamic_locations_per_lookup: For lookup (input generation), this defines the target number of locations to include in each lookup chunk. The total number of chunks will be (total_locations / dynamic_locations_per_lookup).
* dynamic_events_per_analysis: For loss generation, this defines the target number of events to include in each loss chunk. The total number of chunks will be (total_events_in_set / dynamic_events_per_analysis).

**Maximum Chunk Cap (dynamic_chunks_max):** This acts as an upper limit on the maximum number of chunks that can be created, preventing the generation of an excessively large number of small chunks if the per_unit value is very low or the input file is extremely large. For example, if a location file has 100,000 lines and dynamic_locations_per_lookup is set to 1, this *would* theoretically result in 100,000 chunks. However, if dynamic_chunks_max is set to 200, only 200 chunks will be generated, each containing 100,000 / 200 = 500 locations.

**Loss Generation Specifics:**

For dynamic chunking of loss generation, the selected event set from model_settings.json **MUST** include a number_of_events = <total-events-in-set> value. Without this, the system cannot calculate the total number of events for dynamic scaling, and calls to analyses/{id}/run/ will return a 400 Bad Request response.

**Example (PiWind):** If the PiWind model's event set p contains 1447 events, and dynamic_events_per_analysis is set to 100, then a total of 15 sub-tasks (ceil(1447 / 100) = 15) will be generated for loss calculation.

**Ignored Parameters:** Any fields prefixed with fixed\_ (e.g., fixed_lookup_chunks) are ignored when this strategy is active.

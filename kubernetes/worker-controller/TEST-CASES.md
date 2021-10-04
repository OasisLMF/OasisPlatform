Worker Controller testing
=========================

This is a list of test cases to check the auto-scaling functionally from (sprint 2).
The new component reads the scaling settings on a per-model basis from the Oasis API using two new endpoints:

* `/v1/models/{id}/scaling_configuration/`
```
{
  "scaling_strategy":   <enum>,   (FIXED_WORKERS, QUEUE_LOAD, DYNAMIC_TASKS)
  "worker_count_fixed": <pos-integer>,
  "worker_count_max":   <pos-integer>,
  "chunks_per_worker":  <pos-integer>
}
```


* `/v1/models/{id}/chunking_configuration/`
```
{
  "lookup_strategy":              <enum>,  (FIXED_CHUNKS, DYNAMIC_CHUNKS)
  "loss_strategy":                <enum>,  (FIXED_CHUNKS, DYNAMIC_CHUNKS)
  "dynamic_locations_per_lookup": <pos-integer>,
  "dynamic_events_per_analysis":  <pos-integer>,
  "fixed_analysis_chunks":        <pos-integer>,
  "fixed_lookup_chunks":          <pos-integer>
}
```


So when a test states <em>'Set a model to `"scaling_strategy": "FIXED_WORKERS"`'</em> that setting should be changed via the Oasis API and picked up on the fly by the auto-scaler.


# Test cases

## Fixed Scaling

> Set scaling strategy to `FIXED_WORKERS`

| Test No  | Description  |
|---|:---|
| 1 | Check if a single worker scales up/down to fixed size. |
| 2 | Check if multiple workers simultaneously scale to a fixed size. |
| 3 | Set `worker_count_max` and check that the value is not exceeded when scaling. |
| 4 | Simulate a crash of 2 workers mid-analysis and check that the workers replaced.  |


## Dynamic scaling

> Set the scaling strategy to `DYNAMIC_TASKS` and `chunks_per_worker` = `50`


| Test No  | Description  |
|---|:---|
| 5 | Add lookup chunk load to a model queue using multiple lookup tasks with high number of chunks. Check that (total chunks / 50) workers are created.  |
| 6 | Set `chunks_per_worker` = `20`,  Add loss chunk load and check that (total chunks / 20) workers are created. |
| 7 | Add mixed lookup/loss chunk load,  check that (total chunks / 20) workers are created. |
| 8 | set `worker_count_max` = `10`, repeat `Test 7`, check that the value is not exceeded. |


## Queue Load Scaling

> Set scaling strategy to `QUEUE_LOAD`

| Test No  | Description  |
|---|:---|
| 9 | Add load on the main celery queue, check that one worker is created for each Job submitted. |
| 10 | Create two models using `QUEUE_LOAD` scaling, load the celery queue with jobs for both models and repeat `Test 9`. |


## Multiple scaling strategies

> Create three models, each with a different value for `scaling_strategy`.

| Test No  | Description  |
|---|:---|
| 11  | Submit 3 tasks (one per model) and check that the expected numbers of workers are created for each model based on the strategy. |

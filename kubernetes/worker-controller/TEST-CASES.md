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

| Test No  | Inputs | Expected result | Description  |
|---|:---|:---|:---|
| 1 | <ul><li> Model `A` </li><li>1 analysis started</li></ul> | A `worker_count_fixed` number of workers are created and removed | Check if a single model scales workers up/down to fixed size. |
| 2 | <ul><li> Model `A` </li><li> Model `B` </li><li> 1 analysis per model started  </li></ul> | Each model has its `worker_count_fixed` used to create workers | Check if multiple models simultaneously scale to a fixed size. |
| 3 | <ul><li> Model `A` </li><li> 1 analysis started </li><li> set `worker_count_max` < `worker_count_fixed` </li></ul> | A `worker_count_max` number of workers are created | Set `worker_count_max` and check that the value is not exceeded when scaling. |
| 4 | <ul><li> Model `A` </li><li> 1 analysis started </li><li> `fixed_analysis_chunks`=`10` </li><li> `worker_count_fixed`=`2` </li></ul> | 2 new workers will replace the crashed containers | Simulate a crash of 2 workers mid-analysis and check that the workers replaced.  |


## Dynamic scaling

> Set the scaling strategy to `DYNAMIC_TASKS` and `chunks_per_worker` = `50`


| Test No  | Inputs | Expected result | Description  |
|---|:---|:---|:---|
| 5 | <ul><li> Model `A` </li><li> `chunks_per_worker`=`50` </li><li> 3 input generation started </li><li> `fixed_lookup_chunks`=`50` </li></ul>| 3 workers are created | Add lookup chunk load to a model queue using multiple lookup tasks with high number of chunks. Check that (total chunks / 50) workers are created.  |
| 6 | <ul><li> Model `A` </li><li> `chunks_per_worker`=`20` </li><li> 3 analysis started input </li><li> `fixed_analysis_chunks`=`40` </li></ul> | 6 workers are created | Set `chunks_per_worker`=`20`,  Add loss genretion chunks and check that (total chunks / 20) workers are created. |
| 7 | <ul><li> Model `A` </li><li> `chunks_per_worker`=`20` </li><li> 1 input generation started </li><li> 2 analysis started  </li><li> `fixed_lookup_chunks`=`40` </li><li> `fixed_analysis_chunks`=`1000`</li></ul> | 102 workers are created | Add mixed lookup/loss chunk load,  check that (total chunks / 20) workers are created. |
| 8 | <ul><li> Model `A` </li><li> `worker_count_max`=`10`  </li><li> `chunks_per_worker`=`20`  </li><li> 1 input generation started </li><li> 2 analysis started  </li><li> `fixed_lookup_chunks`=`40` </li><li> `fixed_analysis_chunks`=`1000`</li></ul>| 10 workers are created | set `worker_count_max`=`10`, repeat `Test 7`, check that the value is not exceeded. |


## Queue Load Scaling

> Set scaling strategy to `QUEUE_LOAD`

| Test No  | Inputs | Expected result | Description  |
|---|:---|:---|:---|
| 9 | <ul><li> Model `A` </li><li> 5 analysis started </li></ul> | 5 workers are created | Add load on the main celery queue, check that one worker is created for each Job submitted. |
| 10 | <ul><li> Model `A` </li><li> Model `B` </li><li> 2 analysis started (Model A) </li><li>  3 analysis started (Model B) </li></ul> | A total of 5 workers are added, 2 for Model `A` and 3 for Model `B` | Create two models using `QUEUE_LOAD` scaling, load the celery queue with jobs for both models and repeat `Test 9`. |


## Multiple scaling strategies

> Create three models, each with a different value for `scaling_strategy`.

| Test No  | Inputs | Expected result | Description  |
|---|:---|:---|:---|
| 11  | <ul><li> Model `A` </li><li> `scaling_strategy`=`FIXED_WORKERS` </li><li> `worker_count_fixed`=`1` </li><li> 1 analysis started  </li></ul> <ul><li> Model `B` </li><li> `scaling_strategy`=`DYNAMIC_TASKS` </li><li> `chunks_per_worker`=`10` `fixed_lookup_chunks`=`50` </li><li>  1 analysis started  </li></ul> <ul><li> Model `C` </li><li> `scaling_strategy`=`QUEUE_LOAD` </li><li> 2 Input generaion started  </li></ul>| <ul><li> Model `A` = 1 worker </li><li> Model `B` = 5 workers </li><li> Model `C` = 2 workers  </li></ul> | Submit multiple tasks (at least one per model) and check that the expected numbers of workers are created for each model based on the strategy. |

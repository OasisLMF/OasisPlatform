OasisPlatform Changelog
=======================


`1.12.0`_
---------
.. start_latest_release
* [#422](https://github.com/OasisLMF/OasisPlatform/issues/422) - Add S3 Integration tests to the platform
* [#419](https://github.com/OasisLMF/OasisPlatform/issues/419) - Give the API user the possibilty to manage files outside of oasis
* [#424](https://github.com/OasisLMF/OasisPlatform/issues/424) - Fixed default value for DISABLE_WORKER_REG
* [#400](https://github.com/OasisLMF/OasisPlatform/issues/400) - Extend model_settings.json with optional metadata from Nasdaq
* [#423](https://github.com/OasisLMF/OasisPlatform/issues/423) - Revert feature #377 - always Read aws_location from confing dont store with file object
* [#409](https://github.com/OasisLMF/OasisPlatform/issues/409) -  Differentiate model run time parameters between generation and losses steps in model_settings.json
.. end_latest_release


`1.11.1`_
---------
* Update oasislmf package to 1.11.1


`1.11.0`_
---------
* [#377](https://github.com/OasisLMF/OasisPlatform/issues/377) - Changing S3 variable 'aws_location' invalidates stored files
* [#417](https://github.com/OasisLMF/OasisPlatform/issues/417) - Store analysis S3 objects as `analysis_<id>_<filename>`
* [#407](https://github.com/OasisLMF/OasisPlatform/issues/407) - Store analysis_settings.json in output.tar
* [#404](https://github.com/OasisLMF/OasisPlatform/issues/404) - Cleanup dangling files using delete handlers
* [#403](https://github.com/OasisLMF/OasisPlatform/issues/403) - Task timestamps - not updating on rerun
* Fixed S3 example compose

`1.10.2`_
---------
* Update oasislmf package to 1.10.2

`1.10.1`_
---------
* Fix issue with supplier model runner
* [#401](https://github.com/OasisLMF/OasisPlatform/issues/401) - Fix CASCADE deletes on analyses copy
* [#398](https://github.com/OasisLMF/OasisPlatform/issues/398) - Added option to disable worker auto-registration
* [PR 406](https://github.com/OasisLMF/OasisPlatform/pull/406) - Clean up for worker configuration

`1.10.0`_
---------
* Skipped due to oasislmf hotfix 1.10.1

`1.9.1`_
--------
* Update oasislmf package to 1.9.1

`1.9.0`_
--------
* [#391](https://github.com/OasisLMF/OasisPlatform/issues/391) - Store `keys-errors.csv` in API on Generate Inputs error
* [#375](https://github.com/OasisLMF/OasisPlatform/issues/375) - Add check for non-null location_file to analyses serializer
* [#394](https://github.com/OasisLMF/OasisPlatform/issues/394) - Pass model_settings.json to generate-oasis-files
* [#381](https://github.com/OasisLMF/OasisPlatform/issues/381) - Worker Monitor - Not updating DB on failure
* [#385](https://github.com/OasisLMF/OasisPlatform/issues/385) - Jenkins, improve model regression testing
* [PR 396](https://github.com/OasisLMF/OasisPlatform/pull/396) - Added Django security patches (3.0.7)

`1.8.3`_
--------
* Update MDK to 1.8.3

`1.8.2`_
---------
* Update MDK to 1.8.2

`1.8.1`_
---------
* [#380](https://github.com/OasisLMF/OasisPlatform/issues/380) -  Use partial update of FileFields to prevent overwrite

`1.8.0`_
---------
* [#353](https://github.com/OasisLMF/OasisPlatform/issues/353) - Add Slack notification for software releases
* [#369](https://github.com/OasisLMF/OasisPlatform/issues/369) - Add Known issues to release notes
* [#370](https://github.com/OasisLMF/OasisPlatform/issues/370) - Fix for unsigned URLS in S3 Storage manager
* [#372](https://github.com/OasisLMF/OasisPlatform/issues/372) - Exposure summary produces incorrect 'overview' TIV
* [#374](https://github.com/OasisLMF/OasisPlatform/issues/374) - Schema fix analysis_settings.json

`1.7.1`_
--------
* #359 - Fix, Model data files not available in worker

`1.7.0`_
--------
* #342 - automate milestone creation
* #346 - Fix schema for server_info endpoint
* #339 - Add collapseable option to parameter grouping
* #345 - sets of configuration parameters

`1.6.1`_
--------
* #343 - Avoid task failure for missing non-essential files on inputs generation

`1.6.0`_
--------
* #321 - Updated Django to 3.0.3
* #325 - Fixed Migration issue from version 1.1.2
* #323 - Added 'server_info' endpoint for details on the running API
* #317 - Added Backwards compatibility tests to CI
* #313 - Added option to set run dir location in worker
* #284 - Added support for S3 Object stores
* #311 - Improved error logging in worker monitor
* #306 - Fixed logical deletion for AnalysisModels
* #335 - Accept compressed CSV files as portfolio uploads
* Added `tooltip` to model_settings schema

`1.5.1`_
--------
* #309 - worker: Missing error logs from input generation
* #307 - worker: Show subprocess output in worker logs

`1.5.0`_
--------

* #304 - Slim image builds (Currently optional)
* #303 - model settings schema Update
* #302 - Add Maven Swagger API build test
* #297 - Remove previous output results on run error
* #297 - Fix Log and traceback storage
* #222 - Update to  model settings schema
* #275 - Fixed delete operations with multipart as content type in swagger
* #274 - Fixed reverting behaviour for complex models (custom gulcalc)
* #281 - Added Task Queued state
* #268 - Store run trace on success
* #287 - Store ktools log directory in an Analyses
* #283 - Fixed Worker not releasing memory from Python process

`1.4.1`_
--------
* Fixes #280 - JSON file schemas compatibility with swagger
* Added models/{id}/versions endpoint
* Improved worker environment variables logging and defaults

`1.4.0`_
--------
* Added `/v1/models/{id}/settings` to replace `/v1/models/{id}/resource_file/`
* Added `/v1/analyses/{id}/settings` to replace `/v1/analyses/{id}/settings_file/`
* New worker environment variable `MODEL_SETTINGS_FILE` if set workers auto-update model settings on connection
* Removed environment variable `WRITE_EXPOSURE_SUMMARY` in favour of `DISABLE_EXPOSURE_SUMMARY`
* Workers log internal versions to the API and docker logs
* Schemas updated for `analysis_settings` and `model_settings`

`1.3.5`_
--------
* Automate GitHub release
* Hotfix, Add option to disable ktools error monitor in worker

`1.3.4`_
--------
* Fix for coverage reports
* Fix for groovy script
* Fixes for temporary directory manager
* Update integration test script
* Update worker for RI alloc rule

`1.3.3`_
--------
* Fix for Cascade delete of traceback files
* Fix slow multiprocess lookup with newer billiard lib

`1.3.2`_
--------
* Update Django and django-rest-framework to latest versions
* Added option to rotate refresh token
* Fix to remove old error logs once analysis completes successfully
* Update worker for MDK 1.4.2

`1.3.1`_
--------
* Hotfix - fix for scope file null check

`1.3.0`_
--------
* oasislmf updated to [1.4.1](https://github.com/OasisLMF/OasisLMF/releases/tag/1.4.1)
* ktooks updated to [3.1.1](https://github.com/OasisLMF/ktools/releases/tag/v3.1.1)
* Update ENV for worker `KTOOLS_ALLOC_RULE` -> `KTOOLS_ALLOC_RULE_IL`
* New ENV for worker `KTOOLS_ALLOC_RULE_GUL`
* Fixes for OpenAPI / Swagger schema

`1.2.1`_
--------
* Fix for Complex_model DataFiles
* remove some dependencies in model_worker
* Update to api testing script

`1.2.0`_
--------
* Renamed `portfolios/{id}/reinsurance_source_file` to `portfolios/{id}/reinsurance_scope_file`
* Fix for Automatic file generation on creation of analysis from `/v1/portfolios/{id}/create_analysis/`
* Added JWT key option to settings conf
* exposure-summary files added as file endpoints to analyses `/v1/analyses/{id}/lookup_validation_file/`, `lookup_success_file/` and `lookup_errors_file/`
* Generic `data_files` refactored and added to API
* `/oed_peril_codes/` added for UI reference
* Removed `base` dockerfile
* `/v1/analyses/{id}/summary_levels_file/` added to analyses
* Default worker mount point changed from `/var/oasis/model_data` to `/var/oasis`
* Oasislmf updated to 1.4.0

`1.1.2`_
--------
* Hotfix - Set Oasislmf to 1.3.10

`1.1.1`_
--------
 * Update Oasislmf to 1.3.9
 * Update API test script

`1.1.0`_
--------
 * New endpoint `complex_data_files`
 * OasisLMF update to `1.3.8`
 * Ktools update to `v3.0.8`
 * Added environment variable `DEBUG_MODE` to worker for verbose logging

`1.0.2`_
--------
* Fix file large file upload error
* Add Env option to keep worker run directory
* Update python requirements
* Fix for unittests
* Update Oasislmf to 1.3.6

`1.0.1`_
--------
* Oasislmf package [1.3.2](https://github.com/OasisLMF/OasisLMF/tree/1.3.2)

`1.0.0`_
--------
* Oasislmf package [1.3.1](https://github.com/OasisLMF/OasisLMF/tree/1.3.1)
* Initial release of New API based on Django REST Framework
* Worker image updated to handle oasis files generation
* For full notes see `Release notes 1.0.0 <https://github.com/OasisLMF/OasisPlatform/blob/develop/RELEASE.md#100-732019>`_

`0.397.3`_
----------
* Add Envrioment Variable to set Ktools Allocation rule in worker `KTOOLS_ALLOC_RULE`
* Update to Automated testing script

`0.397.2`_
----------
* oasislmf package 1.2.3

`0.397.1`_
----------
* oasislmf package 1.2.2

`0.397.0`_
----------
* oasislmf package 1.2.1
* Fix for Retry Lock file issue
* Switch Environment variables prefix to `OASIS_<VAR_NAME>` from  `OASIS_API_<VAR_NAME>`

`0.396.2`_
----------
* oasislmf package 1.2.1


`0.396.1`_
----------
* oasislmf package 1.2.1
* No Change in Base images


`0.396.0`_
----------
* oasislmf package 1.2.1
* Added Dockerfile to build oasis_base via git install of oasislmf
* Added Environment Variable for Ktools memory limit `KTOOLS_MEMORY_LIMIT`

`0.395.3`_
----------
* oasislmf package 1.2.1


`0.395.2`_
----------
* oasislmf package 1.1.26
* Add LICENSE file

`0.395.1`_
----------
* oasislmf package 1.1.26


`0.395.0`_
----------
* oasislmf package 1.1.26
* Added Reinsurance support + test RI files

`0.394.1`_
----------
* oasislmf package 1.1.25

.. _`1.12.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.11.1...1.12.0
.. _`1.11.1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.11.0...1.11.1
.. _`1.11.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.10.2...1.11.0
.. _`1.10.2`:  https://github.com/OasisLMF/OasisPlatform/compare/1.10.1...1.10.2
.. _`1.10.1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.9.1...1.10.1
.. _`1.9.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.8.3...1.9.0
.. _`1.8.3`:  https://github.com/OasisLMF/OasisPlatform/compare/1.8.2...1.8.3
.. _`1.8.2`:  https://github.com/OasisLMF/OasisPlatform/compare/1.8.1...1.8.2
.. _`1.8.1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.8.0...1.8.1
.. _`1.8.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.7.1...1.8.0
.. _`1.7.1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.7.0...1.7.1
.. _`1.7.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.6.1...1.7.0
.. _`1.6.1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.6.0...1.6.1
.. _`1.6.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.5.1...1.6.0
.. _`1.5.1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.5.0...1.5.1
.. _`1.5.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.4.1...1.5.0
.. _`1.4.1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.4.0...1.4.1
.. _`1.4.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.3.5...1.4.0
.. _`1.3.5`:  https://github.com/OasisLMF/OasisPlatform/compare/1.3.4...1.3.5
.. _`1.3.4`:  https://github.com/OasisLMF/OasisPlatform/compare/1.3.3...1.3.4
.. _`1.3.3`:  https://github.com/OasisLMF/OasisPlatform/compare/1.3.2...1.3.3
.. _`1.3.2`:  https://github.com/OasisLMF/OasisPlatform/compare/1.3.1...1.3.2
.. _`1.3.1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.3.0...1.3.1
.. _`1.3.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.2.1...1.3.0
.. _`1.2.1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.2.0...1.2.1
.. _`1.2.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.1.2...1.2.0
.. _`1.1.2`:  https://github.com/OasisLMF/OasisPlatform/compare/1.1.1...1.1.2
.. _`1.1.1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.1.0...1.1.1
.. _`1.1.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.0.2...1.1.0
.. _`1.0.2`:  https://github.com/OasisLMF/OasisPlatform/compare/1.0.1...1.0.2
.. _`1.0.1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.0.0...1.0.1
.. _`1.0.0`:  https://github.com/OasisLMF/OasisPlatform/compare/0.397.3...1.0.0
.. _`0.397.3`:  https://github.com/OasisLMF/OasisPlatform/compare/0.397.2...0.397.3
.. _`0.397.2`:  https://github.com/OasisLMF/OasisPlatform/compare/0.397.1...0.397.2
.. _`0.397.1`:  https://github.com/OasisLMF/OasisPlatform/compare/0.397.0...0.397.1
.. _`0.397.0`:  https://github.com/OasisLMF/OasisPlatform/compare/0.396.2...0.397.0
.. _`0.396.2`:  https://github.com/OasisLMF/OasisPlatform/compare/0.396.1...0.396.2
.. _`0.396.1`:  https://github.com/OasisLMF/OasisPlatform/compare/0.396.0...0.396.1
.. _`0.396.0`:  https://github.com/OasisLMF/OasisPlatform/compare/0.395.3...0.396.0
.. _`0.395.3`:  https://github.com/OasisLMF/OasisPlatform/compare/0.395.2...0.395.3
.. _`0.395.2`:  https://github.com/OasisLMF/OasisPlatform/compare/0.395.1...0.395.2
.. _`0.395.1`:  https://github.com/OasisLMF/OasisPlatform/compare/0.395.0...0.395.1
.. _`0.395.0`:  https://github.com/OasisLMF/OasisPlatform/compare/0.394.1...0.395.0
.. _`0.394.1`:  https://github.com/OasisLMF/OasisPlatform/compare/OASIS_0_0_389_0...0.394.1

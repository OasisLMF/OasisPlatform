<!--- AUTO_INSERT-RELEASE --->
# 1.0.2 (05/04/2019)
 * Ktools [3.0.6](https://github.com/OasisLMF/ktools/tree/v3.0.6)
 * Oasislmf [1.3.6](https://github.com/OasisLMF/OasisLMF/tree/1.3.6)
 
 ## Features and Improvements
 * Oasis input generation performance update 
# 1.0.1 (8/3/2019)
* Ktools [3.0.5](https://github.com/OasisLMF/ktools/tree/v3.0.5)
* Oasislmf [1.3.2](https://github.com/OasisLMF/OasisLMF/tree/1.3.2)


## Features and Improvements
* Added support for running complex models (see [ComplexModelMDK](https://github.com/OasisLMF/ComplexModelMDK/blob/master/install.sh))
* Updated Oasislmf package to 1.3.2 (Bug fixes)

# 1.0.0 (7/3/2019)
* Ktools [3.0.5](https://github.com/OasisLMF/ktools/tree/v3.0.5)
* Oasislmf [1.3.1](https://github.com/OasisLMF/OasisLMF/tree/1.3.1)

## Features and Improvements
* Architecture overhaul 
    - All system components containerized 
    - Docker images moved to use python3.6 (Debian based) 
    - Ktools files generation moved into Worker  
    - Model Keys lookups moved into worker container 
    - API moved to Django REST Framework 

* Oasis UI
    - Updated Interface 
    - Logic moved into API and workflow improvments 
    - Port binding now dynamic, no need to edit the docker deamon  

* Model Development kit
    - Parity between model runs on the MDK (Model Dev Kit) and the worker execution 
    - Reinsurance support on commandline   

## Docker image changes 
* API images
    - Renamed `coreoasis/model_execution_worker` -> `coreoasis/model_worker`
    - Renamed `coreoasis/oasis_api_server` -> `coreoasis/api_server`  
    - Deprecated `coreoasis/oasis_base`  
    - Deprecated `coreoasis/custom_keys_server`  
    - Deprecated `coreoasis/builtin_keys_server`  
    - Deprecated `coreoasis/<MODEL>_keys_server`  

* UI images
    - Renamed `coreoasis/shiny_proxy` -> `coreoasis/oasisui_proxy`  
    - Renamed `coreoasis/flamingo_shiny` -> `coreoasis/oasisui_app` 
    - Deprecated `coreoasis/flamingo_server`  

    

## Deprecations & Breaking Changes
* Removed CSV file transformations
* Windows based SQL file generation
* All Docker based keys_servers removed, lookups are now performed in the `model_worker`

## API Changes
* User based authentication
* Added Django admin panel for user management & edits to backing database 
* Added Swagger UI for testing the API
* Improved workflow 
* Easer installation (see [OasisEvaluation](https://github.com/OasisLMF/OasisEvaluation))
* Added the ability to cancel an analysis or Input generation from the API
* Workers automatically register with the API `models/` end point 




# 0.397.3 (30/1/2019)

## [Ktools](https://github.com/OasisLMF/ktools/tree/v3.0.4)
* Ktools *3.0.4* packaged in `0.397.3` docker images 

### Fixes
* Performance improvement for fmcalc


## [OasisLMF](https://github.com/OasisLMF/OasisLMF/tree/1.2.2)
* oasislmf *1.2.5* packaged in `0.397.3` docker images 

### Fixes and Changes
* Fix for Windows 10 (Linux Sub-system), FIFO queues moved into `/tmp/<random>`
* Fix for Reinsurance, Set RiskLevel = `SEL` as default when value is not set
* Fix, calc rule for all positive deductibles
* Fixes for new API Client 
* Added Deterministic loss generation
* Added FM acceptance tests
* Added Automated testing 



## [OasisPlatform](https://github.com/OasisLMF/OasisPlatform/tree/0.397.3)
 
### Deployment Updates
* New enviroment var to set fmcalc allocation rule,  `OASIS_KTOOLS_ALLOC_RULE` 



# 0.397.1

## [oasis ui](https://github.com/oasislmf/oasisui/tree/0.397.1)
### bug fixes and other changes
* Fix for Reinsurance


# 0.397.0

## [Ktools](https://github.com/OasisLMF/ktools/tree/v3.0.3)
* Ktools *3.0.3* packaged in `0.397.0` docker images 

### Bug Fixes and Other Changes
* Performance optimization for Alloc rule 2 
* Fix for aalcalc, standard deviation when an event has multiple periods 
* Fix aalcalc weighting
* Added `summarycalctobin` and removed `fptofmcache`
* Improved error handling 
* Event shuffling to distribute workload been CPU cores. 


### Deprecations
* cygwin no longer supported, `./winconfigure`, to run ktools on windows use `MSYS2`.
* For Documentation see [Windows installation](https://github.com/OasisLMF/ktools#windows-installation)

## [OasisLMF](https://github.com/OasisLMF/OasisLMF/tree/1.2.2)
* oasislmf *1.2.2* packaged in `0.397.0` docker images 

### Features and Improvements
* Added API client for OED API update 
* New MDK commands to Invoke updated API client `oasislmf api [run, list, delete, add-model]`
* Improved FM file generation testing

### Reinsurance changes 
* Fixes to scope filters to correctly handle account, policy and location combinations.
* Added portfolio and location group scope filters.
* Fixes to required fields and default values to match OED

### Bug Fixes and Other Changes
* Fixed binary file writing bug, corrupted tar output files

## [OasisPlatform](https://github.com/OasisLMF/OasisPlatform/tree/0.397.0)
 
### Deployment Updates
* Always use `OASIS_<VAR_NAME>` prefix for env variable. This replaces `OASIS_API_<VAR_NAME>` 
* Fix for retry timeouts.

## [oasis ui](https://github.com/oasislmf/oasisui/tree/0.397.0)
### bug fixes and other changes
* docker files moved from `<root_dir>/build` to `<root_dir>/docker`
* dynamic port binding option added for rshiny-proxy 
* fix for policy level outputs


# 0.396.0

## Sub-Package versions
* Ktools updated to `v3.0.2`
* Python OasisLMF PyPi package updated to `v1.2.1`

## Major Features and Improvements
    * Ktools
        - Improved error handling 
        - Compatibility fix for OSX                                                                                                     

    * OasisLMF
        - Financial Module (FM) / Insurance loss (IL) support in the Model development kit (MDK)
        - Fixes for OED reinsurance for SS and Fac application scope
        - Various optimisations & fixes


# 0.395.0

## Sub-Package versions
* Ktools update to `v3.0.0`
* Python OasisLMF PyPi package update to `v1.1.26`

## Major Features and Improvements
  * Reinsurance Phase 1 Completed - added support for
      * Reinsurance contract types
          - Facultative at location or policy, proportional or excess of loss
          - Quota share with event limit
          - Surplus share with event limit
          - Per risk excess of loss
          - Catastrophe excess of loss, per occurrence only
      * Loss perspectives
          - Net loss pre-cat
          - Reinsurance loss
      * Outputs
          - ELTs, Loss Exceedance Curves, PLTs, AAL
          - All summary levels as per gross perspective (e.g. Portfolio, State, County, Location)
          - Support for multiple inuring priorities and complex hierarchies


  * Support added for Open Exposure Data v1.0 (OED) input format -- Only for Reinsurance
  * New type of keys_server type `coreoasis/builtin_keys_server` - A built-in generic lookup that combines a peril lookup which uses Rtree spatial indexes and a vulnerability lookup which uses a simple key-value approach using dictionaries.

# 0.397.4

## [OasisLMF](https://github.com/OasisLMF/OasisLMF/tree/1.2.7)
* oasislmf *1.2.7* packaged in `0.397.4` docker images 


### Fixes and Changes
* Fix for Ktools Memory limits in Genbash
* Fix in Generate-Losses command

## [OasisPlatform](https://github.com/OasisLMF/OasisPlatform/tree/0.397.4)
### Fixes and Changes
* Fix for lockfile max retries


## No Change from 0.397.3
* Ktools 3.0.4


# 0.397.3

## [Ktools](https://github.com/OasisLMF/ktools/tree/v3.0.4)
* Ktools *3.0.4* packaged in `0.397.3` docker images 

### Fixes
* Performance improvement for fmcalc


## [OasisLMF](https://github.com/OasisLMF/OasisLMF/tree/1.2.5)
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


# 0.397.2

## [OasisLMF](https://github.com/OasisLMF/OasisLMF/tree/1.2.3)
* oasislmf *1.2.3* packaged in `0.397.2` docker images 
### Fixes and Changes
* Hotfix for Reinsurance required fields


## No Change from 0.397.1
* Ktools 3.0.3
* OasisPlatform 


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


<!--- Template
# Release <RELEASE_TAG>

[![Ktools_version](https://img.shields.io/badge/Ktools-v3.0.0-lightgrey.svg)](https://github.com/OasisLMF/ktools/tree/v3.0.0)
[![PyPI version](https://img.shields.io/badge/PyPi%20--%20OasisLMF-1.1.26-brightgreen.svg)](https://github.com/OasisLMF/OasisLMF/tree/v1.1.26)

## Major Features and Improvements

## Breaking Changes

## Bug Fixes and Other Changes

## Deprecations

## API Changes

## Known Bugs

--->

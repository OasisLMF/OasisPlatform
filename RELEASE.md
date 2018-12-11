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

## [Oasis UI](https://github.com/OasisLMF/OasisUI/tree/0.397.0)
### Bug Fixes and Other Changes
* Docker files moved from `<root_dir>/build` to `<root_dir>/docker`
* Dynamic port binding option added for RShiny-Proxy 
* Fix for policy level outputs


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

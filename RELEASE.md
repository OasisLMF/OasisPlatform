# Release v0.395.0

[![Ktools_version](https://img.shields.io/badge/Ktools-v3.0.0-lightgrey.svg)](https://github.com/OasisLMF/ktools/tree/v3.0.0)
[![PyPI version](https://img.shields.io/badge/PyPi%20--%20OasisLMF-1.1.26-brightgreen.svg)](https://github.com/OasisLMF/OasisLMF/tree/v1.1.26)

## Sub-Package versions
* Ktools update to v3.0.0
* Python OasisLMF PyPi package update to v1.1.26

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

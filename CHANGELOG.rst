OasisPlatform Changelog
=======================

.. _`2.3.16`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.15...2.3.16

`2.3.15`_
 ---------
* [#1193](https://github.com/OasisLMF/OasisPlatform/pull/1193) - Update base deb image to p3.12
* [#781](https://github.com/OasisLMF/OasisPlatform/pull/1194) - Add kubernetes CI/CD testing
.. _`2.3.15`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.14...2.3.15

.. _`2.3.14`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.13...2.3.14

`2.3.13`_
 ---------
* [#1149, #1150](https://github.com/OasisLMF/OasisPlatform/pull/1164) - Fixed missing stack trace logging for V1 workers 
* [#1158](https://github.com/OasisLMF/OasisPlatform/pull/1158) - Worker controller detects pending V1 task and tries to scale V2 workers 
.. _`2.3.13`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.12...2.3.13

* [#1063](https://github.com/OasisLMF/OasisPlatform/pull/1152) - Expose components versions in API
.. _`2.3.12`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.11...2.3.12

`2.3.11`_
 ---------
* [#1125](https://github.com/OasisLMF/OasisPlatform/pull/1133) - Support Cyber models on OasisPlatform
* [#1134](https://github.com/OasisLMF/OasisPlatform/pull/1134) - Fixed pip install on model worker images 
* [#1139](https://github.com/OasisLMF/OasisPlatform/pull/1139) - Fix/1135 model settings conf
* [#1129](https://github.com/OasisLMF/OasisPlatform/pull/1143) - Platform schema generation - minor changes between versions.
* [#1140](https://github.com/OasisLMF/OasisPlatform/pull/1145) - Add DB indexing to fields like Analyses status. 
* [#1147](https://github.com/OasisLMF/OasisPlatform/pull/1147) - Release notes script - skip merge commits
.. _`2.3.11`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.10...2.3.11

`2.3.10`_
 ---------
* [#1121](https://github.com/OasisLMF/OasisPlatform/pull/1121) - Release 2.3.9
* [#1122](https://github.com/OasisLMF/OasisPlatform/pull/1122) - Update python packages for  2.3.9
* [#1124](https://github.com/OasisLMF/OasisPlatform/pull/1124) - Update docker base images and python packages 
* [#1123](https://github.com/OasisLMF/OasisPlatform/pull/1130) - Generate oasis files is not using the pre-analysis adjusted location file for V2 runs
* [#1125](https://github.com/OasisLMF/OasisPlatform/pull/1133) - Support Cyber models on OasisPlatform
.. _`2.3.10`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.9...2.3.10

`2.3.9`_
 ---------
* [#1105](https://github.com/OasisLMF/OasisPlatform/pull/1105) - Release 2.3.8
* [#1122](https://github.com/OasisLMF/OasisPlatform/pull/1122) - Update python packages for  2.3.9
.. _`2.3.9`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.8...2.3.9

`2.3.8`_
 ---------
* [#1098](https://github.com/OasisLMF/OasisPlatform/pull/1099) - API is down. Please try again later 
* [#1075](https://github.com/OasisLMF/OasisPlatform/pull/1103) - Logging - V2 input generation and losses tar should include log files for all sub-tasks 
* [#1104](https://github.com/OasisLMF/OasisPlatform/pull/1104) - Fix params for V1 workers - so custom hooks are called
* [#1107](https://github.com/OasisLMF/OasisPlatform/pull/1107) - Fix/gen log storage
* [#1109](https://github.com/OasisLMF/OasisPlatform/pull/1109) - set artifact to v4
* [#1079](https://github.com/OasisLMF/OasisPlatform/pull/1079) - Release 2.3.7 (Aug 6) 
* [#1111](https://github.com/OasisLMF/OasisPlatform/pull/1112) - Keycloak OIDC group permistions is broken. 
* [#1110](https://github.com/OasisLMF/OasisPlatform/pull/1113) - Add Endpoint for models - 'storage_links'
.. _`2.3.8`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.7...2.3.8

`2.3.7`_
 ---------
* [#1090](https://github.com/OasisLMF/OasisPlatform/pull/1090) -  Fixed CVEs from fiona package (backport)
* [#1091](https://github.com/OasisLMF/OasisPlatform/pull/1091) - Fixed build error from worker-controller image
* [#1057, #1092](https://github.com/OasisLMF/OasisPlatform/pull/1093) - Fix/1092 task cancellation issue
* [#1095](https://github.com/OasisLMF/OasisPlatform/pull/1095) - Updated Package Requirements: twisted==24.7.0rc1
* [#1065](https://github.com/OasisLMF/OasisPlatform/pull/1065) - Release 2.3.6 (July 1st 2024)
* [#1077](https://github.com/OasisLMF/OasisPlatform/pull/1077) - FIx missing exception trace in V1 workers 
* [#1076](https://github.com/OasisLMF/OasisPlatform/pull/1078) - Fix return of types of create 'analyses' and 'model' POST in API spec. 
* [#1081](https://github.com/OasisLMF/OasisPlatform/pull/1081) - Fix/api responses v2
* [#1085](https://github.com/OasisLMF/OasisPlatform/pull/1086) - Validation errors when posting a run incorrectly update an anaysis state to RUN_ERROR  
* [#1071](https://github.com/OasisLMF/OasisPlatform/pull/1087) - Add new custom code hooks into the V2 workflow 
.. _`2.3.7`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.6...2.3.7

`2.3.6`_
 ---------
* [#1062](https://github.com/OasisLMF/OasisPlatform/pull/1062) - Fix autoscaling ramping down when new analysis run is triggered  
* [#1066](https://github.com/OasisLMF/OasisPlatform/pull/1066) - Fix keycloak when running with Postgres Flexible server
* [#1056](https://github.com/OasisLMF/OasisPlatform/pull/1067) - Passing analysis/model settings as a(n optional) parameter when creating a new analysis or model
* [#1068](https://github.com/OasisLMF/OasisPlatform/pull/1069) - If conf.ini is missing a [celery] section OASIS_CELERY_BROKER_URL fails to load 
* [#1072](https://github.com/OasisLMF/OasisPlatform/pull/1073) - Always mark Sub-tasks as error when hitting problems 
* [#1044](https://github.com/OasisLMF/OasisPlatform/pull/1044) - Release 2.3.5 (30th May 2024)
.. _`2.3.6`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.5...2.3.6

`2.3.5`_
 ---------
* [#1058](https://github.com/OasisLMF/OasisPlatform/pull/1058) -  CI - Disable external docker images scanning 
* [#1060](https://github.com/OasisLMF/OasisPlatform/pull/1060) - Set version 2.3.5
* [#1040](https://github.com/OasisLMF/OasisPlatform/pull/1040) - Azure Postgres Flexible server support   
* [#1038, #1039](https://github.com/OasisLMF/OasisPlatform/pull/1041) - Minor bug fixes for worker and server
* [#1042](https://github.com/OasisLMF/OasisPlatform/pull/1045) - Check older paramter names are updated and working in 2.3.4  
* [#1051](https://github.com/OasisLMF/OasisPlatform/pull/1051) - Fix running V2 workers with custom OED specification files
* [#1020](https://github.com/OasisLMF/OasisPlatform/pull/1020) - Release 2.3.4 (staging)
* [#1052](https://github.com/OasisLMF/OasisPlatform/pull/1054) - Lot3 - worker monitor compatibility fix needed 
* [#1055](https://github.com/OasisLMF/OasisPlatform/pull/1055) - Fix failing unittest in release branch 2.3.5
.. _`2.3.5`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.4...2.3.5

`2.3.4`_
 ---------
* [#1023](https://github.com/OasisLMF/OasisPlatform/pull/1024) - Error reading sub-task logs from S3 when AWS_LOCATION is set
* [#1025](https://github.com/OasisLMF/OasisPlatform/pull/1026) - V2 worker monitor - error when ktools logs are missing 
* [#1016](https://github.com/OasisLMF/OasisPlatform/pull/1016) - Release 2.3.3 (patch release) 
* [#1018](https://github.com/OasisLMF/OasisPlatform/pull/1018) - Fix namespace issue when called from analysis serializer
* [#1019](https://github.com/OasisLMF/OasisPlatform/pull/1019) - Fix the pre-analysis hook file loading for V2 workers 
.. _`2.3.4`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.3...2.3.4

`2.3.3`_
 ---------
* [#992](https://github.com/OasisLMF/OasisPlatform/pull/992) - Release 2.3.2
* [#1018](https://github.com/OasisLMF/OasisPlatform/pull/1018) - Fix namespace issue when called from analysis serializer
* [#1006](https://github.com/OasisLMF/OasisPlatform/pull/1007) - Migration Helper script needs fixing
* [#1008](https://github.com/OasisLMF/OasisPlatform/pull/1015) - CI v1 worker test seems to get stuck at `6_case`
.. _`2.3.3`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.2...2.3.3

`2.3.2`_
 ---------
* [#993, #971, #784, #664, #798](https://github.com/OasisLMF/OasisPlatform/pull/994) - Logging fixes for workers 
* [#995](https://github.com/OasisLMF/OasisPlatform/pull/996) - List analyses serializer returning Portfolio does not exist error 
* [#1004](https://github.com/OasisLMF/OasisPlatform/pull/1004) - Fixes for task Cancellation Handling 
* [#1005](https://github.com/OasisLMF/OasisPlatform/pull/1005) - Remove DB migration env on websocket
* [#979](https://github.com/OasisLMF/OasisPlatform/pull/979) - Release 2.3.1
* [#989](https://github.com/OasisLMF/OasisPlatform/pull/990) - Calling `queue` or `queue-status` invokes django channels from HTTP server
* [#977](https://github.com/OasisLMF/OasisPlatform/pull/991) - Intermittent boto3 client error when sending json settings to S3 store   
.. _`2.3.2`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.1...2.3.2

`2.3.1`_
 ---------
* [#623, #797, #967](https://github.com/OasisLMF/OasisPlatform/pull/975) - Fix OOM worker retires infinite loop
* [#980](https://github.com/OasisLMF/OasisPlatform/pull/981) - Error when linking S3 object to portfolio
* [#982](https://github.com/OasisLMF/OasisPlatform/pull/982) - Fix run validation for V1 models
* [#978, #932, #869](https://github.com/OasisLMF/OasisPlatform/pull/983) - Fixes for websocket stability
* [#985](https://github.com/OasisLMF/OasisPlatform/pull/986) - Issue with pandas 2.x.x and v2 key generation 
.. _`2.3.1`:  https://github.com/OasisLMF/OasisPlatform/compare/2.3.0...2.3.1

`2.3.0`_
 ---------
* [#898](https://github.com/OasisLMF/OasisPlatform/pull/898) - Fix ods-tools changelog call
* [#869](https://github.com/OasisLMF/OasisPlatform/pull/899) - Worker Controller crashing under heavy load 
* [#897](https://github.com/OasisLMF/OasisPlatform/pull/906) - Collected WebSocket bug fixes
* [#912](https://github.com/OasisLMF/OasisPlatform/pull/912) - Fix syntax in flower chart template
* [#913](https://github.com/OasisLMF/OasisPlatform/pull/914) - Add ENV var to disable http in websocket pod
* [#918](https://github.com/OasisLMF/OasisPlatform/pull/918) - Fix worker_count_max assigment
* [#920](https://github.com/OasisLMF/OasisPlatform/pull/921) - ODS Tools link in release notes points to OasisLMF repo
* [#929](https://github.com/OasisLMF/OasisPlatform/pull/930) - Platform 2 - Keycloak DB reset on restart or redeployment. 
* [#893](https://github.com/OasisLMF/OasisPlatform/pull/931) - Support Platform 1 workers on the v2 server 
* [#942](https://github.com/OasisLMF/OasisPlatform/pull/942) - Updated Package Requirements: oasislmf==1.28.5 ods-tools==3.1.4
* [#928, #681](https://github.com/OasisLMF/OasisPlatform/pull/944) - Added chunking options to analysis level
* [#905, #786](https://github.com/OasisLMF/OasisPlatform/pull/945) - Fixed generate and run endpoint 
* [#818](https://github.com/OasisLMF/OasisPlatform/pull/818) - Update/remote trig python tests
* [#910](https://github.com/OasisLMF/OasisPlatform/pull/947) - Add post analysis hook to platform 2 workflow 
* [#890](https://github.com/OasisLMF/OasisPlatform/pull/948) - Fetch a model's versions when auto-registration is disabled 
* [#903](https://github.com/OasisLMF/OasisPlatform/pull/950) - File linking OED from sub-directories fails to link inside workers   
* [#953](https://github.com/OasisLMF/OasisPlatform/pull/954) - Platform 2.1.3 - No free channel ids error
* [#955](https://github.com/OasisLMF/OasisPlatform/pull/955) - Revert "Always post model version info on worker startup (platform 2)…
* [#951](https://github.com/OasisLMF/OasisPlatform/pull/956) - Allow 'single instance' execution from v2 api 
* [#952](https://github.com/OasisLMF/OasisPlatform/pull/957) - Cleaner split between v1 and v2 OpenAPI schemas
* [#960](https://github.com/OasisLMF/OasisPlatform/pull/960) - Update external images & python packages (2.3.0 release)
* [#961](https://github.com/OasisLMF/OasisPlatform/pull/963) - Remove the python3-pip from production server images 
* [#966](https://github.com/OasisLMF/OasisPlatform/pull/966) - Fix broken swagger calls when SUB_PATH_URL=True 
* [#968](https://github.com/OasisLMF/OasisPlatform/pull/968) - Fix model registration script for v1 workers 
* [#857](https://github.com/OasisLMF/OasisPlatform/pull/857) - Release 2.2.1 (staging)
* [#872](https://github.com/OasisLMF/OasisPlatform/pull/882) - Investigate flower error in monitoring chart 
* [#871](https://github.com/OasisLMF/OasisPlatform/pull/883) - Handle exceptions from OedExposure on file Upload 
* [#702](https://github.com/OasisLMF/OasisPlatform/pull/886) - Fix worker controller stablility 
.. _`2.3.0`:  https://github.com/OasisLMF/OasisPlatform/compare/2.2.1...2.3.0

`2.2.1`_
 ---------
* [#849](https://github.com/OasisLMF/OasisPlatform/pull/849) - Feautre/1323 reorganize branches plat2
* [#868](https://github.com/OasisLMF/OasisPlatform/pull/865) - Fixes for OasisPlatform Publish
* [#860, #863](https://github.com/OasisLMF/OasisPlatform/pull/862) - Fix/migrations plat1 to plat2
* [#847](https://github.com/OasisLMF/OasisPlatform/pull/847) - Release 2.2.0
.. _`2.2.1`:  https://github.com/OasisLMF/OasisPlatform/compare/2.2.0...2.2.1

`2.2.1rc1`_
 ---------
* [#849](https://github.com/OasisLMF/OasisPlatform/pull/849) - Feautre/1323 reorganize branches plat2
* [#860, #863](https://github.com/OasisLMF/OasisPlatform/pull/862) - Fix/migrations plat1 to plat2
* [#847](https://github.com/OasisLMF/OasisPlatform/pull/847) - Release 2.2.0
.. _`2.2.1rc1`:  https://github.com/OasisLMF/OasisPlatform/compare/2.2.0...2.2.1rc1

`2.2.0`_
 ---------
* [#725](https://github.com/OasisLMF/OasisPlatform/pull/843) - Queue priority for same job
* [#842](https://github.com/OasisLMF/OasisPlatform/pull/842) - Fix CVE-2023-30608
* [#813, #822](https://github.com/OasisLMF/OasisPlatform/pull/835) - Fixes for OpenAPI schema
* [#679](https://github.com/OasisLMF/OasisPlatform/pull/844) - Portfolio file linking fails with azure file share 
.. _`2.2.0`:  https://github.com/OasisLMF/OasisPlatform/compare/2.1.2...2.2.0

`2.1.2`_
 ---------
* [#834](https://github.com/OasisLMF/OasisPlatform/pull/834) - Update external docker images
* [#813, #822](https://github.com/OasisLMF/OasisPlatform/pull/835) - Fixes for OpenAPI schema
* [#823](https://github.com/OasisLMF/OasisPlatform/pull/828) - Possible bug in collect keys sub-task 
* [#782](https://github.com/OasisLMF/OasisPlatform/pull/782) - Feature/ods read from stream Plat2
* [#824](https://github.com/OasisLMF/OasisPlatform/pull/824) - Fix typo in requirments-worker.in causing incorrect package install
* [#821](https://github.com/OasisLMF/OasisPlatform/pull/821) - Miscellaneous platform 2 improvements
* [#790](https://github.com/OasisLMF/OasisPlatform/pull/790) - Release/2.1.1
* [#791](https://github.com/OasisLMF/OasisPlatform/pull/791) - Fix bug in release note build script
* [#792](https://github.com/OasisLMF/OasisPlatform/pull/792) - Limit external image scans to release PRs
* [#796](https://github.com/OasisLMF/OasisPlatform/pull/796) - Plat 2.1.1 fixes
* [#830](https://github.com/OasisLMF/OasisPlatform/pull/830) - Fix pre-analysis hook 
.. _`2.1.2`:  https://github.com/OasisLMF/OasisPlatform/compare/2.1.1...2.1.2

`2.1.1`_
 ---------
* [#771](https://github.com/OasisLMF/OasisPlatform/pull/772) - Add ODS_Tools version summary to release notes builder
* [#775](https://github.com/OasisLMF/OasisPlatform/pull/775) - Search all repo for tags, but limit the scope by env
* [#639](https://github.com/OasisLMF/OasisPlatform/pull/648) - CVE security cleanup 
* [#776](https://github.com/OasisLMF/OasisPlatform/pull/776) - Platform 2 - Updates and forward ports 
* [#608](https://github.com/OasisLMF/OasisPlatform/pull/651) - Store templates for analysis settings 
* [#780](https://github.com/OasisLMF/OasisPlatform/pull/779) - DataFiles are not loaded in Platform2 
* [#633](https://github.com/OasisLMF/OasisPlatform/pull/653) - List serilizer reutrns are not sorted by 'id'
* [#782](https://github.com/OasisLMF/OasisPlatform/pull/782) - Feature/ods read from stream Plat2
* [#624](https://github.com/OasisLMF/OasisPlatform/pull/655) - Update sub_task_list endpoint
* [#631](https://github.com/OasisLMF/OasisPlatform/pull/656) - Auto scaling not dropping to zero worker pods 
* [#625, #635](https://github.com/OasisLMF/OasisPlatform/pull/657) - Fixes for work sub-tasks 
* [#652](https://github.com/OasisLMF/OasisPlatform/pull/659) - Oasis UI - idle session crash 
* [#660](https://github.com/OasisLMF/OasisPlatform/pull/660) - Fix/loclines lessthan chunks
* [#785](https://github.com/OasisLMF/OasisPlatform/pull/787) - Analysis run fails when using custom user data files
* [#646](https://github.com/OasisLMF/OasisPlatform/pull/662) - Dynamic scalling models can causes websocket pushes to fail. 
* [#634](https://github.com/OasisLMF/OasisPlatform/pull/663) - Add pre-analysis hook to new workflow 
* [#789](https://github.com/OasisLMF/OasisPlatform/pull/789) - Update Python packages for v2.1.1
* [#646](https://github.com/OasisLMF/OasisPlatform/pull/665) - Dynamic scalling models can causes websocket pushes to fail. 
* [#669](https://github.com/OasisLMF/OasisPlatform/pull/670) - Remove "lookup_complex_config_json" if no settings file given
* [#677](https://github.com/OasisLMF/OasisPlatform/pull/685) - Investigate - large file downloads failing from the azure hosted platform  
* [#686](https://github.com/OasisLMF/OasisPlatform/pull/687) - Update channels redis config to have SSL options
* [#697](https://github.com/OasisLMF/OasisPlatform/pull/697) - Fix/auth timeout
* [#700](https://github.com/OasisLMF/OasisPlatform/pull/700) - Fix/error reading file len
* [#708](https://github.com/OasisLMF/OasisPlatform/pull/708) - Update/CVE versions
* [#740](https://github.com/OasisLMF/OasisPlatform/pull/709) - CVE Update external Image versions 
* [#711](https://github.com/OasisLMF/OasisPlatform/pull/711) - Github actions CI/CD update
* [#717](https://github.com/OasisLMF/OasisPlatform/pull/717) - Fixes for Github actions - Platform 2.x
* [#718](https://github.com/OasisLMF/OasisPlatform/pull/719) - ConfigMap error when installing the helm charts to k3s
* [#722, #723](https://github.com/OasisLMF/OasisPlatform/pull/724) - Added OED validation on file upload, and updated ods-tools package to 3.0.1
* [#674](https://github.com/OasisLMF/OasisPlatform/pull/731) - Collect custom lookup output 
* [#734](https://github.com/OasisLMF/OasisPlatform/pull/744) - Add OED v3 support to the scalable platform 
* [#741](https://github.com/OasisLMF/OasisPlatform/pull/745) - Fix Piwind testing on platform 2 
* [#746](https://github.com/OasisLMF/OasisPlatform/pull/746) - CVE scans are raising issues but Actions marked as passed
* [#620](https://github.com/OasisLMF/OasisPlatform/pull/620) - Feature/1018 default samples
* [#608](https://github.com/OasisLMF/OasisPlatform/pull/621) - Store templates for analysis settings 
* [#738](https://github.com/OasisLMF/OasisPlatform/pull/748) - CVE update Prometheus 
* [#753](https://github.com/OasisLMF/OasisPlatform/pull/753) - Set ods-tools 3.0.2
* [#740, #742](https://github.com/OasisLMF/OasisPlatform/pull/757) - Update external image versions 
* [#758](https://github.com/OasisLMF/OasisPlatform/pull/758) - Fixes for merging of distributed input files
* [#761](https://github.com/OasisLMF/OasisPlatform/pull/761) -  Release Platform 2.1.0 (Horizontal scaling / Kubernetes)  --
* [#754](https://github.com/OasisLMF/OasisPlatform/pull/762) - Update the model settings schema to include correlation options  
* [#764](https://github.com/OasisLMF/OasisPlatform/pull/764) - Fix schema build workflow
* [#765](https://github.com/OasisLMF/OasisPlatform/pull/765) - Move json settings schema to ods-tools
.. _`2.1.1`:  https://github.com/OasisLMF/OasisPlatform/compare/2.1.0...2.1.1

`2.1.0`_
 ---------
* [#754](https://github.com/OasisLMF/OasisPlatform/pull/762) - Update the model settings schema to include correlation options  
* [#740](https://github.com/OasisLMF/OasisPlatform/pull/709) - CVE Update external Image versions 
* [#711](https://github.com/OasisLMF/OasisPlatform/pull/711) - Github actions CI/CD update
* [#734](https://github.com/OasisLMF/OasisPlatform/pull/744) - Add OED v3 support to the scalable platform 
* [#741](https://github.com/OasisLMF/OasisPlatform/pull/745) - Fix Piwind testing on platform 2 
* [#746](https://github.com/OasisLMF/OasisPlatform/pull/746) - CVE scans are raising issues but Actions marked as passed
* [#738](https://github.com/OasisLMF/OasisPlatform/pull/748) - CVE update Prometheus 
* [#717](https://github.com/OasisLMF/OasisPlatform/pull/717) - Fixes for Github actions - Platform 2.x
* [#718](https://github.com/OasisLMF/OasisPlatform/pull/719) - ConfigMap error when installing the helm charts to k3s
* [#753](https://github.com/OasisLMF/OasisPlatform/pull/753) - Set ods-tools 3.0.2
* [#722, #723](https://github.com/OasisLMF/OasisPlatform/pull/724) - Added OED validation on file upload, and updated ods-tools package to 3.0.1
* [#740, #742](https://github.com/OasisLMF/OasisPlatform/pull/757) - Update external image versions 
* [#758](https://github.com/OasisLMF/OasisPlatform/pull/758) - Fixes for merging of distributed input files
* [#729](https://github.com/OasisLMF/OasisPlatform/pull/730) - No support for private image registries
* [#674](https://github.com/OasisLMF/OasisPlatform/pull/731) - Collect custom lookup output 
* [#764](https://github.com/OasisLMF/OasisPlatform/pull/764) - Fix schema build workflow
* [#669](https://github.com/OasisLMF/OasisPlatform/pull/670) - Remove "lookup_complex_config_json" if no settings file given
.. _`2.1.0`:  https://github.com/OasisLMF/OasisPlatform/compare/2.1.0-dev...2.1.0

`1.18.0`_
 ---------
* [#512](https://github.com/OasisLMF/OasisPlatform/pull/512) - Fix/django CVE issues
* [#500](https://github.com/OasisLMF/OasisPlatform/pull/500) - Added Github Templates
* [#504](https://github.com/OasisLMF/OasisPlatform/pull/504) - Add explicit version tags for auto-release notes
* [#505](https://github.com/OasisLMF/OasisPlatform/pull/505) - Fix clash with requirements files
* [#507](https://github.com/OasisLMF/OasisPlatform/pull/507) - Update urllib3 for CVE-2021-33503
* [#509](https://github.com/OasisLMF/OasisPlatform/pull/510) - Slow portfolio queries 
* [#511](https://github.com/OasisLMF/OasisPlatform/pull/511) - Build model worker with optional packages
.. _`1.18.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.17.0...1.18.0

`1.17.0`_
 ---------
* [#485](https://github.com/OasisLMF/OasisPlatform/pull/487) - Update critical CVE for backport 1.15.x
* [#468](https://github.com/OasisLMF/OasisPlatform/pull/488) - Automate piwind worker build on release 
* [#492](https://github.com/OasisLMF/OasisPlatform/pull/492) - Bump Django to 3.1.8 - CVE-2021-28658
* [#495](https://github.com/OasisLMF/OasisPlatform/pull/495) - Align Platform schema with oasislmf
* [#497](https://github.com/OasisLMF/OasisPlatform/pull/497) - Update bash promp to show oasis version number
* [#498](https://github.com/OasisLMF/OasisPlatform/pull/499) - Portfolio s3 storage link issue (S3)
* [#500](https://github.com/OasisLMF/OasisPlatform/pull/500) - Added Github Templates
* [#501](https://github.com/OasisLMF/OasisPlatform/pull/501) - Update build script
* [#504](https://github.com/OasisLMF/OasisPlatform/pull/504) - Add explicit version tags for auto-release notes
* [#505](https://github.com/OasisLMF/OasisPlatform/pull/505) - Fix clash with requirements files
* [#507](https://github.com/OasisLMF/OasisPlatform/pull/507) - Update urllib3 for CVE-2021-33503
.. _`1.17.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.16.0...1.17.0

`1.17.0rc1`_
 ---------
* [#485](https://github.com/OasisLMF/OasisPlatform/pull/487) - Update critical CVE for backport 1.15.x
* [#468](https://github.com/OasisLMF/OasisPlatform/pull/488) - Automate piwind worker build on release 
* [#492](https://github.com/OasisLMF/OasisPlatform/pull/492) - Bump Django to 3.1.8 - CVE-2021-28658
* [#495](https://github.com/OasisLMF/OasisPlatform/pull/495) - Align Platform schema with oasislmf
* [#497](https://github.com/OasisLMF/OasisPlatform/pull/497) - Update bash promp to show oasis version number
* [#498](https://github.com/OasisLMF/OasisPlatform/pull/499) - Portfolio s3 storage link issue (S3)
* [#500](https://github.com/OasisLMF/OasisPlatform/pull/500) - Added Github Templates
* [#501](https://github.com/OasisLMF/OasisPlatform/pull/501) - Update build script
* [#504](https://github.com/OasisLMF/OasisPlatform/pull/504) - Add explicit version tags for auto-release notes
.. _`1.17.0rc1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.16.0...1.17.0rc1

`1.16.0`_
---------
* [#480](https://github.com/OasisLMF/OasisPlatform/issues/480) - Revert new cancellation stauts, causes UI to crash
* [#479](https://github.com/OasisLMF/OasisPlatform/issues/479) - Fix error in the swagger generation
* [#467](https://github.com/OasisLMF/OasisPlatform/issues/468) - Automate piwind worker build on release
* [#467](https://github.com/OasisLMF/OasisPlatform/issues/467) - Single endpoint which cancels either analysis run and generation
* [#486](https://github.com/OasisLMF/OasisPlatform/pull/486) - Update alpine packages in server image for CVE fixes
* [#465](https://github.com/OasisLMF/OasisPlatform/issues/465) - Fixed, cancelling running task doesn't terminate execution pipeline 
* [#471](https://github.com/OasisLMF/OasisPlatform/pull/471) - ORD outputs schema update 
* [#475](https://github.com/OasisLMF/OasisPlatform/issues/475) - Add pre-release process  
* [#470](https://github.com/OasisLMF/OasisPlatform/pull/470) - Update package requirements for security fixes 

`1.15.7`_
---------
* [#485 - Hotfix](https://github.com/OasisLMF/OasisLMF/pull/485) - Update critical CVE for `jsonpickle`
* [#468 - Hotfix](https://github.com/OasisLMF/OasisPlatform/issues/468) - Automate piwind worker build on release

`1.15.6`_
---------
* [#803 - Hotfix](https://github.com/OasisLMF/OasisLMF/pull/802) - Partial fix for Max Ded back allocation in fmpy

`1.15.5`_
---------
* [#798 - Hotfix](https://github.com/OasisLMF/OasisLMF/issues/798) - Fix process cleanup on ktools script exit 
* [#799 - Hotfix](https://github.com/OasisLMF/OasisLMF/issues/799) - Fix fmpy, multilayer stream writer for RI  
* [#794 - Hotfix](https://github.com/OasisLMF/OasisLMF/issues/794) - Fix column duplication when using "tiv, loc_id, coverage_type_id" in oed_field

`1.15.4`_
---------
* [#464 - Hotfix](https://github.com/OasisLMF/OasisPlatform/issues/464) - Worker stuck idle on some bash errors
* [#785 - Hotfix](https://github.com/OasisLMF/OasisLMF/issues/785) - fmsummaryxref.csv not copied into top level RI directory

`1.15.3`_
---------
* Hotfix for fmpy 

`1.15.2`_
---------
* Hotfix for core oasislmf package

`1.15.0`_
---------
* [#460](https://github.com/OasisLMF/OasisPlatform/issues/460) - Added required packages and example compose file for PostgreSQL support
* [#459](https://github.com/OasisLMF/OasisPlatform/issues/459) - Fix for API load stability

`1.14.0`_
---------
* [#455](https://github.com/OasisLMF/OasisPlatform/issues/455) - Added `wait_until_exists()` call after coping a results object between worker and server storage spaces
* [#454](https://github.com/OasisLMF/OasisPlatform/issues/454) - Added new config option `AWS454LOG454LEVEL` to set S3 logging level independently of the oasis logger

`1.13.2`_
---------
* [#456](https://github.com/OasisLMF/OasisPlatform/pull/456) - Fix JSON schema's to be inline with oasislmf

`1.13.1`_
---------
* Restore default model settings option
* Update oasislmf package to 1.13.1

`1.13.0`_
---------
* [#432](https://github.com/OasisLMF/OasisPlatform/pull/432) - Update Python dependencies
* [#434](https://github.com/OasisLMF/OasisPlatform/pull/434) - Worker environment variables take precedence over config files
* [#387](https://github.com/OasisLMF/OasisPlatform/issues/387) - Disabled task prefetch in workers - blocks idle workers from executing
* [#368](https://github.com/OasisLMF/OasisPlatform/issues/368) - Adjust Docker mount points for model files to `/home/worker/model`
* [#438](https://github.com/OasisLMF/OasisPlatform/issues/438) - Add reporting output dependency by event_set to model_settings.json, see [PR #694](https://github.com/OasisLMF/OasisLMF/pull/694)
* [#444](https://github.com/OasisLMF/OasisPlatform/issues/444) - Fix Swagger ui, broken with Django 3.1+
* [#435](https://github.com/OasisLMF/OasisPlatform/issues/435) - Added `file_category` field to data_files endpoint
* [#413](https://github.com/OasisLMF/OasisPlatform/issues/413) - Improved container security, added image vulnerability scanning, server base switched to apline and worker base switched to ubuntu:20.04

`1.12.1`_
---------
* Update oasislmf package to 1.12.1


`1.12.0`_
---------
* [#422](https://github.com/OasisLMF/OasisPlatform/issues/422) - Add S3 Integration tests to the platform
* [#419](https://github.com/OasisLMF/OasisPlatform/issues/419) - Give the API user the possibilty to manage files outside of oasis
* [#424](https://github.com/OasisLMF/OasisPlatform/issues/424) - Fixed default value for DISABLE_WORKER_REG
* [#400](https://github.com/OasisLMF/OasisPlatform/issues/400) - Extend model_settings.json with optional metadata from Nasdaq
* [#423](https://github.com/OasisLMF/OasisPlatform/issues/423) - Revert feature #377 - always Read aws_location from confing dont store with file object
* [#409](https://github.com/OasisLMF/OasisPlatform/issues/409) -  Differentiate model run time parameters between generation and losses steps in model_settings.json


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

.. _`1.16.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.15.7...1.16.0
.. _`1.15.7`:  https://github.com/OasisLMF/OasisPlatform/compare/1.15.6...1.15.7
.. _`1.15.6`:  https://github.com/OasisLMF/OasisPlatform/compare/1.15.5...1.15.6
.. _`1.15.5`:  https://github.com/OasisLMF/OasisPlatform/compare/1.15.4...1.15.5
.. _`1.15.4`:  https://github.com/OasisLMF/OasisPlatform/compare/1.15.3...1.15.4
.. _`1.15.3`:  https://github.com/OasisLMF/OasisPlatform/compare/1.15.2...1.15.3
.. _`1.15.2`:  https://github.com/OasisLMF/OasisPlatform/compare/1.15.0...1.15.2
.. _`1.15.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.14.0...1.15.0
.. _`1.14.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.13.2...1.14.0
.. _`1.13.2`:  https://github.com/OasisLMF/OasisPlatform/compare/1.13.1...1.13.2
.. _`1.13.1`:  https://github.com/OasisLMF/OasisPlatform/compare/1.13.0...1.13.1
.. _`1.13.0`:  https://github.com/OasisLMF/OasisPlatform/compare/1.12.0...1.13.0
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

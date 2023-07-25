# Analysis Settings Overview

The run time settings for the analysis are controlled by the analysis_settings.json file which is a user supplied file detailing all of the options requested for the run (model to run, exposure set to use, number of samples, occurrence options, outputs required, etc.). In the MDK, the analysis settings file must be specified as part of the command line arguments (or in the oasislmf.json configuration file) and in the platform, it needs to be posted to the endpoint. A full json schema for the available options in the analysis settings file can be found here:

https://github.com/OasisLMF/ODS_Tools/blob/develop/ods_tools/data/analysis_settings_schema.json

# Model Settings Overview 

This is a configuration file provided with the model to specify important meta data about the model to model users and systems. It is supplied by the model provider and is a static document. A full specification of the model settings schema can be found here: https://github.com/OasisLMF/ODS_Tools/blob/main/ods_tools/data/model_settings_schema.json

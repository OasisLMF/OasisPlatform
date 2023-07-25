import json
from ods_tools.oed.setting_schema import ModelSettingSchema, AnalysisSettingSchema

with open('model_schema.json', "w") as f:
    json.dump(ModelSettingSchema().schema, f)

with open('analysis_schema.json', "w") as f:
    json.dump(AnalysisSettingSchema().schema, f)

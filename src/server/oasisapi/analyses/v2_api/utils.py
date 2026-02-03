from rest_framework.exceptions import ValidationError
from src.server.oasisapi.analyses.models import Analysis


def verify_model_scaling(model):
    if model.run_mode:
        if model.run_mode.lower() == "v1" and model.scaling_options:
            if model.scaling_options.scaling_strategy not in ["QUEUE_LOAD", "FIXED_WORKERS", None]:
                raise ValidationError("Model has invalid scaling setting")

def validate_and_get_combine_queryset(analysis_ids):
    queryset = Analysis.objects.filter(pk__in=analysis_ids)

    if len(queryset) != len(analysis_ids):
        raise ValidationError(f'Not all selected analyses {analysis_ids} found.')

    return queryset

from rest_framework import serializers

from .models import AnalysisModel


class AnalysisModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisModel
        fields = (
            'id',
            'supplier_id',
            'version_id',
            'created',
            'modified',
        )

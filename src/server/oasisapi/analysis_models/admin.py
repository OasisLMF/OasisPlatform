from django.contrib import admin
from .models import AnalysisModel

@admin.register(AnalysisModel)
class CatModelAdmin(admin.ModelAdmin):
    list_display = ['model_id', 'supplier_id', 'version_id', 'creator']

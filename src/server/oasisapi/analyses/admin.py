from django.contrib import admin
from .models import Analysis, AnalysisTaskStatus


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ['name', 'model']


@admin.register(AnalysisTaskStatus)
class AnalysisTaskStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'queue_name', 'task_id', 'analysis', 'status']

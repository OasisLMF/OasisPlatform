from django.contrib import admin
from .models import AnalysisModel, SettingsTemplate, ModelScalingOptions, ModelChunkingOptions
from django.contrib.admin.actions import delete_selected as delete_selected_


""" Cascading delete of Model and anything linked to it via foreign key
"""


def delete_hard(modeladmin, request, queryset):
    if not modeladmin.has_delete_permission(request):
        raise PermissionDenied
    for obj in queryset:
        obj.hard_delete()


""" Re-enables a soft-deleted model by toggling database flag
"""


def activate_model(modeladmin, request, queryset):
    if not modeladmin.has_add_permission(request):
        raise PermissionDenied
    for obj in queryset:
        obj.activate()


@admin.register(AnalysisModel)
class CatModelAdmin(admin.ModelAdmin):
    actions = [delete_hard, activate_model]
    list_display = [
        'model_id', 
        'supplier_id', 
        'version_id', 
        'creator', 
        'deleted'
    ]

    def get_queryset(self, request):
        return self.model.all_objects

    activate_model.short_description = "Activate Model"
    delete_hard.short_description = "Delete model - removes all linked analyses"
    delete_selected_.short_description = "Disable Model"


@admin.register(SettingsTemplate)
class SettingsTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'file', 
        'name', 
        'creator'
    ]

    
@admin.register(ModelScalingOptions)
class ModelScalingOptionsAdmin(admin.ModelAdmin):
    list_display = [
        'scaling_types', 
        'scaling_strategy', 
        'worker_count_fixed', 
        'worker_count_max', 
        'worker_count_min', 
        'chunks_per_worker',
    ]

@admin.register(ModelChunkingOptions)
class ModelChunkingTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'lookup_strategy',
        'loss_strategy',
        'dynamic_locations_per_lookup',
        'dynamic_events_per_analysis',
        'dynamic_chunks_max',
        'fixed_analysis_chunks',
        'fixed_lookup_chunks',
    ]

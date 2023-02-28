from django.contrib import admin
from .models import AnalysisModel, SettingsTemplate
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

    list_display = ['model_id', 'supplier_id', 'version_id', 'creator', 'deleted']

    def get_queryset(self, request):
        return self.model.all_objects

    activate_model.short_description = "Activate Model"
    delete_hard.short_description = "Delete model - removes all linked analyses"
    delete_selected_.short_description = "Disable Model"


@admin.register(SettingsTemplate)
class SettingsTemplateAdmin(admin.ModelAdmin):
    list_display = ['file', 'name', 'creator']

from django.contrib import admin
from .models import AnalysisModel
from django.contrib.admin.actions import delete_selected as delete_selected_


def delete_hard(modeladmin, request, queryset):
    if not modeladmin.has_delete_permission(request):
        raise PermissionDenied
    for obj in queryset:
        obj.hard_delete()
#actions.delete_hard.short_description = "Permiment Delete of model and linked analyses"

@admin.register(AnalysisModel)
class CatModelAdmin(admin.ModelAdmin):
    actions = [delete_hard]

    list_display = ['model_id', 'supplier_id', 'version_id', 'creator', 'deleted']

    def get_queryset(self, request):
        return self.model.all_objects
    
    delete_hard.short_description = "Cascade Delete of model and linked analyses"
    delete_selected_.short_description = "Delete"

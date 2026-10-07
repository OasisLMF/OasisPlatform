from django.contrib import admin

from .models import ExternalJob, ExternalProviderSettings


@admin.register(ExternalProviderSettings)
class ExternalProviderSettingsAdmin(admin.ModelAdmin):
    list_display = ['provider', 'base_url', 'client_id', 'updated']
    readonly_fields = ['updated']


@admin.register(ExternalJob)
class ExternalJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'provider', 'job_type', 'portfolio', 'status', 'created', 'finished']
    list_filter = ['provider', 'job_type', 'status']
    readonly_fields = ['id', 'task_id', 'request_data', 'started', 'finished', 'error_message', 'created', 'modified']

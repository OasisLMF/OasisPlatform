from django.contrib import admin
from .models import RelatedFile


@admin.register(RelatedFile)
class RelatedFileAdmin(admin.ModelAdmin):
    list_display = ['file', 'filename', 'content_type', 'creator']

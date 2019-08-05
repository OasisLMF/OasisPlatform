from django.contrib import admin
from .models import DataFile


@admin.register(DataFile)
class DataFileAdmin(admin.ModelAdmin):
    list_display = ['file_description', 'creator']

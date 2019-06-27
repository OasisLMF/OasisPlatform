from django.contrib import admin
from .models import DataFile


@admin.register(DataFile)
class DataFileAdmin(admin.ModelAdmin):
    list_display = ['filename', 'file_description', 'creator']

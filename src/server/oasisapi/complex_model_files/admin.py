from django.contrib import admin
from .models import ComplexModelDataFile


@admin.register(ComplexModelDataFile)
class ComplexModelFileAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'file_description', 'creator']

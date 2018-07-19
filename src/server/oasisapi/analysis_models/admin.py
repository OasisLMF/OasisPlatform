from django.contrib.admin import site

from .models import AnalysisModel

site.register(AnalysisModel)

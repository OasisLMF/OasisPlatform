from django.apps import AppConfig


class V1_AnalysesAppConfig(AppConfig):
    name = 'src.server.oasisapi.analyses.v1_api'

    def ready(self):
        from django.db.models.signals import post_save
        from .v2_api.signal_receivers import analysis_updated
        from .models import Analysis

        post_save.connect(analysis_updated, sender=Analysis)


class V2_AnalysesAppConfig(AppConfig):
    name = 'src.server.oasisapi.analyses.v2_api'

    def ready(self):
        from django.db.models.signals import post_save
        from .v2_api.signal_receivers import analysis_updated
        from .models import Analysis

        post_save.connect(analysis_updated, sender=Analysis)

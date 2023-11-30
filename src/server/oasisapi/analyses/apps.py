from django.apps import AppConfig


class V1_AnalysesAppConfig(AppConfig):
    name = 'src.server.oasisapi.analyses.v1_api'

class V2_AnalysesAppConfig(AppConfig):
    name = 'src.server.oasisapi.analyses.v2_api'

    def ready(self):
        from django.db.models.signals import post_save
        from .signal_receivers import task_updated
        from .models import AnalysisTaskStatus

        post_save.connect(task_updated, sender=AnalysisTaskStatus)

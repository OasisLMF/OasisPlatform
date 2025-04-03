from django.apps import AppConfig


class V1_AnalysesAppConfig(AppConfig):
    name = 'src.server.oasisapi.analyses.v1_api'

    def ready(self):
        from src.server.oasisapi.signals import default_ready
        default_ready()


class V2_AnalysesAppConfig(AppConfig):
    name = 'src.server.oasisapi.analyses.v2_api'

    def ready(self):
        from src.server.oasisapi.signals import default_ready
        default_ready()

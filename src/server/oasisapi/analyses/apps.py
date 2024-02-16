from django.apps import AppConfig


class V1_AnalysesAppConfig(AppConfig):
    name = 'src.server.oasisapi.analyses.v1_api'


class V2_AnalysesAppConfig(AppConfig):
    name = 'src.server.oasisapi.analyses.v2_api'

    # def ready(self):
    #     from django.db.models.signals import post_save
    #     from .v2_api.signal_receivers import task_updated
    #     from .models import AnalysisTaskStatus
    #
    #     """ This sends an update to the web-socket on each update of a subtask and can generate a lot of
    #         messages under heavy load --- test removing this feature and scaling based on the periodic
    #         queue updates
    #     """
    #      post_save.connect(task_updated, sender=AnalysisTaskStatus)

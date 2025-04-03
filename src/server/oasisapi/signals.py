from django.dispatch import Signal

post_update = Signal(providing_args=['analysis', 'tasks'])

def default_ready():
    from django.db.models.signals import post_save
    from .analyses.v2_api.signal_receivers import task_updated
    from .analyses.models import AnalysisTaskStatus

    post_save.connect(task_updated, sender=AnalysisTaskStatus)

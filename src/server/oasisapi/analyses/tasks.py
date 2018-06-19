from __future__ import absolute_import

from ..celery import celery_app


@celery_app.task()
def poll_analysis_status(pk):
    from .models import Analysis

    analysis = Analysis.objects.get(pk=pk)
    
    # check status

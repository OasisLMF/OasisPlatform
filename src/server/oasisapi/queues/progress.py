from django.db.models import F

# Run progress pings from workers, mapped to the Analysis field each one updates.
# Totals replace the stored value; counts are increments, since many processes report for the same run.
PROGRESS_TOTALS = {
    'events_total': 'num_events_total',
    'outputs_total': 'num_outputs_total',
}
PROGRESS_COUNTS = {
    'events_complete': 'num_events_complete',
    'gul_processes': 'num_gul_processes',
    'gul_ready': 'num_gul_ready',
    'outputs_complete': 'num_outputs_complete',
}


def analysis_progress_updates(data):
    """Maps a run progress ping to the Analysis field updates it makes.

    Counts become atomic SQL increments (``F(field) + n``), so pings from different worker processes
    can't clobber one another. Totals are set as sent: ``events_total`` is reported once per chunk, so
    the matching counts are reset at run start (``Analysis._reset_loss_progress``), never here.

    Args:
        data (dict): the ping, e.g. ``{'analysis_pk': 1, 'events_complete': 3}``. Values may be numbers or
            numeric strings, as sent over the websocket. Unknown keys are ignored.

    Returns:
        dict: Analysis field name to new value or ``F`` expression, empty if the ping has no progress keys
    """
    updates = {}
    for key, field in PROGRESS_TOTALS.items():
        if key in data:
            updates[field] = int(float(data[key]))
    for key, field in PROGRESS_COUNTS.items():
        if key in data:
            updates[field] = F(field) + int(float(data[key]))
    return updates

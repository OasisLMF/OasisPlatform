from django.dispatch import Signal

post_update = Signal(providing_args=['analysis', 'tasks'])

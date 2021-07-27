import json

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from rest_framework_simplejwt.tokens import RefreshToken

try:
    from websocket import WebSocketApp
except ImportError:
    print('install websocket_client')
    exit(1)


def echo(app, message):
    print('Message received:')
    print(json.dumps(json.loads(message), indent=4))

def on_error(app, error):
    print(error)

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--url', default='ws://localhost:8000/ws/v1/queue-status/')

    def handle(self, *args, **options):
        user = get_user_model().objects.first()
        if not user:
            raise Exception('no users present in the database')

        ref_token = RefreshToken.for_user(user)
        acc_token = str(ref_token.access_token)

        app = WebSocketApp(
            options['url'],
            on_message=echo,
            on_error=on_error,
            header=[
                f'Authorization: Bearer {acc_token}',
            ]
        )
        app.run_forever()

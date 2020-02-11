import json

from django.core.management import BaseCommand

try:
    from websocket import WebSocketApp
except ImportError:
    print('install websocket_client')
    exit(1)


def echo(app, message):
    print('Message received:')
    print(json.dumps(json.loads(message), indent=4))


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--url', default='ws://localhost:8000/ws/tasks/')

    def handle(self, *args, **options):
        app = WebSocketApp(
            options['url'],
            on_message=echo,
        )
        app.run_forever()

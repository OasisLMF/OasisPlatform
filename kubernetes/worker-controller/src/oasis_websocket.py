import asyncio
import json
import logging
from urllib.parse import urljoin

import websockets
from aiohttp import ClientError
from websockets import ConnectionClosedError, WebSocketException

from autoscaler import AutoScaler
from oasis_client import OasisClient


class WebSocketConnection:
    """
    Handles connecting to the websocket. Before connecting to the socket we
    first fetch the access token from the server to authenticate the websocket.
    """

    def __init__(self, oasis_client: OasisClient):
        """
        :param oasis_client: Oasis API client.
        """
        self.oasis_client = oasis_client
        self.ws_scheme = 'wss://' if oasis_client.secure else 'ws://'
        self.connection = None

    async def __aenter__(self):

        access_token = await self.oasis_client.get_access_token()

        self.connection = websockets.connect(
            urljoin(f'{self.ws_scheme}{self.oasis_client.host}:{self.oasis_client.port}', '/ws/v1/queue-status/'),
            extra_headers={'AUTHORIZATION': f'Bearer {access_token}'}
        )
        return await self.connection.__aenter__()

    async def __aexit__(self, exc_type, exc_value, traceback):
        return await self.connection.__aexit__(exc_type, exc_value, traceback)

    def __await__(self):
        return self.connection.__await__()


async def next_msg(socket):
    """
    Collects messages from the websocket forever until the connection is closed
    or the program is stopped

    :param socket: The socket ot process

    :return: An iterable of websocket messages
    """
    while msg := await socket.recv():
        try:
            yield json.loads(msg)
        except ClientError:
            break


class OasisWebSocket:
    """
    Connects and listens to changes from the Oasis websocket. Each update from Oasis is processed and matched
    against a worker deployment auto scaling setting, and if found update the number of replicas of the deployment
    based on rules defined in autoscaler_rules.
    """

    def __init__(self, oasis_client: OasisClient, autoscaler: AutoScaler):
        """
        :param oasis_client: A initialized oasis client.
        :param autoscaler: The autoscaler to forward websocket messages to.
        """
        self.oasis_client = oasis_client
        self.autoscaler = autoscaler

    async def watch(self):
        """
        Connects to the websocket and handles all the messages from the websocket.
        If there is ever a connection issue, the task and application will stop and
        let kubernetes restart the pod.
        """
        running = True

        while running:
            try:
                async with WebSocketConnection(self.oasis_client) as socket:

                    async for msg in next_msg(socket):
                        logging.info('Socket message: %s', msg)
                        await self.autoscaler.process_queue_status_message(msg)
            except ConnectionClosedError as e:
                logging.exception(f'Connection to {self.oasis_client.host}:{self.oasis_client.port} was closed')
                running = False
            except (WebSocketException, ClientError) as e:
                logging.exception(f'Connection to {self.oasis_client.host}:{self.oasis_client.port} failed', e)
                running = False
            except Exception as e:
                logging.exception(f'Unexpected web socket exception thrown', e)
                running = False

        asyncio.get_event_loop().stop()

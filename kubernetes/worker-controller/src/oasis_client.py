import asyncio
import json
from urllib.parse import urljoin

import aiohttp
import time
from aiohttp import ClientResponse


class OasisClient:
    """
    A simple client for the Oasis API. Takes care of the access token and supports searching for models.
    """

    def __init__(self, host, port, secure, username, password):
        """
        :param host: Oasis API hostname.
        :param port: Oasis API port.
        :param secure: Use secure connection.
        :param username: Username for API authentication.
        :param password: Password for API authentication.
        """
        self.host = host
        self.port = port
        self.secure = secure
        self.http_host = ('https://' if secure else 'http://') + f'{host}:{port}'
        self.username = username
        self.password = password
        self.access_token = None
        self.token_expire_time = None

    def is_authenticated(self) -> bool:
        """
        Checks if the retrieved access token is expired or not.

        :return: True if access token is valid, False if expired.
        """
        return self.token_expire_time is not None and time.time() < self.token_expire_time

    async def authenticate(self):
        """
        Authenticates with username and password and on success stores the access token
        and expire time.
        """

        async with aiohttp.ClientSession(loop=asyncio.get_event_loop()) as session:
            params = {'username': self.username, 'password': self.password}

            async with session.post(urljoin(self.http_host, '/access_token/'), data=params) as response:

                data = await self.parse_answer(response)

                self.access_token = data['access_token']
                self.token_expire_time = time.time() + round(data['expires_in'] / 2)

    async def get_access_token(self) -> str:

        """
        Returns the access token - authentication will be made if there is none or it as expired.

        :return: Access token.
        """

        if not self.is_authenticated():
            await self.authenticate()

        return self.access_token

    async def authenticate_if_needed(self):
        """
        Authenticates if the access token is invalid. If we have a valid access token we will do nothing.
        """

        if not self.is_authenticated():
            await self.authenticate()

    async def get_oasis_model_id(self, supplier_id: str, model_id: str, model_version_id: str) -> int:
        """
        Get the Oasis model id by model information.

        :param supplier_id: Supplier id
        :param model_id: Model id
        :param model_version_id: Model version id
        :return: Oasis model id
        """

        await self.authenticate_if_needed()

        params = {
            'supplier_id': supplier_id,
            'model_id': model_id,
            'version_id': model_version_id
        }
        models = await self._get('/v1/models/', params)

        for model in models:
            if model['supplier_id'] == supplier_id and model['model_id'] == model_id and model['version_id'] == model_version_id:
                return model['id']

    async def get_auto_scaling(self, model_id):
        """
        Fetch a specific models auto scaling configuration.

        :param model_id: the oasis model id.
        :return: Autoscaling settings
        """

        await self.authenticate_if_needed()

        model = await self._get(f'/v1/models/{model_id}/scaling_configuration/')

        return model

    async def _get(self, path, params=None):
        """
        Run a get query against the Oasis API

        :param path: API path
        :param params: Url parameters
        :return:
        """
        headers = {
            'AUTHORIZATION': f'Bearer {self.access_token}'
        }
        async with aiohttp.ClientSession(loop=asyncio.get_event_loop()) as session:

            async with session.get(urljoin(self.http_host, path), params=params, headers=headers) as response:

                return await self.parse_answer(response)

    async def parse_answer(self, response: ClientResponse):
        """
        Verifies the API HTTP response (code 200 OK), parse the data as json and returns it.

        :param response: API query response.
        :return: Parsed json.
        """

        raw = (await response.content.read()).decode()

        if response.status != 200:
            raise Exception(f'Unexpected Oasis API response: {response.status}: {raw}')

        data = json.loads(raw)
        return data

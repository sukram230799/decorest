# -*- coding: utf-8 -*-
#
# Copyright 2018-2021 Bartosz Kryza <bkryza@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Generic wrappers around Http sessions."""

import asyncio
import typing

from .types import ArgsDict
from .utils import merge_dicts

if typing.TYPE_CHECKING:
    from .client import RestClient


class RestClientSession:
    """Wrap a `requests` session for specific API client."""
    def __init__(self, client: 'RestClient', **kwargs: ArgsDict) -> None:
        """Initialize the session instance with a specific API client."""
        self.__client: 'RestClient' = client

        # Create a session of type specific for given backend
        if self.__client.backend_ == 'requests':
            import requests
            from decorest.types import SessionTypes
            self.__session: SessionTypes = requests.Session()
            for a in requests.Session.__attrs__:
                if a in kwargs:
                    setattr(self.__session, a, kwargs[a])
        else:
            import httpx
            args = merge_dicts(self.__client.client_args_, kwargs)
            self.__session = httpx.Client(**args)

    def __enter__(self) -> 'RestClientSession':
        """Context manager initialization."""
        return self

    def __exit__(self, *args: typing.Any) -> None:
        """Context manager destruction."""
        self.__session.close()

    def __getitem__(self, key: str) -> typing.Any:
        """Return named client argument."""
        return self.__client._get_or_none(key)

    def __setitem__(self, key: str, value: typing.Any) -> None:
        """Set named client argument."""
        self.__client[key] = value

    def __getattr__(self, name: str) -> typing.Any:
        """Forward any method invocation to actual client with session."""
        if name == 'backend_session_':
            return self.__session

        # deprecated
        if name == '_requests_session':
            return self.__session

        if name == 'client_' or name == '_client':
            return self.__client

        if name == '_close':
            return self.__session.close

        if name == 'auth_' or name == '_auth':
            return self.__client['auth']

        def invoker(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
            kwargs['__session'] = self.__session
            return getattr(self.__client, name)(*args, **kwargs)

        return invoker


class RestClientAsyncSession:
    """Wrap a `requests` session for specific API client."""
    def __init__(self, client: 'RestClient', **kwargs: ArgsDict) \
            -> None:
        """Initialize the session instance with a specific API client."""
        self.__client: 'RestClient' = client

        # Create a session of type specific for given backend
        import httpx
        args = merge_dicts(self.__client.client_args_, kwargs)
        self.__session = httpx.AsyncClient(**args)

    async def __aenter__(self) -> 'RestClientAsyncSession':
        """Context manager initialization."""
        await self.__session.__aenter__()
        return self

    async def __aexit__(self, *args: typing.Any) -> None:
        """Context manager destruction."""
        await self.__session.__aexit__(*args)

    def __getattr__(self, name: str) -> typing.Any:
        """Forward any method invocation to actual client with session."""
        if name == '_requests_session':
            return self.__session

        if name == '_client':
            return self.__client

        if name == '_close':
            return self.__session.aclose

        if name == '_auth':
            return self.__session.auth

        async def invoker(*args: typing.Any,
                          **kwargs: typing.Any) -> typing.Any:
            kwargs['__session'] = self.__session

            # TODO: MERGE __client_args with kwargs
            assert asyncio.iscoroutinefunction(getattr(self.__client, name))
            return await getattr(self.__client, name)(*args, **kwargs)

        return invoker

# -*- coding: utf-8 -*-
#
# Copyright 2018-2022 Bartosz Kryza <bkryza@gmail.com>
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
"""DELETE Http method decorator."""
import asyncio
import typing
from functools import wraps

from .decorator_utils import set_decor
from .decorators import HttpMethodDecorator
from .types import HttpMethod, TDecor


class DELETE(HttpMethodDecorator):
    """DELETE HTTP method decorator."""
    def __init__(self, path: str):
        """Initialize with endpoint relative path."""
        super(DELETE, self).__init__(path)

    def __call__(self, func: TDecor) -> TDecor:
        """Callable operator."""
        set_decor(func, 'http_method', HttpMethod.DELETE)

        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_delete_decorator(*args: typing.Any,
                                             **kwargs: typing.Any) \
                    -> typing.Any:
                return await super(DELETE,
                                   self).call_async(func, *args, **kwargs)

            return typing.cast(TDecor, async_delete_decorator)

        @wraps(func)
        def delete_decorator(*args: typing.Any, **kwargs: typing.Any) \
                -> typing.Any:
            return super(DELETE, self).call(func, *args, **kwargs)

        return typing.cast(TDecor, delete_decorator)

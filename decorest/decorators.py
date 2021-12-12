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
"""Decorators implementation.

Each RestClient subclass has a `__decorest__` property storing
a dictionary with decorator values provided by decorators
added to the client class or method.
"""

import inspect
import json
import logging as LOG
import numbers
import typing
from operator import methodcaller

import requests
from requests.structures import CaseInsensitiveDict

from . import types
from .errors import HTTPErrorWrapper
from .types import ArgsDict, HttpMethod, HttpStatus
from .utils import dict_from_args, merge_dicts, render_path

DECOR_KEY = '__decorest__'

DECOR_LIST = [
    'header', 'query', 'form', 'multipart', 'on', 'accept', 'content',
    'timeout', 'stream', 'body'
]


def set_decor(t: typing.Any, name: str, value: typing.Any) -> None:
    """Decorate a function or class by storing the value under specific key."""
    if hasattr(t, '__wrapped__') and hasattr(t.__wrapped__, DECOR_KEY):
        setattr(t, DECOR_KEY, t.__wrapped__.__decorest__)

    if not hasattr(t, DECOR_KEY):
        setattr(t, DECOR_KEY, {})

    d = getattr(t, DECOR_KEY)

    if isinstance(value, CaseInsensitiveDict):
        if not d.get(name):
            d[name] = CaseInsensitiveDict()
        d[name] = merge_dicts(d[name], value)
    elif isinstance(value, dict):
        if not d.get(name):
            d[name] = {}
        d[name] = merge_dicts(d[name], value)
    elif isinstance(value, list):
        if not d.get(name):
            d[name] = []
        d[name].extend(value)
    else:
        d[name] = value


def get_decor(t: typing.Any, name: str) -> typing.Optional[typing.Any]:
    """
    Retrieve a named decorator value from class or function.

    Args:
        t (type): Decorated type (can be class or function)
        name (str): Name of the key

    Returns:
        object: any value assigned to the name key

    """
    if hasattr(t, DECOR_KEY) and getattr(t, DECOR_KEY).get(name):
        return getattr(t, DECOR_KEY)[name]

    return None


def on(status: typing.Union[types.ellipsis, int],
       handler: typing.Callable[..., typing.Any]) \
        -> typing.Callable[..., typing.Any]:
    """
    On status result handlers decorator.

    The handler is a function or lambda which will receive as
    the sole parameter the requests response object.
    """

    def on_decorator(t: typing.Callable[..., typing.Any]) \
            -> typing.Callable[..., typing.Any]:
        if status is Ellipsis:  # type: ignore
            set_decor(t, 'on', {HttpStatus.ANY: handler})
        elif isinstance(status, numbers.Integral):
            set_decor(t, 'on', {status: handler})
        else:
            raise TypeError("Status in @on decorator must be integer or '...'")
        return t

    return on_decorator


def query(name: str, value: typing.Optional[str] = None) \
        -> typing.Callable[..., typing.Any]:
    """Query parameter decorator."""

    def query_decorator(t: typing.Callable[..., typing.Any]) \
            -> typing.Callable[..., typing.Any]:
        value_ = value
        if inspect.isclass(t):
            raise TypeError("@query decorator can only be "
                            "applied to methods.")
        if not value_:
            value_ = name
        set_decor(t, 'query', {name: value_})
        return t

    return query_decorator


def form(name: str, value: typing.Optional[str] = None) \
        -> typing.Callable[..., typing.Any]:
    """Form parameter decorator."""

    def form_decorator(t: typing.Callable[..., typing.Any]) \
            -> typing.Callable[..., typing.Any]:
        value_ = value
        if inspect.isclass(t):
            raise TypeError("@form decorator can only be "
                            "applied to methods.")
        if not value_:
            value_ = name
        set_decor(t, 'form', {name: value_})
        return t

    return form_decorator


def multipart(name: str, value: typing.Optional[str] = None) \
        -> typing.Callable[..., typing.Any]:
    """Multipart parameter decorator."""

    def multipart_decorator(t: typing.Callable[..., typing.Any]) \
            -> typing.Callable[..., typing.Any]:
        value_ = value
        if inspect.isclass(t):
            raise TypeError("@multipart decorator can only be "
                            "applied to methods.")
        if not value_:
            value_ = name
        set_decor(t, 'multipart', {name: value_})
        return t

    return multipart_decorator


def header(name: str, value: typing.Optional[str] = None) \
        -> typing.Callable[..., typing.Any]:
    """Header class and method decorator."""

    def header_decorator(t: typing.Callable[..., typing.Any]) \
            -> typing.Callable[..., typing.Any]:
        value_ = value
        if not value_:
            value_ = name
        set_decor(t, 'header', CaseInsensitiveDict({name: value_}))
        return t

    return header_decorator


def endpoint(value: str) -> typing.Callable[..., typing.Any]:
    """Endpoint class and method decorator."""

    def endpoint_decorator(t: typing.Callable[..., typing.Any]) \
            -> typing.Callable[..., typing.Any]:
        set_decor(t, 'endpoint', value)
        return t

    return endpoint_decorator


def content(value: str) -> typing.Callable[..., typing.Any]:
    """Content-type header class and method decorator."""

    def content_decorator(t: typing.Callable[..., typing.Any]) \
            -> typing.Callable[..., typing.Any]:
        set_decor(t, 'header',
                  CaseInsensitiveDict({'Content-Type': value}))
        return t

    return content_decorator


def accept(value: str) -> typing.Callable[..., typing.Any]:
    """Accept header class and method decorator."""

    def accept_decorator(t: typing.Callable[..., typing.Any]) \
            -> typing.Callable[..., typing.Any]:
        set_decor(t, 'header',
                  CaseInsensitiveDict({'Accept': value}))
        return t

    return accept_decorator


def body(name: str,
         serializer: typing.Optional[typing.Callable[..., typing.Any]] = None) \
        -> typing.Callable[..., typing.Any]:
    """
    Body parameter decorator.

    Determines which method argument provides the body.
    """

    def body_decorator(t: typing.Callable[..., typing.Any]) \
            -> typing.Callable[..., typing.Any]:
        set_decor(t, 'body', (name, serializer))
        return t

    return body_decorator


def timeout(value: float) -> typing.Callable[..., typing.Any]:
    """
    Timeout parameter decorator.

    Specifies a default timeout value for method or entire API.
    """

    def timeout_decorator(t: typing.Callable[..., typing.Any]) \
            -> typing.Callable[..., typing.Any]:
        set_decor(t, 'timeout', value)
        return t

    return timeout_decorator


def stream(t: typing.Callable[..., typing.Any]) \
        -> typing.Callable[..., typing.Any]:
    """
    Stream parameter decorator, takes boolean True or False.

    If specified, adds `stream=value` to requests and the value returned
    from such method will be the requests object.
    """
    set_decor(t, 'stream', True)
    return t


class HttpMethodDecorator:
    """Abstract decorator for HTTP method decorators."""

    def __init__(self, path: str):
        """Initialize decorator with endpoint relative path."""
        self.path_template = path

    def call(self, func: typing.Callable[..., typing.Any],
             *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        """Execute the API HTTP request."""
        http_method = get_decor(func, 'http_method')
        rest_client = args[0]
        args_dict = dict_from_args(func, *args)
        req_path = render_path(self.path_template, args_dict)
        session = None
        if '__session' in kwargs:
            session = kwargs['__session']
            del kwargs['__session']

        # Merge query parameters from common values for all method
        # invocations with arguments provided in the method
        # arguments
        query_parameters = self.__merge_args(args_dict, func, 'query')
        form_parameters = self.__merge_args(args_dict, func, 'form')
        multipart_parameters = self.__merge_args(args_dict, func, 'multipart')
        header_parameters = merge_dicts(
            get_decor(rest_client.__class__, 'header'),
            self.__merge_args(args_dict, func, 'header'))

        # Merge header parameters with default values, treat header
        # decorators with 2 params as default values only if they
        # don't match the function argument names
        func_header_decors = get_decor(func, 'header')
        if func_header_decors:
            for key in func_header_decors.keys():
                if not func_header_decors[key] in args_dict:
                    header_parameters[key] = func_header_decors[key]

        # Get body content from positional arguments if one is specified
        # using @body decorator
        body_parameter = get_decor(func, 'body')
        body_content = None
        if body_parameter:
            body_content = args_dict.get(body_parameter[0])
            # Serialize body content first if serialization handler
            # was provided
            if body_content and body_parameter[1]:
                body_content = body_parameter[1](body_content)

        # Get authentication method for this call
        auth = rest_client._auth()

        # Get status handlers
        on_handlers = merge_dicts(get_decor(rest_client.__class__, 'on'),
                                  get_decor(func, 'on'))

        # Get timeout
        request_timeout = get_decor(rest_client.__class__, 'timeout')
        if get_decor(func, 'timeout'):
            request_timeout = get_decor(func, 'timeout')

        # Check if stream is requested for this call
        is_stream = get_decor(func, 'stream')
        if is_stream is None:
            is_stream = get_decor(rest_client.__class__, 'stream')

        #
        # If the kwargs contains any decorest decorators that should
        # be overloaded for this call, extract them.
        #
        # Pass the rest of kwargs to requests calls
        #
        if kwargs:
            for decor in DECOR_LIST:
                if decor in kwargs:
                    if decor == 'header':
                        self.__validate_decor(decor, kwargs, dict)
                        header_parameters = merge_dicts(
                            header_parameters, kwargs['header'])
                        del kwargs['header']
                    elif decor == 'query':
                        self.__validate_decor(decor, kwargs, dict)
                        query_parameters = merge_dicts(query_parameters,
                                                       kwargs['query'])
                        del kwargs['query']
                    elif decor == 'form':
                        self.__validate_decor(decor, kwargs, dict)
                        form_parameters = merge_dicts(form_parameters,
                                                      kwargs['form'])
                        del kwargs['form']
                    elif decor == 'multipart':
                        self.__validate_decor(decor, kwargs, dict)
                        multipart_parameters = merge_dicts(
                            multipart_parameters, kwargs['multipart'])
                        del kwargs['multipart']
                    elif decor == 'on':
                        self.__validate_decor(decor, kwargs, dict)
                        on_handlers = merge_dicts(on_handlers, kwargs['on'])
                        del kwargs['on']
                    elif decor == 'accept':
                        self.__validate_decor(decor, kwargs, str)
                        header_parameters['accept'] = kwargs['accept']
                        del kwargs['accept']
                    elif decor == 'content':
                        self.__validate_decor(decor, kwargs, str)
                        header_parameters['content-type'] = kwargs['content']
                        del kwargs['content']
                    elif decor == 'timeout':
                        self.__validate_decor(decor, kwargs, numbers.Number)
                        request_timeout = kwargs['timeout']
                        del kwargs['timeout']
                    elif decor == 'stream':
                        self.__validate_decor(decor, kwargs, bool)
                        is_stream = kwargs['stream']
                        del kwargs['stream']
                    elif decor == 'body':
                        body_content = kwargs['body']
                        del kwargs['body']
                    else:
                        pass

        # Build request from endpoint and query params
        req = rest_client.build_request(req_path.split('/'))

        # Handle multipart parameters, either from decorators
        # or ones passed directly through kwargs
        if multipart_parameters:
            is_multipart_request = True
            kwargs['files'] = multipart_parameters
        elif rest_client._backend() == 'requests':
            from requests_toolbelt.multipart.encoder import MultipartEncoder
            is_multipart_request = 'data' in kwargs and not isinstance(
                kwargs['data'], MultipartEncoder)
        else:
            is_multipart_request = 'files' in kwargs

        # Assume default content type if not multipart
        if ('content-type' not in header_parameters) \
                and not is_multipart_request:
            header_parameters['content-type'] = 'application/json'

        # Assume default accept
        if 'accept' not in header_parameters:
            header_parameters['accept'] = 'application/json'

        LOG.debug('Request: {method} {request}'.format(method=http_method,
                                                       request=req))

        if auth:
            kwargs['auth'] = auth

        if request_timeout:
            kwargs['timeout'] = request_timeout

        if body_content:
            if header_parameters.get('content-type') == 'application/json':
                if isinstance(body_content, dict):
                    body_content = json.dumps(body_content)

            if rest_client._backend() == 'httpx':
                if isinstance(body_content, dict):
                    kwargs['data'] = body_content
                else:
                    kwargs['content'] = body_content
            else:
                kwargs['data'] = body_content

        if query_parameters:
            kwargs['params'] = query_parameters

        if form_parameters:
            # If form parameters were passed, override the content-type
            header_parameters['content-type'] \
                = 'application/x-www-form-urlencoded'
            kwargs['data'] = form_parameters

        if is_stream:
            kwargs['stream'] = is_stream

        if header_parameters:
            kwargs['headers'] = dict(header_parameters.items())

        result = None

        # If '__session' was passed in the kwargs, execute this request
        # using the session context, otherwise execute directly via the
        # requests module
        if session:
            execution_context = session
        else:
            if rest_client._backend() == 'requests':
                execution_context = requests
            else:
                import httpx
                execution_context = httpx

        if http_method not in (HttpMethod.GET, HttpMethod.POST, HttpMethod.PUT,
                               HttpMethod.PATCH, HttpMethod.DELETE,
                               HttpMethod.HEAD, HttpMethod.OPTIONS):
            raise ValueError(
                'Unsupported HTTP method: {method}'.format(method=http_method))

        try:
            if rest_client._backend() == 'httpx' \
                    and http_method == HttpMethod.GET and is_stream:
                del kwargs['stream']
                result = execution_context.stream("GET", req, **kwargs)
            else:
                if http_method == HttpMethod.POST and is_multipart_request:
                    # TODO: Why do I have to do this?
                    if 'headers' in kwargs:
                        kwargs['headers'].pop('content-type', None)

                result = self.__dispatch(
                    execution_context, http_method, kwargs, req)
        except Exception as e:
            raise HTTPErrorWrapper(typing.cast(types.HTTPErrors, e))

        if on_handlers and result.status_code in on_handlers:
            # Use a registered handler for the returned status code
            return on_handlers[result.status_code](result)
        elif on_handlers and HttpStatus.ANY in on_handlers:
            # If a catch all status handler is provided - use it
            return on_handlers[HttpStatus.ANY](result)
        else:
            # If stream option was passed and no content handler
            # was defined, return requests response
            if is_stream:
                return result

            # Default response handler
            try:
                result.raise_for_status()
            except Exception as e:
                raise HTTPErrorWrapper(typing.cast(types.HTTPErrors, e))

            if result.text:
                content_type = result.headers.get('content-type')
                if content_type == 'application/json':
                    return result.json()
                elif content_type == 'application/octet-stream':
                    return result.content
                else:
                    return result.text

            return None

    def __dispatch(self, execution_context: typing.Callable[..., typing.Any],
                   http_method: typing.Union[str, HttpMethod],
                   kwargs: ArgsDict, req: str) -> typing.Any:
        """
        Dispatch HTTP method based on HTTPMethod enum type.

        Args:
            execution_context: requests or httpx object
            http_method(HttpMethod): HTTP method
            kwargs(dict): named arguments passed to the API method
            req(): request object
        """
        if isinstance(http_method, str):
            method = http_method
        else:
            method = http_method.value[0].lower()

        return methodcaller(method, req, **kwargs)(execution_context)

    def __validate_decor(self, decor: str, kwargs: ArgsDict,
                         cls: typing.Type[typing.Any]) -> None:
        """
        Ensure kwargs contain decor with specific type.

        Args:
            decor(str): Name of the decorator
            kwargs(dict): Named arguments passed to API call
            cls(class): Expected type of decorator parameter
        """
        if not isinstance(kwargs[decor], cls):
            raise TypeError(
                "{} value must be an instance of {}".format(
                    decor, cls.__name__))

    def __merge_args(self, args_dict: ArgsDict,
                     func: typing.Callable[..., typing.Any], decor: str) \
            -> ArgsDict:
        """
        Match named arguments from method call.

        Args:
            args_dict (dict): Function arguments dictionary
            func (type): Decorated function
            decor (str): Name of specific decorator (e.g. 'query')

        Returns:
            object: any value assigned to the name key
        """
        args_decor = get_decor(func, decor)
        parameters = {}
        if args_decor:
            for arg, param in args_decor.items():
                if args_dict.get(arg):
                    parameters[param] = args_dict[arg]
        return parameters

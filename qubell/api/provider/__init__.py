from functools import wraps
import inspect
import logging as log

import requests

from qubell.api.private.exceptions import ApiError, api_http_code_errors


log.getLogger("requests.packages.urllib3.connectionpool").setLevel(log.WARN)


def route(route_str):  # decorator param
    """
    Provides play2 likes routes, with python formatter
    All string fileds should be named parameters
    :param route_str: a route "GET /parent/{parentID}/child/{childId}{ctype}"
    :return: the response of requests.request
    """

    def wrapper(f):  # decorated function
        @wraps(f)
        def wrapped_func(*args, **kwargs):  # params of function
            self = args[0]
            method, url = route_str.split(" ")

            def defaults_dict():
                f_args, varargs, keywords, defaults = inspect.getargspec(f)
                defaults = defaults or []
                return dict(zip(f_args[-len(defaults):], defaults))

            defs = defaults_dict()

            route_args = dict(kwargs.items() + defs.items())

            def get_destination_url():
                try:
                    return url.format(**route_args)
                except KeyError as e:
                    raise AttributeError("Define {0} as named argument for route.".format(e))  # KeyError in format have a message with key

            destination_url = self.base_url + get_destination_url()
            f(*args, **kwargs)  # generally this is "pass"

            bypass_args = {param: kwargs[param] for param in ["data", "cookies", "auth", "files"] if param in kwargs}

            #add json content type for:
            # - all public api, meaning have basic auth
            # - private that ends with .json
            if destination_url.endswith('.json') or "auth" in kwargs:
                bypass_args['headers'] = {'Content-Type': 'application/json'}

            response = requests.request(method, destination_url, verify=self.verify_ssl, **bypass_args)
            if self.verify_codes:
                if response.status_code is not 200:
                    msg = "Route {0} returned code={1} and error: {2}".format(get_destination_url(), response.status_code,
                                                                              response.text)
                    if response.status_code in api_http_code_errors.keys():
                        raise api_http_code_errors[response.status_code](msg)
                    else:
                        log.debug(response.text)
                        raise ApiError(msg)
            return response

        return wrapped_func

    return wrapper


def play_auth(f):
    """
    Injects cookies, into requests call over route
    :return: route
    """

    def wrapper(*args, **kwargs):
        self = args[0]
        if "cookies" in kwargs:
            raise AttributeError("don't set cookies explicitly")
        assert self.is_connected, "not connected, call router.connect(email, password) first"
        assert self._cookies, "no cookies and connected o_O"
        kwargs["cookies"] = self._cookies
        return f(*args, **kwargs)

    return wrapper


def basic_auth(f):
    """
    Injects auth, into requests call over route
    :return: route
    """

    def wrapper(*args, **kwargs):
        self = args[0]
        if "auth" in kwargs:
            raise AttributeError("don't set auth token explicitly")
        assert self.is_connected, "not connected, call router.connect(email, password) first"
        assert self._auth, "no basic token and connected o_O"
        kwargs["auth"] = self._auth
        return f(*args, **kwargs)

    return wrapper
import unittest2
from mock import patch

from qubell.api.private.exceptions import ApiUnauthorizedError, ApiAuthenticationError, ApiNotFoundError, ApiError
from qubell.api.provider import route, play_auth, basic_auth

from qubell.api.provider.router import Router


json_header = {'Content-Type': 'application/json'}


def gen_response(code=200, resp_text="enjoy"):
    class DummyResponse:
        status_code = code
        text = resp_text

    return DummyResponse


@patch("requests.request", create=True)
class RouterDecoratorTests(unittest2.TestCase):
    class DummyRouter(Router):
        @property
        def is_connected(self): return True

        @route("GET /simple")
        def get_simple(self): pass

        @route("GET /simple")
        def get_simple_with_return(self):
            return "this is won't be returned"

        @route("POST /simple")
        def post_simple(self, data): pass

        @route("GET /named/{prefix}{some_name}")
        def get_named(self, some_name, prefix="id"): pass

        @play_auth
        @route("POST /auth")
        def post_something_privetly(self, cookies): pass

        @basic_auth
        @route("POST /auth")
        def post_something_publicly(self, auth): pass

        @play_auth
        @route("GET /simple.json")
        def get_simple_json(self, cookies): pass

    router = DummyRouter("http://nowhere.com")

    def test_simple_get(self, request_mock):
        request_mock.return_value = gen_response()
        self.router.get_simple()
        request_mock.assert_called_once_with('GET', 'http://nowhere.com/simple', verify=False)

    def test_return_from_request(self, request_mock):
        ret_val = gen_response()
        request_mock.return_value = ret_val
        assert self.router.get_simple_with_return() == ret_val
        assert request_mock.called

    def test_simple_post(self, request_mock):
        request_mock.return_value = gen_response()
        self.router.post_simple(data="many data")
        request_mock.assert_called_once_with('POST', 'http://nowhere.com/simple', verify=False, data="many data")

    def test_parameters(self, request_mock):
        request_mock.return_value = gen_response()
        self.router.get_named(some_name="12345")
        request_mock.assert_called_once_with('GET', 'http://nowhere.com/named/id12345', verify=False)

    def test_parameter_without_name(self, request_mock):
        """Route parameters should be defined explicitly"""
        with self.assertRaises(AttributeError) as context:
            self.router.get_named("12345")
        assert str(context.exception) == "Define 'some_name' as named argument for route."
        assert not request_mock.called

    def test_play_auth(self, request_mock):
        request_mock.return_value = gen_response()
        self.router._cookies = "Big Cake"
        self.router.post_something_privetly()
        request_mock.assert_called_once_with('POST', 'http://nowhere.com/auth', verify=False, cookies="Big Cake")

    def test_play_when_cookies_forced(self, request_mock):
        with self.assertRaises(AttributeError) as context:
            self.router.post_something_privetly(cookies="anything")
        assert str(context.exception) == "don't set cookies explicitly"
        assert not request_mock.called

    def test_basic_auth(self, request_mock):
        request_mock.return_value = gen_response()
        self.router._auth = "Encoding..."
        self.router.post_something_publicly()
        request_mock.assert_called_once_with('POST', 'http://nowhere.com/auth', verify=False, auth="Encoding...",
                                             headers=json_header)

    def test_basic_when_auth_forced(self, request_mock):
        with self.assertRaises(AttributeError) as context:
            self.router.post_something_publicly(auth="anything")
        assert str(context.exception) == "don't set auth token explicitly"
        assert not request_mock.called

    def test_simple_json(self, request_mock):
        request_mock.return_value = gen_response()
        self.router.get_simple_json()
        request_mock.assert_called_once_with('GET', 'http://nowhere.com/simple.json', headers=json_header,
                                             cookies="Big Cake", verify=False)

    # Error code processing
    #todo: refactor as data driven tests
    def test_error_401(self, request_mock):
        request_mock.return_value = gen_response(401, "check credentials")
        with self.assertRaises(ApiUnauthorizedError) as context:
            self.router.post_something_publicly()
        assert request_mock.called
        assert str(context.exception) == "Route /auth returned code=401 and error: check credentials"

    def test_error_403(self, request_mock):
        request_mock.return_value = gen_response(403, "ask admin for permissions")
        with self.assertRaises(ApiAuthenticationError) as context:
            self.router.post_something_publicly()
        assert request_mock.called
        assert str(context.exception) == "Route /auth returned code=403 and error: ask admin for permissions"

    def test_error_404(self, request_mock):
        request_mock.return_value = gen_response(404, "not found or don't have permissions")
        with self.assertRaises(ApiNotFoundError) as context:
            self.router.post_something_publicly()
        assert request_mock.called
        assert str(context.exception) == "Route /auth returned code=404 and error: not found or don't have permissions"

    def test_error_408(self, request_mock):
        request_mock.return_value = gen_response(408, "timeout")
        with self.assertRaises(ApiError) as context:
            self.router.post_something_publicly()
        assert request_mock.called
        assert str(context.exception) == "Route /auth returned code=408 and error: timeout"

    def test_error_500(self, request_mock):
        request_mock.return_value = gen_response(500, "server down")
        with self.assertRaises(ApiError) as context:
            self.router.post_something_publicly()
        assert request_mock.called
        assert str(context.exception) == "Route /auth returned code=500 and error: server down"

    def test_errors_can_be_ignored(self, request_mock):
        """Should not propagate errors if verify_codes turned off"""
        try:
            #tempoarary
            self.router.verify_codes = False

            ret_val = gen_response(404, "you hidded")
            request_mock.return_value = ret_val
            assert self.router.post_something_publicly() == ret_val
            assert request_mock.called

        finally:
            self.router.verify_codes = True
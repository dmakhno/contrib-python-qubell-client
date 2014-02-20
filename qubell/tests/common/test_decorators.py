import unittest2

from qubell.api.private.common import Entity, fetched
from qubell.api.tools import cachedproperty


# noinspection PyUnresolvedReferences
# noinspection PyProtectedMember
class CachedPropertyTests(unittest2.TestCase):
    class DummyObject(Entity):
        @fetched
        def do_something(self):
            pass

        @property
        @fetched
        def get_something(self):
            return "turum-burum"

        cache_source = ["a", "b", "c"]

        @cachedproperty
        def keep_something(self):
            return self.cache_source

    def setUp(self):
        self.dummy = CachedPropertyTests.DummyObject(auto_fetch=False)

    def test_cache(self):
        cache = self.dummy.keep_something
        assert cache == self.dummy._keep_something_cache

    def test_cache_update(self):
        new_source = "abcd"
        self.dummy.cache_source = new_source
        nowhere = self.dummy.keep_something
        assert new_source == self.dummy._keep_something_cache

    def test_cache_empty_on_start_with_zerocachemixin(self):
        assert not self.dummy._keep_something_cache

    def test_fetche_get_is_called_once(self):
        assert False
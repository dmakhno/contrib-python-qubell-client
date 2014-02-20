# Copyright (c) 2013 Qubell Inc., http://qubell.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from qubell.api.tools import is_bson_id, ZeroCacheMixin

from qubell.api.private import exceptions
from qubell import deprecated

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__version__ = ""
__email__ = "vkhomenko@qubell.com"


class EntityList(object):
    """ Class to store qubell objects information (Instances, Applications, etc)
    Gives convenient way for searching and manipulating objects
    """

    def __init__(self):
        self.object_list = []
        self._generate_object_list()

    def __iter__(self):
        return iter(self.object_list)

    def __len__(self):
        return len(self.object_list)

    def __repr__(self):
        return str(self.object_list)

    def __getitem__(self, item):
        # TODO: Guess item is ID or name
        found = [x for x in self.object_list if (is_bson_id(item) and x.id == item) or x.name == item]
        if len(found) > 1:
            raise exceptions.ExistsError("There are more than one '{1}' in {0}".format(self.__class__.__name__, item))
        if len(found) is 0:
            raise exceptions.NotFoundError("None of '{1}' in {0}".format(self.__class__.__name__, item))
        return found[-1]

    def __contains__(self, item):
        if isinstance(item,str):
            if is_bson_id(item):
                return item in [item.id for item in self.object_list]
            else:
                return item in [item.name for item in self.object_list]
        return item.id in [item.id for item in self.object_list]

    #todo: this must be immutable list
    @deprecated
    def add(self, item):
        self.object_list.append(item)

    #todo: this must be immutable list
    @deprecated
    def remove(self, item):
        self.object_list.remove(item)

    def _generate_object_list(self):
        raise AssertionError("'_generate_object_list' method should be implemented in subclasses")

#todo: what does this object do?
class QubellEntityList(EntityList):
    def __init__(self, organization):
        self.organization = organization
        self.auth = self.organization.auth
        self.organizationId = self.organization.organizationId
        EntityList.__init__(self)


class Entity(ZeroCacheMixin):
    def __init__(self, auto_fetch):
        """
        Initialize entity
        :param auto_fetch: indicates, whether item should be fetched on creation
        """
        self.raw_json = None
        self.fetched = False
        if auto_fetch: self.fetch()

    def fetch(self):
        """
        Gets the item using id, and marks as fetched.
        """
        self.fetched = True

def fetched(f):
    """
    If method marked with this decorator, the entity will be fetched if is not.
    :return: route
    """

    def wrapper(*args, **kwargs):
        self = args[0]
        if not self.fetched: self.get()
        return f(*args, **kwargs)

    return wrapper



@deprecated
class Auth(object):
    def __init__(self, user, password, tenant):
        self.user = user
        self.password = password
        self.tenant = tenant

        # TODO: parse tenant to generate api url
        self.api = tenant

Context = Auth

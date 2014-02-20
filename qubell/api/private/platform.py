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
import warnings

from qubell.api.private.organization import Organization, OrganizationList
from qubell.api.provider.router import Router
from qubell import deprecated

#todo: some people may use this object for authentication, need to move this to proper place
from qubell.api.private.common import Auth

#todo: create mimic for Context...
from qubell.api.tools import cachedproperty

Auth = Auth # Auth usage, to be sure won't be removed from imports

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"


class QubellPlatform(object):
    def __init__(self, router=None):
        self.router = router

    @staticmethod
    def connect(tenant, user, password):

        router = Router(tenant)
        router.connect(user, password)

        #todo: remove auth mimics when routes are used everywhere
        router.tenant = tenant
        router.user = user
        router.password = password
        return QubellPlatform(router=router, auth=router)

    @deprecated
    def authenticate(self):
        self.router.connect(self.auth.user, self.auth.password)
        #todo: remove following, left for compatibility
        self.auth.cookies = self.router._cookies
        return True

    def create_organization(self, name):
        return Organization.create(name, self.router)

    def get_organization(self, id):
        org = Organization(id=id, router=self.router)
        self._organizations_cache.append(org)
        return org

    def get_or_create_organization(self, id=None, name=None):
        """ Smart object. Will create organization, modify or pick one"""
        assert id or name
        name = name or 'generated-org-name'
        if id: return self.get_organization(id)
        if name:
            #if cached, no need to get all
            if name in self._organizations_cache or name in self.organizations:
                return self._organizations_cache[name]
            else:
                return self.create_organization(name)

    #alias
    organization = get_or_create_organization

    def organizations_json(self): return self.router.get_organizations().json()

    @cachedproperty
    def organizations(self):
        return OrganizationList(self.organizations_json(), self.router)

    def restore(self, config):
        for org in config.pop('organizations', []):
            restored_org = self.get_or_create_organization(id=org.get('id'), name=org.get('name'))
            restored_org.restore(org)
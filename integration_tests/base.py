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
import unittest
import os
import logging as log

from qubell.api.private.platform import QubellPlatform
from qubell.api.private.common import Auth

from qubell.api.private.manifest import Manifest
from qubell.api.private.testing.setup_once import SetupOnce
from qubell.api.private.service import COBALT_SECURE_STORE_TYPE, WORKFLOW_SERVICE_TYPE, SHARED_INSTANCE_CATALOG_TYPE

# this is required for used imports
# noinspection PyUnresolvedReferences
from qubell.api.testing import eventually, attr

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

parameters = {
    'organization': os.getenv('QUBELL_ORGANIZATION', "selfcheck_organization_name"),
    'user': os.environ['QUBELL_USER'],
    'pass': os.environ['QUBELL_PASSWORD'],
    'tenant': os.environ['QUBELL_TENANT'],
    'provider_name': os.getenv('PROVIDER_NAME', "selfcheck_provider_name"),
    'provider_type': os.environ.get('PROVIDER_TYPE', 'aws-ec2'),
    'provider_identity': os.environ.get('PROVIDER_IDENTITY', 'No PROVIDER_IDENTITY'),
    'provider_credential': os.environ.get('PROVIDER_CREDENTIAL', 'PROVIDER_CREDENTIAL'),
    'provider_region': os.environ.get('PROVIDER_REGION', 'us-east-1'),
}
zone = os.environ.get('QUBELL_ZONE')

class BaseTestCase(SetupOnce, unittest.TestCase):
    parameters=parameters
    ## TODO: Main preparation should be here
    """ Here we prepare global env. (load config, etc)
    """
    # Set default manifest for app creation
    manifest = Manifest(file=os.path.join(os.path.dirname(__file__), './default.yml'), name='BaseTestManifest')
    platform = QubellPlatform.connect(user=parameters['user'], password=parameters['pass'], tenant=parameters['tenant'])

    def setup_once(self):
    # Initialize organization
        if os.getenv("QUBELL_IT_LOCAL"):
            self.parameters['organization'] = self.__class__.__name__
        self.organization = self.platform.organization(name=self.parameters['organization'])

        if zone:
            z = [x for x in self.organization.list_zones() if x['name'] == zone]
            if z:
                self.organization.zoneId = z[0]['id']


    # Initialize environment
        if zone:
            self.environment = self.organization.environment(name='default', zone=self.organization.zoneId)
            self.environment.set_backend(self.organization.zoneId)
        else:
            self.environment = self.organization.get_environment(name='default')
        self.environment.clean()
        self.shared_service = self.organization.service(name='BaseTestSharedService', type=SHARED_INSTANCE_CATALOG_TYPE, environment=self.environment, parameters={'configuration.shared-instances':{}})
        self.wf_service = self.organization.service(name='Default workflow service', type=WORKFLOW_SERVICE_TYPE, environment=self.environment)
        self.key_service = self.organization.service(name='Default credentials service', type=COBALT_SECURE_STORE_TYPE, environment=self.environment)
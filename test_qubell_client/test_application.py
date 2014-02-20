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

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__version__ = "1.0.1"
__email__ = "vkhomenko@qubell.com"

import os

from base import BaseTestCase
from qubell.api.private.manifest import Manifest


class ApplicationClassTest(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(ApplicationClassTest, cls).setUpClass()
        cls.org = cls.organization
        cls.app = cls.org.create_application(manifest=cls.manifest, name='Self-ApplicationClassTest')

    @classmethod
    def tearDownClass(cls):
        cls.app.delete()
        super(ApplicationClassTest, cls).tearDownClass()


    def test_applications_sugar(self):
        org = self.org
        app = self.app

        self.assertTrue(app in org.applications)
        self.assertEqual(org.applications['Self-ApplicationClassTest'], app)
        self.assertEqual(org.applications['Self-ApplicationClassTest'].name, app.name)
        self.assertEqual(org.applications['Self-ApplicationClassTest'].id, app.id)

        for x in org.applications:
            self.assertTrue(x.name)

    def test_application_create_method(self):
        # Check we can create applications
        my_app = self.org.create_application(manifest=self.manifest, name='Self-test_application_create_method')
        self.assertTrue(my_app.name)
        self.assertTrue(my_app in self.org.applications)

        # check we cannot create already created application
        new_app = self.org.get_application(id=my_app.id).create_legacy(name='sdf', manifest=self.manifest)
        self.assertEqual(my_app, new_app)

        self.assertTrue(my_app.delete())


    def test_get_or_create_application_method(self):
        app = self.app
        org = self.org
        # Get tests
        self.assertEqual(app, org.get_or_create_application(id=app.id))
        self.assertEqual(app, org.get_or_create_application(name=app.name))

        # Create tests
        new_app = org.get_or_create_application(name='Self-get_or_create_application-test', manifest=app.manifest)
        self.assertTrue(new_app in org.applications)
        self.assertTrue(new_app.id)
        self.assertEqual(new_app.name, 'Self-get_or_create_application-test')
        self.assertTrue(new_app.delete())


    def test_smart_application_method(self):
        org = self.org
        app = self.app
        base_app = org.get_or_create_application(name='Self-smart_application_method', manifest=app.manifest)

        # Get application
        self.assertEqual(base_app, org.application(name='Self-smart_application_method'))
        self.assertEqual(base_app, org.application(id=base_app.id))
        self.assertEqual(base_app, org.application(id=base_app.id, name='Self-smart_application_method'))

        # Modify application
        new_name_app = org.application(id=base_app.id, name='Self-smart_application_method-new-name')
        self.assertEqual(base_app, new_name_app)
        self.assertEqual('Self-smart_application_method-new-name', new_name_app.name)

        new_manifest = Manifest(file=os.path.join(os.path.dirname(__file__), 'default.yml'), name='Updated')
        new_manifest.patch('application/configuration/in.app_input', 'NEW NEW')
        new_name_app = org.application(id=base_app.id, manifest=new_manifest)
        self.assertEqual(base_app, new_name_app)
        self.assertTrue('NEW NEW' in base_app.get_manifest()['manifest'])

        # Create application
        new_application = org.application(name='Self-smart_application_method-create', manifest=app.manifest)
        self.assertEqual('Self-smart_application_method-create', new_application.name)
        self.assertTrue(new_application in org.applications)
        self.assertTrue(new_application.delete())

        # Clean
        self.assertTrue(base_app.delete())

"""
    def test_revision_create(self):
        app = self.org.application(manifest=self.manifest, name='test-revision-create')

        instance = app.launch(destroyInterval=600000)
        self.assertTrue(instance.ready())

        revision = app.create_revision(name='test-revision-create', instance=instance)

        self.assertTrue(revision)
        self.assertTrue(app.clean())
        self.assertTrue(instance.destroyed())
        self.assertTrue(app.delete())
"""
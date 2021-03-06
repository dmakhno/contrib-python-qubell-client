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

from qubellclient.tests import base
from qubellclient.private.manifest import Manifest
from qubellclient.tests.base import attr

class HierappReconfiguration(base.BaseTestCasePrivate):

    @classmethod
    def setUpClass(cls):
        super(HierappReconfiguration, cls).setUpClass()
        cls.parent_app = cls.organization.application(name="%s-reconfiguration-hierapp-parent" % cls.prefix, manifest=cls.manifest)
        cls.child_app = cls.organization.application(name="%s-reconfiguration-hierapp-child" % cls.prefix, manifest=cls.manifest)
        cls.new_child_app = cls.organization.application(name="%s-reconfiguration-hierapp-child-new" % cls.prefix, manifest=cls.manifest)

        # Prepare child
        cmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "hier-child.one.yml"))
        cls.child_app.upload(cmnf)


        # Prepare shared child
        cls.child_instance = cls.child_app.launch(destroyInterval=300000)
        assert cls.child_instance.ready()
        cls.child_rev = cls.child_app.revisionCreate(name='tests-reconf-hierapp-shared', instance=cls.child_instance)
        revision_id = cls.child_rev.revisionId.split('-')[0]
        instance_id = cls.child_instance.instanceId

        cls.child_service = cls.organization.service(name='shared-test', type='builtin:shared_instances_catalog', parameters='%s: %s' % (revision_id, instance_id))
        cls.environment.serviceAdd(cls.child_service)

        # Prepare new_child
        cmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "hier-child.two.yml"))
        cls.new_child_app.upload(cmnf)


    @classmethod
    def tearDownClass(cls):
        super(HierappReconfiguration, cls).tearDownClass()
        cls.environment.serviceRemove(cls.child_service)
        cls.child_service.delete()
        cls.child_rev.delete()

        cls.child_instance.delete()
        assert cls.child_instance.destroyed()

        #cls.parent_app.clean()
        #cls.child_app.clean()
        #cls.new_child_app.clean()

        cls.parent_app.delete()
        cls.child_app.delete()
        cls.new_child_app.delete()


    def test_new_child_application(self):
        """ Launch hierarchical app with child as not shared instance. Change __locator and check new child launched
        """

        # Run parent with child
        pmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "hier-parent.yml"))
        pmnf.patch('application/components/child/configuration/__locator.application-id', self.child_app.applicationId)

        self.parent_app.upload(pmnf)
        parent_instance = self.parent_app.launch(destroyInterval=300000)
        self.assertTrue(parent_instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')


        # Run parent with new_child
        pmnf.patch('application/components/child/configuration/__locator.application-id', self.new_child_app.applicationId)
        self.parent_app.upload(pmnf)
        new_parent_instance = self.parent_app.launch(destroyInterval=300000)
        self.assertTrue(new_parent_instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(new_parent_instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        self.assertEqual(new_parent_instance.submodules[0]['status'], 'Running')

        new_rev = self.parent_app.revisionCreate(name='tests-new-child', instance=new_parent_instance)

        # Reconfigure old parent with new revision
        parent_instance.reconfigure(revisionId=new_rev.revisionId)

        # Check results
        self.assertTrue(new_parent_instance.ready(), "Instance failed to reconfigure")
        self.assertNotEqual(parent_instance.submodules[0]['id'], new_parent_instance.submodules[0]['id'])
        self.assertEqual("Child2 welcomes you", new_parent_instance.returnValues['parent_out.child_out'])

        self.assertTrue(new_rev.delete)

        self.assertTrue(parent_instance.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
        self.assertTrue(new_parent_instance.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(new_parent_instance.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))



    @attr('skip') # TODO: Bug here. need investigation
    def test_switch_child_shared_standalone_and_back(self):
        """ Launch hierarchical app with non shared instance. Change child to shared, check. Switch back.
        """

        # Run parent with NON shared child
        pmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "hier-parent.yml"))
        pmnf.patch('application/components/child/configuration/__locator.application-id', self.child_app.applicationId)
        self.parent_app.upload(pmnf)

        parent_instance = self.parent_app.launch(destroyInterval=300000)
        self.assertTrue(parent_instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        non_shared_rev = self.parent_app.revisionCreate(name='non-shared-child', instance=parent_instance)

        # Ensure we use non shared instance
        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')
        self.assertNotEqual(parent_instance.submodules[0]['id'], self.child_instance.instanceId)

        # Reconfigure parent to use shared child
        parameters = {self.child_app.name: {'revisionId': self.child_rev.revisionId}}
        parent_instance.reconfigure(parameters=parameters)

        import time
        time.sleep(10)
        # Check we use shared instance
        self.assertTrue(parent_instance.ready(), "Instance failed to reconfigure")
        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')
        self.assertEqual(parent_instance.submodules[0]['id'], self.child_instance.instanceId)
        print parent_instance.submodules


        # Switch back to non shared instance
        parent_instance.reconfigure(revisionId=non_shared_rev.revisionId)

        time.sleep(10)

        # Check we use shared instance again
        self.assertTrue(parent_instance.ready(), "Instance failed to reconfigure")
        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')
        self.assertNotEqual(parent_instance.submodules[0]['id'], self.child_instance.instanceId)

        self.assertTrue(parent_instance.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))

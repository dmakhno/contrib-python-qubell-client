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
__email__ = "vkhomenko@qubell.com"

import logging as log

import requests
import simplejson as json

from qubell.api.private.manifest import Manifest
from qubell.api.private.instance import Instance
from qubell.api.private import exceptions


class Instances:
    def __init__(self, organization):
        self.current = 0
        self.organization = organization
        self.auth = self.organization.auth
        self.organizationId = self.organization.organizationId
        self.object_list = []
        self.__generate_instance_list()

    def __iter__(self):
        i = self.current
        while i<len(self.object_list):
            yield self.object_list[i]
            i+=1

    def __len__(self):
        return len(self.object_list)

    def __repr__(self):
        return str(self.object_list)

    def __getitem__(self, item):
        # TODO: Guess item is ID or name
        found = [x for x in self.object_list if x.name == item]
        if len(found)==1:
            return found[0]
        raise

    def __contains__(self, item):
        return item in self.object_list

    def add(self, instance):
        self.object_list.append(instance)

    def remove(self, instance):
        del self.object_list[instance]

    def __list_applications(self):
        url = self.auth.api+'/organizations/'+self.organizationId+'/applications.json'
        resp = requests.get(url, cookies=self.auth.cookies, data="{}", verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to get applications list, got error: %s' % resp.text)

    def __generate_instance_list(self):
        from qubell.api.private.application import Application
        for app in self.__list_applications():
            url = self.auth.api+'/organizations/'+self.organizationId+'/applications/'+app['id']+'.json'
            resp = requests.get(url, cookies=self.auth.cookies, data="{}", verify=False)
            log.debug(resp.text)
            if resp.status_code == 200:
                instances = resp.json()['instances']
                instances_alive = [ins for ins in instances if ins['status'] not in ['Destroyed', 'Destroying']]
                app_obj = Application(self.auth, self.organization, app['id'])

                for ins in instances_alive:
                    self.object_list.append(Instance(self.auth, app_obj, id=ins['id']))
            else:
                raise exceptions.ApiError('Unable to get instances by url %s, got error: %s' % (url, resp.text))





class Organization(object):

    def __init__(self, auth, id):
        self.applications = []
        self.environments = []
        self.services = []
        self.providers = []
        self.zones = []

        self.organizationId = id
        self.auth = auth
        self.zone = self.get_default_zone()
        self.defaultEnvironment = self.get_default_environment()

        my = self.json()
        self.name = my['name']
        self.instance_list = []
        self.instances = Instances(self)


    def json(self):
        url = self.auth.api+'/organizations.json'
        resp = requests.get(url, cookies=self.auth.cookies, verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            org = [x for x in resp.json() if x['id'] == self.organizationId]
            if len(org)>0:
                return org[0]
            return resp.json()
        raise exceptions.ApiError('Unable to get organization by id %s, got error: %s' % (self.organizationId, resp.text))

    def restore(self, config):
        for instance in config.pop('instances', []):
            launched = self.get_or_launch_instance(id=instance.pop('id', None), name=instance.pop('name'), **instance)
            assert launched.ready()
        for serv in config.pop('services',[]):
            self.get_or_create_service(id=serv.pop('id', None), name=serv.pop('name'), type=serv.pop('type', None))
        for prov in config.get('providers', []):
            self.get_or_create_provider(id=prov.pop('id', None), name=prov.pop('name'), parameters=prov)
        for env in config.pop('environments',[]):
            restored_env = self.get_or_create_environment(id=env.pop('id', None), name=env.pop('name', 'default'),zone=env.pop('zone', None), default=env.pop('default', False))
            restored_env.clean()
            restored_env.restore(env)
        for app in config.pop('applications'):
            mnf = app.pop('manifest', None)
            restored_app = self.application(id=app.pop('id', None), manifest=Manifest(**mnf), name=app.pop('name'))
            restored_app.restore(app)

### APPLICATION
    def create_application(self, name, manifest):
        log.info("Creating application: %s" % name)
        url = self.auth.api+'/organizations/'+self.organizationId+'/applications.json'

        resp = requests.post(url, files={'path': manifest.content}, data={'manifestSource': 'upload', 'name': name}, verify=False, cookies=self.auth.cookies)
        log.debug(resp.text)
        if resp.status_code == 200:
            app = self.get_application(resp.json()['id'])
            app.manifest = manifest
            return app
        raise exceptions.ApiError('Unable to create application %s, got error: %s' % (name, resp.text))

    def get_application(self, id):
        log.info("Picking application: %s" % id)
        from qubell.api.private.application import Application
        app = Application(auth=self.auth, organization=self, id=id)
        self.applications.append(app)
        return app

    def list_applications(self):
        url = self.auth.api+'/organizations/'+self.organizationId+'/applications.json'
        resp = requests.get(url, cookies=self.auth.cookies, data="{}", verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to get applications list, got error: %s' % resp.text)

    def delete_application(self, id):
        app = self.get_application(id)
        self.applications.remove(app)
        return app.delete()

    def get_or_create_application(self, id=None, manifest=None, name=None):
        """ Will get app by id or create application with parameters """
        if name:
            appz = [app for app in self.list_applications() if app['name'] == name]
            # app found by name
            if len(appz):
                app = self.get_application(appz[0]['id']) # pick first
                if manifest:
                    app.upload(manifest)
                    return self.get_application(app.applicationId)
                else:
                    return app
            else:
                return self.create_application(name, manifest)
        else:
            name = 'generated-app-name'
            if id:
                return self.get_application(id)
            else:
                return self.create_application(name, manifest)

    def application(self, id=None, manifest=None, name=None):
        """ Creates, picks or modify application
        """
        if id:
            app = self.get_application()
            if name: app.update(name=name)
            if manifest:
                app.upload(manifest=manifest)
        elif name:
            app = self.get_or_create_application(id=id, manifest=manifest, name=name)
            if manifest: app.upload(manifest=manifest)
        return app


# INSTANCE

    def create_instance(self, application, revision=None, environment=None, name=None, parameters={}):
        """ Launches instance in application and returns Instance object.
        """
        if not application:
            raise exceptions.NotEnoughParams('Application not set')
        from qubell.api.private.instance import Instance
        instance = Instance(auth=self.auth, application=application)
        instance.create(revision=revision, environment=environment, name=name, parameters=parameters)
        self.instances.add(instance)
        return instance

    def get_instance(self, application=None, id=None, name=None):
        """ Get instance object by name or id.
        If application set, search within the application.
        """

        if application:
            instances = [x for x in self.instances if x.applicationId == application.applicationId]
        else:
            instances = self.instances

        if id:
            instance = [x for x in instances if x.id==id]
        elif name:
            instance = [x for x in instances if x.name==name]
        else:
            raise exceptions.NotEnoughParams('No name nor id given. Unable to get instance')

        if len(instance) == 1:
            return instance[0]
        elif len(instance) > 1:
            log.warning('Found several instances with name %s. Picking first' % name)
            return instance[0]
        raise exceptions.NotFoundError('Unable to get instance or too many found')

    def list_instances_json(self, application=None):
        """ Get list of instances in json format converted to list
        """
        if application: # Return list of instances in application
            url = self.auth.api+'/organizations/'+self.organizationId+'/applications/'+application.applicationId+'.json'
            resp = requests.get(url, cookies=self.auth.cookies, data="{}", verify=False)
            log.debug(resp.text)
            if resp.status_code == 200:
                instances = resp.json()['instances']
                return [ins for ins in instances if ins['status'] not in ['Destroyed', 'Destroying']]
            raise exceptions.ApiError('Unable to get application by url %s\n, got error: %s' % (url, resp.text))
        else:  # Return all instances in organization
            instances = []
            for app in self.list_applications():
                found_app = self.get_application(app['id'])
                instances.extend(self.list_instances(found_app))
            return instances


    def delete_instance(self, id):
        instance = self.get_instance(id)
        self.instances.remove(instance)
        return instance.delete()

    def get_or_launch_instance(self, id=None, application=None, name=None, **kwargs):
        """ Get instance by id or name.
        If not found: create with given application (name and params are optional)
        """
        if id:
            return self.get_instance(id=id)
        elif name:
            try:
                instance = self.get_instance(name=name)
            except exceptions.NotFoundError:
                instance = self.create_instance(application=application, name=name, **kwargs)
            return instance
        elif application:
            return self.create_instance(application=application, **kwargs)
        raise exceptions.NotEnoughParams('Not enough parameters')

    def instance(self, application=None, id=None, name=None, revision=None, environment=None,  parameters={}):
        """ Smart method. It does everything, to return Instance with given parameters within the application.
        If instance found running and given parameters are actual: return it.
        If instance found, but parameters differs - reconfigure instance with new parameters.
        If instance not found: launch instance with given parameters.
        Return: Instance object.
        """

        modify = False
        found = False

        # Try to find instance by name or id
        if name and id:
            found = self.get_instance(application=application, id=id)
            if not found.name == name:
                modify = True
        elif id:
            found = self.get_instance(application=application, id=id)
            name = found.name

        elif name:
            try:
                found = self.get_instance(application=application, name=name)
                id = found.instanceId
            except exceptions.NotFoundError:
                pass

        # If found - compare parameters
        # TODO:
        """
        if found:
            if revision and not revision == found.revision:
                modify = True
            if environment and not environment == found.environment:
                modify = True
            if parameters and not parameters == found.parameters:
                modify = True
        """

        # We need to reconfigure instance
        if found and modify:
            found.reconfigure(revision=revision, environment=environment, name=name, parameters=parameters)

        if not found:
            created = self.create_instance(application=application, revision=revision, environment=environment, name=name, parameters=parameters)

        return found or created


### SERVICE
    def create_service(self, name, type, parameters={}, zone=None):
        log.info("Creating service: %s" % name)
        if not zone:
            zone = self.zone.zoneId
        data = {'name': name,
                'typeId': type,
                'zoneId': zone,
                'parameters': parameters}

        url = self.auth.api+'/organizations/'+self.organizationId+'/services.json'
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, cookies=self.auth.cookies, data=json.dumps(data), verify=False, headers=headers)
        log.debug(resp.request.body)
        log.debug(resp.text)

        if resp.status_code == 200:
            return self.get_service(resp.json()['id'])
        raise exceptions.ApiError('Unable to create service %s, got error: %s' % (name, resp.text))

    def create_keystore_service(self, name='generated-keystore', parameters={}, zone=None):
        return self.create_service(name=name, type='builtin:cobalt_secure_store', parameters=parameters, zone=zone)

    def create_workflow_service(self, name='generated-workflow', policies={}, zone=None):
        parameters = {'configuration.policies': json.dumps(policies)}
        return self.create_service(name=name, type='builtin:workflow_service', parameters=parameters, zone=zone)

    def create_shared_service(self, name='generated-shared', instances={}, zone=None):
        parameters = {'configuration.shared-instances': json.dumps(instances)}
        return self.create_service(name=name, type='builtin:shared_instances_catalog', parameters=parameters, zone=zone)

    def get_service(self, id):
        log.info("Picking service: %s" % id)
        from qubell.api.private.service import Service
        serv = Service(self.auth, organization=self, id=id)
        self.services.append(serv)
        return serv

    def list_services(self):
        url = self.auth.api+'/organizations/'+self.organizationId+'/services.json'
        resp = requests.get(url, cookies=self.auth.cookies, verify=False)
        log.debug(resp.request.body)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to get services list, got error: %s' % resp.text)

    def delete_service(self, id):
        srv = self.get_service(id)
        return srv.delete()

    def get_or_create_service(self, id=None, name=None, type=None, parameters={}, zone=None):
        """ Get by name or create service with given parameters"""
        if name:
            servs = [srv for srv in self.list_services() if srv['name'] == name]
            # service found by name
            if len(servs):
                return self.get_service(servs[0]['id']) # pick first
            elif type:
                return self.create_service(name, type, parameters, zone)
        else:
            name = 'generated-service'
            if id:
                return self.get_service(id)
            elif type:
                return self.create_service(name, type, parameters, zone)
        raise exceptions.NotFoundError('Service not found or not enough parameters to create service: %s' % name)

    def service(self, id=None, name=None, type=None, parameters={}, zone=None):
        """ Get, modify or create service
        """
        # TODO: modify service if differs
        return self.get_or_create_service(id=id, name=name, type=type, parameters=parameters, zone=zone)

### ENVIRONMENT
    def create_environment(self, name, default=False, zone=None):
        log.info("Creating environment: %s" % name)
        if not zone:
            zone = self.zone.zoneId
        data = {'isDefault': default,
                'name': name,
                'backend': zone,
                'organizationId': self.organizationId}

        url = self.auth.api+'/organizations/'+self.organizationId+'/environments.json'
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, cookies=self.auth.cookies, data=json.dumps(data), verify=False, headers=headers)
        log.debug(resp.request.body)
        log.debug(resp.text)

        if resp.status_code == 200:
            return self.get_environment(resp.json()['id'])
        raise exceptions.ApiError('Unable to create environment %s, got error: %s' % (name, resp.text))

    def list_environments(self):
        url = self.auth.api+'/organizations/'+self.organizationId+'/environments.json'
        resp = requests.get(url, cookies=self.auth.cookies, verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to get environments list, got error: %s' % resp.text)

    def get_environment(self, id):
        from qubell.api.private.environment import Environment
        env = Environment(self.auth, self, id)
        self.environments.append(env)
        return env

    def delete_environment(self, id):
        env = self.get_environment(id)
        self.environments.remove(env)
        return env.delete()

    def get_or_create_environment(self, id=None, name=None, zone=None, default=False):
        """ Get env by name or create with parameters"""
        if name:
            envs = [env for env in self.list_environments() if env['name'] == name]
            # environment found by name
            if len(envs):
                return self.get_environment(envs[0]['id']) # pick first
            else:
                return self.create_environment(name=name, zone=zone, default=default)
        else:
            name = 'generated-env'
            if id:
                return self.get_environment(id)
            else:
                return self.create_environment(name=name, zone=zone, default=default)

    def environment(self, id=None, name=None, zone=None, default=False):
        return self.get_or_create_environment(id=id, name=name, zone=zone, default=default)

    def get_default_environment(self):
        envs = self.list_environments()
        defaults = [x for x in envs if x['isDefault']==True]
        if len(defaults):
            envId = defaults[0]['id'] # If we had several default environments, pick first
            return self.get_environment(id=envId)
        raise exceptions.NotFoundError('Unable to get default environment')

    def set_default_environment(self, id):
        url = self.auth.api+'/organizations/'+self.organizationId+'/defaultEnvironment.json'
        headers = {'Content-Type': 'application/json'}
        data = json.dumps({'environmentId': id})
        resp = requests.put(url, cookies=self.auth.cookies, headers=headers, data=data, verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to set default environment, got error: %s' % resp.text)

### PROVIDER
    def create_provider(self, name, parameters):
        log.info("Creating provider: %s" % name)
        parameters['name'] = name

        url = self.auth.api+'/organizations/'+self.organizationId+'/providers.json'
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, cookies=self.auth.cookies, data=json.dumps(parameters), verify=False, headers=headers)
        log.debug(resp.text)

        if resp.status_code == 200:
            return self.get_provider(resp.json()['id'])
        raise exceptions.ApiError('Unable to create provider %s, got error: %s' % (name, resp.text))

    def list_providers(self):
        url = self.auth.api+'/organizations/'+self.organizationId+'/providers.json'
        resp = requests.get(url, cookies=self.auth.cookies, verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to get providers list, got error: %s' % resp.text)

    def get_provider(self, id):
        from qubell.api.private.provider import Provider
        prov = Provider(self.auth, organization=self, id=id)
        self.providers.append(prov)
        return prov

    def delete_provider(self, id):
        prov = self.get_provider(id)
        self.providers.remove(prov)
        return prov.delete()

    def get_or_create_provider(self,id=None, name=None, parameters=None):


        """ Smart object. Will create provider or pick one, if exists"""
        if name:
            provs = [prov for prov in self.list_providers() if prov['name'] == name]
            # provider found by name
            if len(provs):
                return self.get_provider(provs[0]['id']) # pick first
            elif parameters:
                return self.create_provider(name=name, parameters=parameters)
        else:
            name = 'generated-provider'
            if id:
                return self.get_provider(id)
            elif parameters:
                return self.create_provider(name=name, parameters=parameters)
        raise exceptions.NotFoundError('Provider not found or not enough parameters to create provider: %s' % name)

    def provider(self, id=None, name=None, parameters=None):
        """ Get , create or modify provider
        """
        return self.get_or_create_provider(id=id, name=name, parameters=parameters)

### ZONES

    def list_zones(self):
        url = self.auth.api+'/organizations/'+self.organizationId+'/zones.json'
        resp = requests.get(url, cookies=self.auth.cookies, verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to get zones list, got error: %s' % resp.text)

    def get_zone(self, id):
        from qubell.api.private.zone import Zone
        zone = Zone(self.auth, organization=self, id=id)
        self.zones.append(zone)
        return zone

    def get_default_zone(self):
    # Zones(backends) are factor we can't controll. So, get them.
        backends = self.json()['backends']
        zones = [bk for bk in backends if bk['isDefault']==True]
        if len(zones):
            zoneId = zones[0]['id']
            return self.get_zone(id=zoneId)
        raise exceptions.NotFoundError('Unable to get default zone')

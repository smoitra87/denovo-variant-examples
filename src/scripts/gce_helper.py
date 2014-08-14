#!/usr/bin/env python
#
# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.

import argparse
import logging
import re
import copy

import httplib2
from apiclient.discovery import build
from oauth2client import tools
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow

from utils import confirm
from utils import constants


class GCEHelper(object):

    """ Helper class for gce instances """

    new_disk_json = {
        "zone":
         "{GCE_URL}{PROJECT_ID}/zones/{DEFAULT_ZONE}".format(**constants),
        "name": "{device_name}",
        "type": "{GCE_URL}{PROJECT_ID}/zones/{DEFAULT_ZONE}/diskTypes/pd-standard".format(**constants),
        "sourceSnapshot":
        "{GCE_URL}{PROJECT_ID}/global/snapshots/{SNAPSHOT_NAME}".format(**constants),
    }

    new_instance_json = {
        "name": "{instance_name}",
        "disks":
        [
         {"type": "PERSISTENT",
          "boot": True,
          "mode": "READ_WRITE",
          "deviceName": "{device_name}",
          "zone":
          "{GCE_URL}{PROJECT_ID}/zones/{DEFAULT_ZONE}".format(**constants),
          "source":
          "{GCE_URL}{PROJECT_ID}/zones/{DEFAULT_ZONE}/disks/{device_name}",
          "autoDelete": True}],
        "networkInterfaces":
        [
         {"network":
          "{GCE_URL}{PROJECT_ID}/global/networks/default".format(**constants),
          "accessConfigs":
          [{"name": "External NAT", "type": "ONE_TO_ONE_NAT"}]}], "metadata":
        {"items": []}, "tags": {"items": ["http-server", "https-server"]},
        "zone":
        "{GCE_URL}{PROJECT_ID}/zones/{DEFAULT_ZONE}".format(**constants),
        "canIpForward": False, "scheduling":
        {"automaticRestart": True, "onHostMaintenance": "MIGRATE"},
        "machineType":
        "{GCE_URL}{PROJECT_ID}/zones/{DEFAULT_ZONE}/machineTypes/n1-standard-{num_cores}",
        "serviceAccounts":
        [
         {"email": "default", "scopes":
          ["https://www.googleapis.com/auth/devstorage.read_only"]}]}

    def __init__(self):
        self.gce_service = None
        self.auth_http = None
        self._build_service()
        self.logger = logging.getLogger('gce_helper')
        self.logger.setLevel(logging.INFO)
        self.nameToIPMap = {}
        self.IPtoNameMap = {}
        self._updateNameToIPMap()

    def _build_service(self):
        logging.basicConfig(level=logging.WARNING)

        parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            parents=[tools.argparser])

        # Parse the command-line flags.
        flags = parser.parse_args([])

        # Perform OAuth 2.0 authorization.
        flow = flow_from_clientsecrets(
            constants["CLIENT_SECRETS"],
            scope=constants["GCE_SCOPE"])
        storage = Storage(constants["OAUTH2_STORAGE"])
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage, flags)
        http = httplib2.Http()
        self.auth_http = credentials.authorize(http)

        # Build the service
        self.gce_service = build('compute', constants["API_VERSION"])

    def _list_instances(self):
        # List instances
        request = self.gce_service.instances(). list(
            project=constants["PROJECT_ID"],
            filter=None,
            zone=constants["DEFAULT_ZONE"])
        response = request.execute(http=self.auth_http)
        if response and 'items' in response:
            instances = response['items']
            for instance in instances:
                yield instance['name']

    def gce_list_denovo_instances(self) :
        """ Lists all the denovo instances """
        for inst in self._list_denovo_instances():
            print(inst)

    def gce_list_instances(self):
        """ Lists all the instances in my GCE """
        for inst in self._list_denovo_instances():
            print(inst)

    def _list_denovo_instances(self):
        for instance in self._list_instances():
            if 'denovo' in instance:
                yield instance

    def _create_instance(self, instance_json):
        """ Create a new instance from json """
        self.logger.info("Creating instance {:s}".format(instance_json["name"]))
        request = self.gce_service.instances().insert(
            project=constants["PROJECT_ID"],
            body=instance_json,
            zone=constants["DEFAULT_ZONE"])
        response = request.execute(http=self.auth_http)
        response = self._blocking_call(self.gce_service, self.auth_http,
                                        response)

    def _create_disk(self, disk_json):
        """ Create a new disk from json """
        self.logger.info("Creating disk {:s}".format(disk_json["name"]))
        request = self.gce_service.disks().insert(
            project=constants["PROJECT_ID"],
            body=disk_json,
            zone=constants["DEFAULT_ZONE"])
        response = request.execute(http=self.auth_http)
        response = self._blocking_call(self.gce_service, self.auth_http,
                                        response)

    def _create_instance_json(self, instance_name, device_name, num_cores):
        """ Creates a REST Json object to create a new instance"""
        instance_json = copy.deepcopy(GCEHelper.new_instance_json)
        instance_constants = copy.deepcopy(constants)
        instance_constants["instance_name"] = instance_name
        instance_constants["device_name"] = device_name
        instance_constants["num_cores"] = num_cores

        instance_json["name"] = instance_json["name"].format(
            **instance_constants)
        instance_json["disks"][0]["deviceName"] = \
            instance_json["disks"][0]["deviceName"].format(
            **instance_constants)
        instance_json["disks"][0]["source"] = \
            instance_json["disks"][0]["source"].format(
            **instance_constants)
        instance_json["machineType"] = instance_json["machineType"].format(
            **instance_constants)
        return instance_json

    def _create_disk_json(self, device_name):
        """ Creates a REST Json object to create a new disk"""
        disk_json = copy.deepcopy(GCEHelper.new_disk_json)
        disk_constants = copy.deepcopy(constants)
        disk_constants["device_name"] = device_name

        disk_json["name"] = disk_json["name"].format(**disk_constants)

        return disk_json

    def gce_create_denovo_instances(self, num_instances=1, num_cores=4):
        """ Create new denovo instances

        Keyword arguments:
        num_instances -- the number of instances (default 1)
        num_cores -- the number of cores per instance (default 4)
        """
        self.logger.info("Creating instances...")

        num_instances = int(num_instances)
        new_instance_start_number = self._get_max_denovo_number() + 1
        for instance_idx in xrange(new_instance_start_number,
                                   new_instance_start_number+num_instances):
            device_name = "denovo-{:d}".format(instance_idx)
            instance_name = "denovo-{:d}".format(instance_idx)
            self._create_disk(self._create_disk_json(device_name))
            self._create_instance(self._create_instance_json(
                instance_name, device_name, num_cores))

    def gce_delete_all_denovo_instances(self):
        """ Deletes all denovo instances """

        self.logger.info("Deleting all denovo instances...")
        if not confirm():
            return
        for instance_name in self._list_denovo_instances():
            self.delete_instance(instance_name)

    def gce_delete_instance(self, instance_name):
        """ Deletes a particular instance by name """

        self.logger.info("Deleting instance : {:s}...".format(instance_name))
        request = self.gce_service.instances().delete(
            project=constants["PROJECT_ID"],
            instance=instance_name,
            zone=constants["DEFAULT_ZONE"]
        )
        response = request.execute(http=self.auth_http)
        response = self._blocking_call(
            self.gce_service, self.auth_http, response)

    def _blocking_call(self, gce_service, auth_http, response):
        """Blocks until the operation status is done for the given operation."""

        status = response['status']
        while status != 'DONE' and response:
            operation_id = response['name']

            # Identify if this is a per-zone resource
            if 'zone' in response:
                zone_name = response['zone'].split('/')[-1]
                request = self.gce_service.zoneOperations().get(
                    project=constants["PROJECT_ID"],
                    operation=operation_id,
                    zone=zone_name)
            else:
                request = self.gce_service.globalOperations().get(
                    project=constants["PROJECT_ID"], operation=operation_id)

            response = request.execute(http=self.auth_http)
            if response:
                status = response['status']
        return response

    @staticmethod
    def _get_instance_number(instance_name):
        """ Get the number from an instance"""
        try:
            number = int(next(re.compile('\d+').finditer(
                instance_name)).group())
        except StopIteration:
            raise ValueError("Unknown instance type" + instance_name)
        return number

    def _get_max_denovo_number(self):
        """ Get the maximum number from the list of denovo instances"""
        try :
            return max(GCEHelper._get_instance_number(e) for e in
                   self._list_denovo_instances())
        except ValueError:
            return 0

    def _updateNameToIPMap(self):
        self.logger.info("Updating name to ip map")
        request = self.gce_service.instances(). list(
            project=constants["PROJECT_ID"],
            filter=None,
            zone=constants["DEFAULT_ZONE"])
        response = request.execute(http=self.auth_http)
        self.nameToIPMap, self.IPtoNameMap = {},{}
        if response and 'items' in response:
            instances = response['items']
            for instance in instances:
                if len(instance["networkInterfaces"]) > 1:
                    raise ValueError("Only one IP per instance expected")
                net_interface = instance["networkInterfaces"][0]
                if len(net_interface["accessConfigs"]) > 1:
                    raise ValueError("Only one IP per instance expected")
                access_config = net_interface["accessConfigs"][0]
                self.nameToIPMap[instance["name"]] = access_config["natIP"]
                self.IPtoNameMap[access_config["natIP"]] = instance["name"]

    def gce_list_name_ips(self):
        """ List all the name to ip maps """
        for  key, val in self.nameToIPMap.iteritems():
            print("{0}: {1}".format(key, val))

if __name__ == '__main__':
    helper = GCEHelper()
    helper.list_denovo_instances()
    helper._updateNameToIPMap()
    print(helper.nameToIPMap)

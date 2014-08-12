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
import os
import re
import copy

import httplib2
from apiclient.discovery import build
from oauth2client import tools
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow

constants = {
    "DEFAULT_ZONE": 'us-central2-b',
    "API_VERSION": 'v1',
    "PROJECT_ID": 'de-novo-experiment',
    "CLIENT_SECRETS": '/usr/local/google/home/smoitra/Downloads/client_secrets.json',
    "OAUTH2_STORAGE": os.path.expanduser(
        '~/.store/genomics_denovo_caller/oauth2.dat'),
    "GCE_SCOPE": 'https://www.googleapis.com/auth/compute',
    "SNAPSHOT_NAME": "denovo-snapshot"
}
constants["GCE_URL"] = 'https://www.googleapis.com/compute/{API_VERSION}/projects/'.format(**constants)


class gce_helper(object):

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
        project_url = '%s%s' % (constants["GCE_URL"], constants["PROJECT_ID"])

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

    def list_denovo_instances(self) :
        """ Lists all the denovo instances """
        print_iterable(self._list_denovo_instances())

    def list_instances(self):
        """ Lists all the instances in my GCE """
        print_iterable(self._list_instances())

    def _list_denovo_instances(self):
        for instance in self._list_instances():
            if 'denovo' in instance:
                yield instance

    def _create_instance(self, instance_json):
        """ Create a new instance from json """
        print("Creating instance {:s}".format(instance_json["name"]))
        request = self.gce_service.instances().insert(
            project=constants["PROJECT_ID"],
            body=instance_json,
            zone=constants["DEFAULT_ZONE"])
        response = request.execute(http=self.auth_http)
        response = self._blocking_call(self.gce_service, self.auth_http,
                                        response)

    def _create_disk(self, disk_json):
        """ Create a new disk from json """
        print("Creating disk {:s}".format(disk_json["name"]))
        request = self.gce_service.disks().insert(
            project=constants["PROJECT_ID"],
            body=disk_json,
            zone=constants["DEFAULT_ZONE"])
        response = request.execute(http=self.auth_http)
        response = self._blocking_call(self.gce_service, self.auth_http,
                                        response)

    def _create_instance_json(self, instance_name, device_name, num_cores):
        """ Creates a REST Json object to create a new instance"""
        instance_json = copy.deepcopy(gce_helper.new_instance_json)
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
        disk_json = copy.deepcopy(gce_helper.new_disk_json)
        disk_constants = copy.deepcopy(constants)
        disk_constants["device_name"] = device_name

        disk_json["name"] = disk_json["name"].format(**disk_constants)

        return disk_json

    def create_denovo_instances(self, num_instances=1, num_cores=4):
        """ Create new denovo instances

        Keyword arguments:
        num_instances -- the number of instances (default 1)
        num_cores -- the number of cores per instance (default 4)
        """
        print("Creating instances...")

        num_instances = int(num_instances)
        new_instance_start_number = self._get_max_denovo_number() + 1
        for instance_idx in xrange(new_instance_start_number,
                                   new_instance_start_number+num_instances):
            device_name = "denovo-{:d}".format(instance_idx)
            instance_name = "denovo-{:d}".format(instance_idx)
            self._create_disk(self._create_disk_json(device_name))
            self._create_instance(self._create_instance_json(
                instance_name, device_name, num_cores))

    def delete_all_denovo_instances(self):
        """ Deletes all denovo instances """

        print("Deleting all denovo instances...")
        if not confirm():
            return
        for instance_name in self._list_denovo_instances():
            self.delete_instance(instance_name)

    def delete_instance(self, instance_name):
        """ Deletes a particular instance by name """

        print("Deleting instance : {:s}...".format(instance_name))
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
        except StopIteration as e:
            raise ValueError("Unknown instance type" + instance_name)
        return number

    def _get_max_denovo_number(self):
        """ Get the maximum number from the list of denovo instances"""
        try :
            return max(gce_helper._get_instance_number(e) for e in
                   self._list_denovo_instances())
        except ValueError:
            return 0


def confirm(prompt="Are you sure?"):
    """prompts for yes or no """

    prompt = "{} (y|n): ".format(prompt)

    while True:
        ans = raw_input(prompt)
        if not ans:
            print prompt
            continue
        if ans in 'yY':
            return True
        if ans in 'nN':
            return False
        else:
            print prompt
            continue

def print_iterable(iterable):
    for e in iterable:
        print e

if __name__ == '__main__':
    helper = gce_helper()
    helper.list_denovo_instances()

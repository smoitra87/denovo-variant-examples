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
import gce_helper
from fabric.api import *
from contextlib import nested

class DenovoHelper(object):
    """ Helper for running commands on denovo instances

    Wraps up ssh requests and submits them
    """
    def __init__(self, helper):
        self.gce_helper = helper

    def denovo_update_from_github(self):
        """ Update denovo-variant-caller on all hosts"""
        with cd("denovo-variant-caller"):
            run("git pull origin master")

    def denovo_push_client_secrets(self):
        """ Push denovo client_secrets file to all hosts """
        local()

    def denovo_run_mvn_package(self):
        """ Run maven package on all hosts """
        with cd("denovo-variant-caller"):
            run("mvn package")


if __name__ == '__main__':
    helper = gce_helper.GCEHelper()
    denovo_helper = DenovoHelper()

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
import denovo_helper
import inspect
from fabric.api import *
import utils
import itertools

# Instantiate helper objects
helper = gce_helper.GCEHelper()
denovo_helper = denovo_helper.DenovoHelper(helper)

# Set up roles and environments
env.user = utils.constants["GCE_USER"]
env.roledefs = {
    "denovo":
    [ip for (name, ip) in helper.nameToIPMap.items() if 'denovo' in name],
    "gce": [],
}
env.disable_known_hosts = True
env.key_filename = utils.constants["GCE_PRIVATE_KEY"]

# Add methods from helper classes to fabric namespace
gce_methods = [tup for tup in
               inspect.getmembers(helper, predicate=inspect.ismethod)
               if not tup[0].startswith("_")]
denovo_methods = [tup for tup in
               inspect.getmembers(denovo_helper, predicate=inspect.ismethod)
               if not tup[0].startswith("_")]

for tup in gce_methods:
    locals()[tup[0]] = roles("gce")(tup[1])

for tup in denovo_methods:
    locals()[tup[0]] = roles("denovo")(tup[1])

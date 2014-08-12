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
import inspect

# Add gce direct methods
helper = gce_helper.gce_helper()
gce_methods = [tup for tup in
               inspect.getmembers(helper, predicate=inspect.ismethod)
               if not tup[0].startswith("_")]
for tup in gce_methods:
    locals()[tup[0]] = tup[1]

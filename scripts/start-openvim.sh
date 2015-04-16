#!/bin/bash

##
# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
# This file is part of openmano
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact with: nfvlabs@tid.es
##

#launch openvim inside a screen. It assumes a relative path ../openvim

DIRNAME=`dirname $0`

echo "Deprecated, use '$DIRNAME/openmano-service.sh start openvim'"


screen -dmS vim  bash
sleep 1
screen -S vim -p 0 -X stuff "cd ${DIRNAME}/../openvim\n"
sleep 1
screen -S vim -p 0 -X stuff "./openvimd.py\n"

echo "openvim running. Execute 'screen -x vim' and type 'exit' to terminte"






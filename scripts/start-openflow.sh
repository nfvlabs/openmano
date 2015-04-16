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


#Launch openflow controller if installed.  
#PARAM $1: directory where openflow controller is installed. By default ../../floodlight-0.90

DIRNAME=`dirname $0`
FLD=${DIRNAME}/../../floodlight-0.90

[ -n "$1" ] && FLD=$1

#check directory exist and it is compiled
[ ! -d ${FLD} ] &&
     echo "Directory ${FLD} not found" && exit
[ ! -r $FLD/target/floodlight.jar ] &&
     echo "File 'target/floodlight.jar' not found" && exit


echo "Deprecated, use '$DIRNAME/openmano-service.sh start floodlight'"

screen -dmS flow bash
#sleep 1
#screen -S flow -p 0 -X stuff "cd ${FLD}\n"

sleep 1
screen -S flow -p 0 -X stuff "java  -Dlogback.configurationFile=${DIRNAME}/flow-logback.xml -jar ${FLD}/target/floodlight.jar -cf ${DIRNAME}/flow.properties\n"

echo "openflow controller running. Execute 'screen -x flow' and 'Ctrl+c' to terminte"


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

#This script can be used as a basic test of openvim and openmano.
#Performs automatically the steps indicated at:
#     https://github.com/nfvlabs/openmano/wiki/Getting-started#how-to-use-it
#stopping on an error
#WARNING: It destroy the database content


function usage(){
    echo -e "usage: ${BASH_SOURCE[0]} [-f]\n  Deletes openvim/openmano content and make automatically the wiki steps"
    echo -e "  at 'https://github.com/nfvlabs/openmano/wiki/Getting-started#how-to-use-it'"
    echo -e "  OPTIONS:"
    echo -e "    -f --force : does not prompt for confirmation"
    echo -e "    -h --help  : shows this help"
}

function is_valid_uuid(){
    echo "$1" | grep -q -E '^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$' && return 0
    return 1
}


#detect if is called with a source to use the 'exit'/'return' command for exiting
[[ ${BASH_SOURCE[0]} != $0 ]] && _exit="return" || _exit="exit"

#check correct arguments
[[ -n $1 ]] && [[ $1 != -h ]] && [[ $1 != --help ]] && [[ $1 != -f ]] && [[ $1 != --force ]] && \
   echo "invalid argument '$1'?" &&  usage >&2 && $_exit 1
[[ $1 == -h ]] || [[ $1 == --help ]]  && usage && $_exit 0

#ask for confirmation if argument is not -f --force
force=""
[[ $1 == -f ]] || [[ $1 == --force ]] && force=y
[[ $force != y ]] && read -e -p "WARNING: openmano and openvim database content will be lost!!!  Continue(y/N)" force
[[ $force != y ]] && [[ $force != yes ]] && echo "aborted!" && $_exit

DIRNAME=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
DIRvim=$(dirname $DIRNAME)/openvim
DIRmano=$(dirname $DIRNAME)/openmano

echo "deleting deployed vm"
openvim vm-delete -f | grep -q deleted && sleep 10 #give some time to get virtual machines deleted

echo "Stopping openmano"
$DIRNAME/service-openmano.sh stop

echo "Initializing databases"
$DIRvim/database_utils/init_vim_db.sh -u vim -p vimpw
$DIRmano/database_utils/init_mano_db.sh -u mano -p manopw

echo "Starting openmano"
$DIRNAME/service-openmano.sh start

echo "Adding example hosts"
openvim host-add $DIRvim/test/hosts/host-example0.json || ! echo "fail" >&2 || $_exit 1
openvim host-add $DIRvim/test/hosts/host-example1.json || ! echo "fail" >&2 || $_exit 1
openvim host-add $DIRvim/test/hosts/host-example2.json || ! echo "fail" >&2 || $_exit 1
openvim host-add $DIRvim/test/hosts/host-example3.json || ! echo "fail" >&2 || $_exit 1
echo "Adding example nets"
openvim net-create $DIRvim/test/networks/net-example0.yaml || ! echo "fail" >&2 || $_exit 1
openvim net-create $DIRvim/test/networks/net-example1.yaml || ! echo "fail" >&2 || $_exit 1
openvim net-create $DIRvim/test/networks/net-example2.yaml || ! echo "fail" >&2 || $_exit 1
openvim net-create $DIRvim/test/networks/net-example3.yaml || ! echo "fail" >&2 || $_exit 1

echo "Creating openvim tenant 'admin'"
vimtenant=`openvim tenant-create '{"tenant": {"name":"admin", "description":"admin"}}' |gawk '{print $1}'`
#check a valid uuid is obtained
is_valid_uuid $vimtenant || ! echo "fail" >&2 || $_exit 1
echo "  $vimtenant"
export OPENVIM_TENANT=$vimtenant

echo "Adding openvim environment variables to ~/.bashrc"
echo -e "\nexport OPENVIM_TENANT=$vimtenant" >> ~/.bashrc

echo "Creating openmano tenant 'mytenant'"
nfvotenant=`openmano tenant-create mytenant --description=mytenant |gawk '{print $1}'`
#check a valid uuid is obtained
is_valid_uuid $nfvotenant || ! echo "fail" >&2 || $_exit 1 
export OPENMANO_TENANT=$nfvotenant
echo "  $nfvotenant"

echo "Creating datacenter 'mydc' in openmano"
datacenter=`openmano datacenter-create mydc http://localhost:9080/openvim |gawk '{print $1}'`
#check a valid uuid is obtained
is_valid_uuid $datacenter || ! echo "fail" >&2 || $_exit 1 
echo "  $datacenter"
export OPENMANO_DATACENTER=$datacenter

echo "Adding openmano environment variables to ~/.bashrc"
echo "export OPENMANO_TENANT=$nfvotenant" >> ~/.bashrc
echo "export OPENMANO_DATACENTER=$datacenter" >> ~/.bashrc

echo "Attaching openmano tenant to the datacenter and the openvim tenant"
openmano datacenter-attach mydc --vim-tenant-id $vimtenant || ! echo "fail" >&2 || $_exit 1 

echo "Updating external nets in openmano"
openmano datacenter-net-update -f mydc || ! echo "fail" >&2 || $_exit 1

echo "Adding particular configuration - VNFs"
openmano vnf-create $DIRmano/vnfs/examples/linux.yaml         || ! echo "fail" >&2 || $_exit 1
openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF1.yaml || ! echo "fail" >&2 || $_exit 1
openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF2.yaml || ! echo "fail" >&2 || $_exit 1

echo "Adding particular configuration - Scenarios"
openmano scenario-create $DIRmano/scenarios/examples/simple.yaml  || ! echo "fail" >&2 || $_exit 1
openmano scenario-create $DIRmano/scenarios/examples/complex.yaml || ! echo "fail" >&2 || $_exit 1

echo "Adding particular configuration - Scenario instances"
openmano scenario-deploy simple simple-instance   || ! echo "fail" >&2 || $_exit 1
openmano scenario-deploy complex complex-instance || ! echo "fail" >&2 || $_exit 1

echo
echo DONE
#echo "Listing VNFs"
#openmano vnf-list
#echo "Listing scenarios"
#openmano scenario-list
#echo "Listing scenario instances"
#openmano instance-scenario-list



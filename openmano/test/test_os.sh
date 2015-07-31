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

#This script can be used as a basic test of openmano deployment over openstack.
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
DIRmano=$(dirname $DIRNAME)
DIRscript=$(dirname $DIRmano)/scripts

echo "deleting deployed vm"
openvim vm-delete -f | grep -q deleted && sleep 10 #give some time to get virtual machines deleted

echo "Stopping openmano"
$DIRscript/service-openmano.sh mano stop

echo "Initializing databases"
#$DIRvim/database_utils/init_vim_db.sh -u vim -p vimpw
$DIRmano/database_utils/init_mano_db.sh -u mano -p manopw

echo "Starting openmano"
$DIRscript/service-openmano.sh mano start

echo "Creating openmano tenant 'mytenant'"
result=`openmano tenant-create mytenant --description=mytenant`
nfvotenant=`echo $result |gawk '{print $1}'`
#check a valid uuid is obtained
is_valid_uuid $nfvotenant || ! echo "fail" >&2 || echo $result >$2 || $_exit 1 
export OPENMANO_TENANT=$nfvotenant
echo "  $nfvotenant"

echo "Creating datacenter 'myos' in openmano"
result=`openmano datacenter-create myos "${OS_AUTH_URL}" "--type=openstack" "--config=${OS_CONFIG}"`
datacenter=`echo $result |gawk '{print $1}'`
#check a valid uuid is obtained
is_valid_uuid $datacenter || ! echo "fail" >&2 || echo $result >$2 || $_exit 1 
echo "  $datacenter"
export OPENMANO_DATACENTER=$datacenter

echo "Adding openmano environment variables to ~/.bashrc"
echo "export OPENMANO_TENANT=$nfvotenant" >> ~/.bashrc
echo "export OPENMANO_DATACENTER=$datacenter" >> ~/.bashrc

echo "Attaching openmano tenant to the datacenter and the openvim tenant"
openmano datacenter-attach myos "--user=$OS_USERNAME" "--password=$OS_PASSWORD" "--vim-tenant-name=$OS_TENANT_NAME"  || ! echo "fail" >&2 || $_exit 1 

echo "Updating external nets in openmano"
openmano datacenter-net-update -f myos || ! echo "fail" >&2 || $_exit 1

echo "Adding particular configuration - VNFs"
#glance image-create --file=./US1404dpdk.qcow2 --name=US1404dpdk --disk-format=qcow2 --min-disk=2 --is-public=True --container-format=bare
#nova image-meta US1404dpdk set location=/mnt/powervault/virtualization/vnfs/os/US1404dpdk.qcow2


#glance image-create --file=./US1404user.qcow2 --min-disk=2 --is-public=True --container-format=bare --name=US1404user --disk-format=qcow2
#nova image-meta US1404user  set location=/mnt/powervault/virtualization/vnfs/os/US1404user.qcow2

openmano vnf-create $DIRmano/vnfs/examples/linux.yaml "--image-path=$OS_TEST_IMAGE_PATH_LINUX"  || ! echo "fail" >&2 || $_exit 1
openmano vnf-create $DIRmano/vnfs/examples/linux.yaml "--image-path=$OS_TEST_IMAGE_PATH_CIRROS" "--name=cirros"
openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF1.yaml "--image-path=$OS_TEST_IMAGE_PATH_LINUX"  || ! echo "fail" >&2 || $_exit 1
openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF2.yaml "--image-path=$OS_TEST_IMAGE_PATH_LINUXDATA" || ! echo "fail" >&2 || $_exit 1

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



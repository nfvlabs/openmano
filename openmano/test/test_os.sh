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
#in order to use you need to set the OS_XXXX bash variables with openstack values
#    OS_USERNAME     e.g.: admin
#    OS_PASSWORD     
#    OS_AUTH_URL     url to access openstack VIM e.g. http:/openstack:35357/v2.0
#    OS_TENANT_NAME  e.g.: admin
#    OS_CONFIG       e.g.: "'network_vlan_ranges: sriov_net'"
#    OS_TEST_IMAGE_PATH_LINUX  image path(location) to use by the VNF linux
#    OS_TEST_IMAGE_PATH_LINUXDATA image path(location) to use by the VNF dataplaneVNF_2VMs and dataplaneVNF3

#it should be used with source. It can modifies /home/$USER/.bashrc appending the variables
#you need to delete them manually if desired

function usage(){
    echo -e "usage: ${BASH_SOURCE[0]} [OPTIONS] <action>\n  test openmano using a openstack VIM"
    echo -e "  <action> is a list of the following items (by default 'reset create')"
    echo -e "    reset     reset the openmano database content"
    echo -e "    create    creates items at openstack VIM"
    echo -e "    delete    delete created items"
    echo -e "  OPTIONS:"
    echo -e "    -f --force       does not prompt for confirmation"
    echo -e "    -h --help        shows this help"
    echo -e "    --insert-bashrc  insert the created tenant,datacenter variables at"
    echo -e "                     ~/.bashrc to be available by openmano config"
}

function is_valid_uuid(){
    echo "$1" | grep -q -E '^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$' && return 0
    return 1
}

#detect if is called with a source to use the 'exit'/'return' command for exiting
[[ ${BASH_SOURCE[0]} != $0 ]] && _exit="return" || _exit="exit"

#detect if environment variables are set
[[ -z $OS_USERNAME ]] && echo "OS_USERNAME variable not defined" >&2 && $_exit 1
[[ -z $OS_PASSWORD ]] && echo "OS_PASSWORD variable not defined" >&2 && $_exit 1
[[ -z $OS_AUTH_URL ]] && echo "OS_AUTH_URL variable not defined" >&2 && $_exit 1
[[ -z $OS_TENANT_NAME ]] && echo "OS_TENANT_NAME variable not defined" >&2 && $_exit 1
[[ -z $OS_CONFIG ]] && echo "OS_CONFIG variable not defined" >&2 && $_exit 1
[[ -z $OS_TEST_IMAGE_PATH_LINUX ]] && echo "OS_TEST_IMAGE_PATH_LINUX variable not defined" >&2 && $_exit 1
[[ -z $OS_TEST_IMAGE_PATH_LINUXDATA ]] && echo "OS_TEST_IMAGE_PATH_LINUXDATA variable not defined" >&2 && $_exit 1

#check correct arguments
action_list=""
for param in $*
do
   if [[ $param == reset ]] || [[ $param == create ]] || [[ $param == delete ]]
   then 
       action_list="$action_list $param"
   elif [[ $param == -h ]] || [[ $param == --help ]]
   then
       usage
       $_exit 0
   elif [[ $param == -f ]] || [[ $param == --force ]]
   then
       force=y
   elif [[ $param == --insert-bashrc ]]
   then
       insert_bashrc=y
   else
       echo "invalid argument '$param'?" &&  usage >&2 && $_exit 1
   fi
done

DIRNAME=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
DIRmano=$(dirname $DIRNAME)
DIRscript=$(dirname $DIRmano)/scripts
#by default action should be reset create
[[ -z $action_list ]] && action_list="reset create"

for action in $action_list
do
if [[ $action == "reset" ]] 
then 

    #ask for confirmation if argument is not -f --force
    [[ $force != y ]] && read -e -p "WARNING: reset openmano database, content will be lost!!! Continue(y/N)" force
    [[ $force != y ]] && [[ $force != yes ]] && echo "aborted!" && $_exit

    echo "Stopping openmano"
    $DIRscript/service-openmano.sh mano stop
    echo "Initializing openmano database"
    $DIRmano/database_utils/init_mano_db.sh -u mano -p manopw
    echo "Starting openmano"
    $DIRscript/service-openmano.sh mano start

elif [[ $action == "delete" ]]
then
    openmano instance-scenario-delete -f simple-instance     || echo "fail" >&2
    openmano instance-scenario-delete -f complex2-instance   || echo "fail" >&2
    openmano scenario-delete -f simple       || echo "fail" >&2
    openmano scenario-delete -f complex2     || echo "fail" >&2
    openmano vnf-delete -f linux             || echo "fail" >&2
    openmano vnf-delete -f dataplaneVNF_2VMs || echo "fail" >&2
    openmano vnf-delete -f dataplaneVNF3     || echo "fail" >&2
    openmano datacenter-detach myos          || echo "fail" >&2
    openmano datacenter-delete -f myos       || echo "fail" >&2
    openmano tenant-delete -f mytenant-os    || echo "fail" >&2

elif [[ $action == "create" ]]
then 

    echo "Creating openmano tenant 'mytenant-os'"
    result=`openmano tenant-create mytenant-os --description=mytenant`
    nfvotenant=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    is_valid_uuid $nfvotenant || ! echo "fail" >&2 || echo $result >$2 || $_exit 1 
    export OPENMANO_TENANT=$nfvotenant
    [[ $insert_bashrc == y ]] && echo -e "\nexport OPENMANO_TENANT=$nfvotenant"  >> ~/.bashrc
    echo "  $nfvotenant"

    echo "Creating datacenter 'myos' in openmano"
    result=`openmano datacenter-create myos "${OS_AUTH_URL}" "--type=openstack" "--config=${OS_CONFIG}"`
    datacenter=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    is_valid_uuid $datacenter || ! echo "fail" >&2 || echo $result >$2 || $_exit 1 
    echo "  $datacenter"
    export OPENMANO_DATACENTER=$datacenter
    [[ $insert_bashrc == y ]] && echo -e "\nexport OPENMANO_DATACENTER=$datacenter"  >> ~/.bashrc

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
    #openmano vnf-create $DIRmano/vnfs/examples/linux.yaml "--image-path=$OS_TEST_IMAGE_PATH_CIRROS" "--name=cirros"
    #openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF1.yaml "--image-path=$OS_TEST_IMAGE_PATH_LINUX"  || ! echo "fail" >&2 || $_exit 1
    #openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF2.yaml "--image-path=$OS_TEST_IMAGE_PATH_LINUXDATA" || ! echo "fail" >&2 || $_exit 1
    openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF_2VMs.yaml "--image-path=$OS_TEST_IMAGE_PATH_LINUXDATA,$OS_TEST_IMAGE_PATH_LINUXDATA" || ! echo "fail" >&2 || $_exit 1
    openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF3.yaml "--image-path=$OS_TEST_IMAGE_PATH_LINUXDATA"  || ! echo "fail" >&2 || $_exit 1

    echo "Adding particular configuration - Scenarios"
    openmano scenario-create $DIRmano/scenarios/examples/simple.yaml  || ! echo "fail" >&2 || $_exit 1
    openmano scenario-create $DIRmano/scenarios/examples/complex2.yaml || ! echo "fail" >&2 || $_exit 1

    echo "Adding particular configuration - Scenario instances"
    openmano scenario-deploy simple simple-instance   || ! echo "fail" >&2 || $_exit 1
    openmano scenario-deploy complex2 complex2-instance || ! echo "fail" >&2 || $_exit 1

    echo
    echo DONE
fi
done


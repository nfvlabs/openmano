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
    echo -e "    -d --delete : delete vnfs,scenarios,instances / vms;"
    echo -e "                  insert twice to delete all (datacenters,tenants / images,flavors,ports,nets,hosts)"
    echo -e "    -h --help  : shows this help"
}

function is_valid_uuid(){
    echo "$1" | grep -q -E '^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$' && return 0
    return 1
}


#detect if is called with a source to use the 'exit'/'return' command for exiting
[[ ${BASH_SOURCE[0]} != $0 ]] && _exit="return" || _exit="exit"

#check correct arguments
force=""
force_="y"
delete=0
while [[ $# -gt 0 ]]
do
    argument="$1"
    shift
    #short options
    if [[ ${argument:0:1} == "-" ]] && [[ ${argument:1:1} != "-" ]] && [[ ${#argument} -ge 2 ]]
    then
        index=0
        while index=$((index+1)) && [[ $index -lt ${#argument} ]]
        do
            [[ ${argument:$index:1} == h ]]  && usage   && $_exit 0
            [[ ${argument:$index:1} == f ]]  && force=y && continue
            [[ ${argument:$index:1} == d ]]  && delete=$((delete+1)) && continue
            echo "invalid option '${argument:$index:1}'?  Type -h for help" >&2 && $_exit 1
        done
        continue
    fi
    #long options
    [[ $argument == --help ]]   && usage   && $_exit 0
    [[ $argument == --force ]]  && force=y && continue
    [[ $argument == --delete ]] && delete=$((delete+1)) && continue
    echo "invalid argument '$argument'?  Type -h for help" >&2 && $_exit 1
done

if [[ $delete -gt 0 ]] 
then
    todelete="instance-scenario scenario vnf"
    showall=""
    [[ $delete -gt 1 ]] && todelete="${todelete} datacenter tenant" && showall="--all"
    for what in $todelete
    do
        [[ $force == y ]] && echo deleting openmano ${what}s
        [[ $force != y ]] && read -e -p "Delete openmano ${what}s? (y/N)" force_
        [[ $force_ != y ]] && [[ $force_ != yes ]] && continue
        for item in `openmano ${what}-list $showall | awk '/^ *[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12} +/{print $1}'`;
        do
            echo -n "$item   "
            if [[ $what == datacenter ]]
            then 
                openmano ${what}-detach $showall $item  
                openmano ${what}-delete  -f $item  || ! echo "fail" >&2 || $_exit 1
            elif [[ $what == tenant ]]
            then
                openmano ${what}-delete  -f $item  || ! echo "fail" >&2 || $_exit 1
            else
                openmano ${what}-delete $showall -f $item  || ! echo "fail" >&2 || $_exit 1
            fi
        done
    done

    todelete="vm"
    [[ $delete -gt 1 ]] && todelete="${todelete} image flavor port net  host tenant"
    for what in ${todelete}
    do
        [[ $force == y ]] && echo deleting openvim ${what}s
        [[ $force != y ]] && read -e -p "Delete openvim ${what}s? (y/N)" force_
        [[ $force_ != y ]] && [[ $force_ != yes ]] && echo "aborted!" && $_exit
        for item in `openvim $what-list | awk '/^ *[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12} +/{print $1}'`;
        do
            echo -n "$item   "
            [[ $what != host ]] || openvim $what-remove -f $item  || ! echo "fail" >&2 || $_exit 1
            [[ $what == host ]] || openvim $what-delete -f $item  || ! echo "fail" >&2 || $_exit 1
        done
    done
    $_exit 0
fi

#ask for confirmation if argument is not -f --force
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
openmano datacenter-netmap-upload -f || ! echo "fail" >&2 || $_exit 1

echo "Adding particular configuration - VNFs"
openmano vnf-create $DIRmano/vnfs/examples/linux.yaml         || ! echo "fail" >&2 || $_exit 1
openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF1.yaml || ! echo "fail" >&2 || $_exit 1
openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF2.yaml || ! echo "fail" >&2 || $_exit 1
openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF_2VMs.yaml || ! echo "fail" >&2 || $_exit 1
openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF3.yaml || ! echo "fail" >&2 || $_exit 1

echo "Adding particular configuration - Scenarios"
openmano scenario-create $DIRmano/scenarios/examples/simple.yaml  || ! echo "fail" >&2 || $_exit 1
openmano scenario-create $DIRmano/scenarios/examples/complex.yaml || ! echo "fail" >&2 || $_exit 1
openmano scenario-create $DIRmano/scenarios/examples/complex2.yaml || ! echo "fail" >&2 || $_exit 1

echo "Adding particular configuration - Scenario instances"
openmano instance-scenario-create --scenario simple   --name simple-instance   || ! echo "fail" >&2 || $_exit 1
openmano instance-scenario-create --scenario complex  --name complex-instance  || ! echo "fail" >&2 || $_exit 1
openmano instance-scenario-create --scenario complex2 --name complex2-instance || ! echo "fail" >&2 || $_exit 1

echo
echo "Check virtual machines are deployed"
vms_error=`openvim vm-list | grep ERROR | wc -l`
vms=`openvim vm-list | wc -l`
[[ $vms -ne 8 ]]       &&  echo "WARNING: $vms VMs created, must be 8 VMs" >&2 && $_exit 1
[[ $vms_error -gt 0 ]] &&  echo "WARNING: $vms_error VMs with ERROR" >&2       && $_exit 1

echo
echo DONE
#echo "Listing VNFs"
#openmano vnf-list
#echo "Listing scenarios"
#openmano scenario-list
#echo "Listing scenario instances"
#openmano instance-scenario-list



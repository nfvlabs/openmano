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
fail=""
[[ -z $OS_USERNAME ]] && echo "OS_USERNAME variable not defined" >&2 && fail=1
[[ -z $OS_PASSWORD ]] && echo "OS_PASSWORD variable not defined" >&2 && fail=1
[[ -z $OS_AUTH_URL ]] && echo "OS_AUTH_URL variable not defined" >&2 && fail=1
[[ -z $OS_TENANT_NAME ]] && echo "OS_TENANT_NAME variable not defined" >&2 && fail=1
[[ -z $OS_CONFIG ]] && echo "OS_CONFIG variable not defined" >&2 && fail=1
[[ -z $OS_TEST_IMAGE_PATH_LINUX ]] && echo "OS_TEST_IMAGE_PATH_LINUX variable not defined" >&2 && fail=1
[[ -z $OS_TEST_IMAGE_PATH_LINUXDATA ]] && echo "OS_TEST_IMAGE_PATH_LINUXDATA variable not defined" >&2 && fail=1
[[ -n $fail ]] && $_exit 1

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
    result=`openmano tenant-list TOS-tenant`
    nfvotenant=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    is_valid_uuid $nfvotenant || ! echo "Tenant TOS-tenant not found. Already delete?" >&2 || $_exit 1
    export OPENMANO_TENANT=$nfvotenant
    openmano instance-scenario-delete -f simple-instance     || echo "fail"
    openmano instance-scenario-delete -f complex2-instance   || echo "fail"
    openmano scenario-delete -f simple       || echo "fail"
    openmano scenario-delete -f complex2     || echo "fail"
    openmano vnf-delete -f linux             || echo "fail"
    openmano vnf-delete -f dataplaneVNF_2VMs || echo "fail"
    openmano vnf-delete -f dataplaneVNF3     || echo "fail"
    openmano vnf-delete -f TOS-VNF1          || echo "fail"
    openmano datacenter-detach TOS-dc        || echo "fail"
    openmano datacenter-delete -f TOS-dc     || echo "fail"
    openmano tenant-delete -f TOS-tenant     || echo "fail"

elif [[ $action == "create" ]]
then 

    printf "%-50s" "Creating openmano tenant 'TOS-tenant': "
    result=`openmano tenant-create TOS-tenant --description="created by test_os.sh"`
    nfvotenant=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    ! is_valid_uuid $nfvotenant && echo "FAIL" && echo "    $result" && $_exit 1 
    export OPENMANO_TENANT=$nfvotenant
    [[ $insert_bashrc == y ]] && echo -e "\nexport OPENMANO_TENANT=$nfvotenant"  >> ~/.bashrc
    echo $nfvotenant

    printf "%-50s" "Creating datacenter 'TOS-dc' in openmano:"
    result=`openmano datacenter-create TOS-dc "${OS_AUTH_URL}" "--type=openstack" "--config=${OS_CONFIG}"`
    datacenter=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    ! is_valid_uuid $datacenter && echo "FAIL" && echo "    $result" && $_exit 1 
    echo $datacenter
    export OPENMANO_DATACENTER=$datacenter
    [[ $insert_bashrc == y ]] && echo -e "\nexport OPENMANO_DATACENTER=$datacenter"  >> ~/.bashrc

    printf "%-50s" "Attaching openmano tenant to the datacenter:"
    result=`openmano datacenter-attach TOS-dc "--user=$OS_USERNAME" "--password=$OS_PASSWORD" "--vim-tenant-name=$OS_TENANT_NAME"`
    [[ $? != 0 ]] && echo  "FAIL" && echo "    $result" && $_exit 1
    echo OK

    printf "%-50s" "Updating external nets in openmano: "
    result=`openmano datacenter-net-update -f TOS-dc`
    [[ $? != 0 ]] && echo  "FAIL" && echo "    $result"  && $_exit 1
    echo OK

    printf "%-50s" "Creating VNF 'linux': "
    #glance image-create --file=./US1404dpdk.qcow2 --name=US1404dpdk --disk-format=qcow2 --min-disk=2 --is-public=True --container-format=bare
    #nova image-meta US1404dpdk set location=/mnt/powervault/virtualization/vnfs/os/US1404dpdk.qcow2
    #glance image-create --file=./US1404user.qcow2 --min-disk=2 --is-public=True --container-format=bare --name=US1404user --disk-format=qcow2
    #nova image-meta US1404user  set location=/mnt/powervault/virtualization/vnfs/os/US1404user.qcow2
    result=`openmano vnf-create $DIRmano/vnfs/examples/linux.yaml "--image-path=$OS_TEST_IMAGE_PATH_LINUX"`
    vnf=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    ! is_valid_uuid $vnf && echo FAIL && echo "    $result" &&  $_exit 1
    echo $vnf
    
    printf "%-50s" "Creating VNF 1PF,1VF,2GHP,4PThreads: "
    result=`openmano vnf-create "vnf:
        name: TOS-VNF1
        external-connections:
        - name: eth0
          type: mgmt
          VNFC: TOS-VNF1-VM
          local_iface_name: eth0
        - name: PF0
          type: data
          VNFC: TOS-VNF1-VM
          local_iface_name: PF0
        - name: VF0
          type: data
          VNFC: TOS-VNF1-VM
          local_iface_name: VF0
        VNFC: 
        - name: TOS-VNF1-VM
          VNFC image: $OS_TEST_IMAGE_PATH_LINUXDATA
          numas:
          - paired-threads: 2
            paired-threads-id: [ [0,2], [1,3] ]
            memory: 2
            interfaces:
            - name:  PF0
              vpci: '0000:00:11.0'
              dedicated: 'yes'
              bandwidth: 10 Gbps
              mac_address: '20:33:45:56:77:44'
            - name:  VF0
              vpci:  '0000:00:12.0'
              dedicated: 'no'
              bandwidth: 1 Gbps
              mac_address: '20:33:45:56:77:45'
          bridge-ifaces:
          - name: eth0
            vpci: '0000:00:09.0'
            bandwidth: 1 Mbps
            mac_address: '20:33:45:56:77:46'
            model: e1000
       "`
    vnf=`echo $result |gawk '{print $1}'`
    ! is_valid_uuid $vnf && echo FAIL && echo "    $result" && $_exit 1
    echo $vnf
 
    printf "%-50s" "Creating VNF 'dataplaneVNF_2VMs': "
    result=`openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF_2VMs.yaml "--image-path=$OS_TEST_IMAGE_PATH_LINUXDATA,$OS_TEST_IMAGE_PATH_LINUXDATA"`
    vnf=`echo $result |gawk '{print $1}'`
    ! is_valid_uuid $vnf && echo FAIL && echo "    $result" && $_exit 1
    echo $vnf
 
    printf "%-50s" "Creating VNF 'dataplaneVNF3.yaml': "
    result=`openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF3.yaml "--image-path=$OS_TEST_IMAGE_PATH_LINUXDATA"`
    vnf=`echo $result |gawk '{print $1}'`
    ! is_valid_uuid $vnf && echo FAIL && echo "    $result" && $_exit 1
    echo $vnf

    for sce in simple complex2
    do
      printf "%-50s" "Creating scenario '$sce':"
      result=`openmano scenario-create $DIRmano/scenarios/examples/${sce}.yaml`
      scenario=`echo $result |gawk '{print $1}'`
      ! is_valid_uuid $scenario && echo FAIL && echo "    $result" &&  $_exit 1
      echo $scenario
    done

    for sce in simple complex2
    do 
      printf "%-50s" "Deploying scenario '$sce':"
      result=`openmano scenario-deploy $sce ${sce}-instance`
      instance=`echo $result |gawk '{print $1}'`
      ! is_valid_uuid $instance && echo FAIL && echo "    $result" && $_exit 1
      echo $instance
    done

    echo
    echo DONE
fi
done


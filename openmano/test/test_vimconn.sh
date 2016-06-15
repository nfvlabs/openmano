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

#This script can be used as a basic test of openmano deployment over a vim
#in order to use you need to set the VIM_XXXX bash variables with a vim values
#    VIM_TYPE         openstack or openvim
#    VIM_USERNAME     e.g.: admin
#    VIM_PASSWORD     
#    VIM_AUTH_URL     url to access VIM e.g. http:/openstack:35357/v2.0
#    VIM_AUTH_URL_ADMIN admin url
#    VIM_TENANT_NAME  e.g.: admin
#    VIM_CONFIG       e.g.: "'network_vlan_ranges: sriov_net'"
#    VIM_TEST_IMAGE_PATH_LINUX  image path(location) to use by the VNF linux
#    VIM_TEST_IMAGE_PATH_NFV image path(location) to use by the VNF dataplaneVNF_2VMs and dataplaneVNF3

#it should be used with source. It can modifies /home/$USER/.bashrc appending the variables
#you need to delete them manually if desired

function usage(){
    echo -e "usage: ${BASH_SOURCE[0]} [OPTIONS] <action>\n  test VIM managing from openmano"
    echo -e "  <action> is a list of the following items (by default 'reset create')"
    echo -e "    reset     reset the openmano database content"
    echo -e "    create    creates items at VIM"
    echo -e "    delete    delete created items"
    echo -e "  OPTIONS:"
    echo -e "    -f --force       does not prompt for confirmation"
    echo -e "    -h --help        shows this help"
    echo -e "    --insert-bashrc  insert the created tenant,datacenter variables at"
    echo -e "                     ~/.bashrc to be available by openmano config"
}

function is_valid_uuid(){
    echo "$1" | grep -q -E '^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$' && return 0
    echo "$1" | grep -q -E '^[0-9a-f]{32}$' && return 0
    return 1
}

#detect if is called with a source to use the 'exit'/'return' command for exiting
[[ ${BASH_SOURCE[0]} != $0 ]] && _exit="return" || _exit="exit"

#detect if environment variables are set
fail=""
[[ -z $VIM_TYPE ]]     && echo "VIM_TYPE variable not defined" >&2 && fail=1
[[ -z $VIM_USERNAME ]] && echo "VIM_USERNAME variable not defined" >&2 && fail=1
[[ -z $VIM_PASSWORD ]] && echo "VIM_PASSWORD variable not defined" >&2 && fail=1
[[ -z $VIM_AUTH_URL ]] && echo "VIM_AUTH_URL variable not defined" >&2 && fail=1
[[ -z $VIM_TENANT_NAME ]] && [[ -z $VIM_TENANT_NAME ]] && echo "neither VIM_TENANT_NAME not VIM_TENANT_ID variables are not defined" >&2 && fail=1
[[ -z $VIM_CONFIG ]] && echo "VIM_CONFIG variable not defined" >&2 && fail=1
[[ -z $VIM_TEST_IMAGE_PATH_LINUX ]] && echo "VIM_TEST_IMAGE_PATH_LINUX variable not defined" >&2 && fail=1
[[ -z $VIM_TEST_IMAGE_PATH_NFV ]]   && echo "VIM_TEST_IMAGE_PATH_NFV variable not defined" >&2 && fail=1
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
#by default action should be reset and create
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
    result=`openmano tenant-list TESTVIM-tenant`
    nfvotenant=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    is_valid_uuid $nfvotenant || ! echo "Tenant TESTVIM-tenant not found. Already delete?" >&2 || $_exit 1
    export OPENMANO_TENANT=$nfvotenant
    openmano instance-scenario-delete -f simple-instance     || echo "fail"
    openmano instance-scenario-delete -f complex2-instance   || echo "fail"
    openmano scenario-delete -f simple       || echo "fail"
    openmano scenario-delete -f complex2     || echo "fail"
    openmano vnf-delete -f linux             || echo "fail"
    openmano vnf-delete -f dataplaneVNF_2VMs || echo "fail"
    openmano vnf-delete -f dataplaneVNF3     || echo "fail"
    openmano vnf-delete -f TESTVIM-VNF1          || echo "fail"
    openmano datacenter-detach TESTVIM-dc        || echo "fail"
    openmano datacenter-delete -f TESTVIM-dc     || echo "fail"
    openmano tenant-delete -f TESTVIM-tenant     || echo "fail"

elif [[ $action == "create" ]]
then 

    printf "%-50s" "Creating openmano tenant 'TESTVIM-tenant': "
    result=`openmano tenant-create TESTVIM-tenant --description="created by test_vimconn.sh"`
    nfvotenant=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    ! is_valid_uuid $nfvotenant && echo "FAIL" && echo "    $result" && $_exit 1 
    export OPENMANO_TENANT=$nfvotenant
    [[ $insert_bashrc == y ]] && echo -e "\nexport OPENMANO_TENANT=$nfvotenant"  >> ~/.bashrc
    echo $nfvotenant

    printf "%-50s" "Creating datacenter 'TESTVIM-dc' in openmano:"
    URL_ADMIN_PARAM=""
    [[ -n $VIM_AUTH_URL_ADMIN ]] && URL_ADMIN_PARAM="--url_admin=$VIM_AUTH_URL_ADMIN"
    result=`openmano datacenter-create TESTVIM-dc "${VIM_AUTH_URL}" "--type=$VIM_TYPE" $URL_ADMIN_PARAM "--config=${VIM_CONFIG}"`
    datacenter=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    ! is_valid_uuid $datacenter && echo "FAIL" && echo "    $result" && $_exit 1 
    echo $datacenter
    export OPENMANO_DATACENTER=$datacenter
    [[ $insert_bashrc == y ]] && echo -e "\nexport OPENMANO_DATACENTER=$datacenter"  >> ~/.bashrc

    printf "%-50s" "Attaching openmano tenant to the datacenter:"
    [[ -n $VIM_PASSWORD ]]    && passwd_param="--password=$VIM_PASSWORD"                    || passwd_param=""
    [[ -n $VIM_TENANT_NAME ]] && vim_tenant_name_param="--vim-tenant-name=$VIM_TENANT_NAME" || vim_tenant_name_param=""
    [[ -n $VIM_TENANT_ID   ]] && vim_tenant_id_param="--vim-tenant-id=$VIM_TENANT_ID"       || vim_tenant_id_param=""
    [[ -n $VIM_PASSWORD ]] && passwd_param="--password=$VIM_PASSWORD" || passwd_param=""
    result=`openmano datacenter-attach TESTVIM-dc "--user=$VIM_USERNAME" "$passwd_param" "$vim_tenant_name_param"`
    [[ $? != 0 ]] && echo  "FAIL" && echo "    $result" && $_exit 1
    echo OK

    printf "%-50s" "Updating external nets in openmano: "
    result=`openmano datacenter-netmap-delete -f --all`
    [[ $? != 0 ]] && echo  "FAIL" && echo "    $result"  && $_exit 1
    result=`openmano datacenter-netmap-upload -f`
    [[ $? != 0 ]] && echo  "FAIL" && echo "    $result"  && $_exit 1
    echo OK

    printf "%-50s" "Creating VNF 'linux': "
    #glance image-create --file=./US1404dpdk.qcow2 --name=US1404dpdk --disk-format=qcow2 --min-disk=2 --is-public=True --container-format=bare
    #nova image-meta US1404dpdk set location=/mnt/powervault/virtualization/vnfs/os/US1404dpdk.qcow2
    #glance image-create --file=./US1404user.qcow2 --min-disk=2 --is-public=True --container-format=bare --name=US1404user --disk-format=qcow2
    #nova image-meta US1404user  set location=/mnt/powervault/virtualization/vnfs/os/US1404user.qcow2
    result=`openmano vnf-create $DIRmano/vnfs/examples/linux.yaml "--image-path=$VIM_TEST_IMAGE_PATH_LINUX"`
    vnf=`echo $result |gawk '{print $1}'`
    #check a valid uuid is obtained
    ! is_valid_uuid $vnf && echo FAIL && echo "    $result" &&  $_exit 1
    echo $vnf
    
    printf "%-50s" "Creating VNF 1PF,1VF,2GB,4PThreads: "
    result=`openmano vnf-create "vnf:
        name: TESTVIM-VNF1
        external-connections:
        - name: eth0
          type: mgmt
          VNFC: TESTVIM-VNF1-VM
          local_iface_name: eth0
        - name: PF0
          type: data
          VNFC: TESTVIM-VNF1-VM
          local_iface_name: PF0
        - name: VF0
          type: data
          VNFC: TESTVIM-VNF1-VM
          local_iface_name: VF0
        VNFC: 
        - name: TESTVIM-VNF1-VM
          VNFC image: $VIM_TEST_IMAGE_PATH_NFV
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
    result=`openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF_2VMs.yaml "--image-path=$VIM_TEST_IMAGE_PATH_NFV,$VIM_TEST_IMAGE_PATH_NFV"`
    vnf=`echo $result |gawk '{print $1}'`
    ! is_valid_uuid $vnf && echo FAIL && echo "    $result" && $_exit 1
    echo $vnf
 
    printf "%-50s" "Creating VNF 'dataplaneVNF3.yaml': "
    result=`openmano vnf-create $DIRmano/vnfs/examples/dataplaneVNF3.yaml "--image-path=$VIM_TEST_IMAGE_PATH_NFV"`
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
      result=`openmano instance-scenario-create --scenario $sce --name ${sce}-instance`
      instance=`echo $result |gawk '{print $1}'`
      ! is_valid_uuid $instance && echo FAIL && echo "    $result" && $_exit 1
      echo $instance
    done

    echo
    echo DONE
fi
done


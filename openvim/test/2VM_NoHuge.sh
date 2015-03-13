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

#
#author Alfonso Tierno
#
#script to test openvim with the creation of flavors and interfaces
#in cloud style
#

echo " Creates 1 flavor, 3 nets, 2 VMs (US)
  WITHOUT huge pages, nor NUMA assigment
  network attach after creation"
echo
echo "Press enter to continue"
read kk

#image to load
imagePath=/mnt/powervault/virtualization/vnfs/os/US1404.qcow2
#image to load as an extra disk, can be any
imagePath_extra=/mnt/powervault/virtualization/vnfs/os/US1404user.qcow2
#default network to use
network_eth0=default


DIRNAME=`dirname $0`

function del_rubbish(){
  echo "Press enter to delete the deployed things"
  read kk
  [ -n "$DEL_server" ]  && ${DIRNAME}/test_openvim.py -f del server $DEL_server
  [ -n "$DEL_network" ] && ${DIRNAME}/test_openvim.py -f del network $DEL_network
  [ -n "$DEL_flavor" ]  && ${DIRNAME}/test_openvim.py -f del flavor $DEL_flavor
  [ -n "$DEL_image" ]   && ${DIRNAME}/test_openvim.py -f del image $DEL_image
  rm -f kk.out
}

function proccess_out(){ # action_text  field to retrieve
  if egrep -q "\"error\""  kk.out
  then
    echo "failed to" $1
    cat kk.out
    del_rubbish
    exit -1
  fi
  if [ -z "$2" ] ; then pattern='"id"' ; else pattern="$2" ; fi
  value=`egrep  "$pattern"  kk.out `
  value=${value##* \"}
  value=${value%\"*}
  if [[ -z "$value" ]]
  then 
    echo "not found the field" $2
    cat kk.out
    del_rubbish
    exit -1
  fi
}

#proccess_out "insert server tidgen1" '^            "id"'
#echo $value
#exit 0



echo -n "get ${imagePath##*/} image:                       "
${DIRNAME}/test_openvim.py -F"path=$imagePath" images > kk.out
proccess_out "get ${imagePath##*/}" 
echo $value
image1=$value


echo -n "get ${imagePath_extra##*/} image:                 "
${DIRNAME}/test_openvim.py -F"path=$imagePath_extra" images > kk.out
proccess_out "get ${imagePath_extra##*/}" 
echo $value
image2=$value


echo -n "get ${network_eth0} network:                 "
${DIRNAME}/test_openvim.py -F"name=$network_eth0" network > kk.out
proccess_out "get  ${network_eth0} network" 
echo $value
network_eth0=$value


echo -n "insert flavor:                                    "
${DIRNAME}/test_openvim.py new flavor '
---
flavor:
  name: CloudVM
  description: normal cloud image with 1G, 1core
  ram: 1024
  vcpus: 1
'  > kk.out
proccess_out "insert flavor" 
echo $value
flavor1=$value
DEL_flavor="$DEL_flavor $flavor1"


echo
echo "Press enter to continue"
read kk

echo -n "insert bridge network net2:                       "
${DIRNAME}/test_openvim.py new network '
---
network:
  name: network-bridge
  type: bridge_data
'  > kk.out
proccess_out "insert network 2"
echo $value
network2=$value
DEL_network="$DEL_network $value"

echo -n "insert test VM 1:                                 "
${DIRNAME}/test_openvim.py new server "
---
server:
  name: test_VM1
  descrition: US  1 core
  imageRef: '$image1'
  flavorRef: '$flavor1'
  networks:
  - name: mgmt0
    vpci: '0000:00:0a.0'
    uuid: ${network_eth0}
    mac_address: '10:10:10:10:10:12'
  - name: eth0
    vpci: '0000:00:0b.0'
    uuid: '$network2'
    mac_address: '10:10:10:10:10:13'
"  > kk.out
proccess_out "insert test VM 2" '^        "id"'
echo $value
server1=$value
DEL_server="$DEL_server $value"


echo
echo "Press enter to continue"
read kk

echo -n "insert test VM 2:                                 "
${DIRNAME}/test_openvim.py new server "
---
server:
  name: test_VM2
  descrition: US 1G 1core
  imageRef: '$image1'
  flavorRef: '$flavor1'
  ram: 1024
  vcpus: 1
  networks:
  - name: mgmt0
    vpci: '0000:00:0a.0'
    uuid: ${network_eth0}
    mac_address: '10:10:10:10:aa:12'
  - name: eth0
    vpci: '0000:00:0b.0'
    uuid: '$network2'
    mac_address: '10:10:10:10:aa:13'
  extended:
    devices:
    - type: disk
      imageRef: '$image2'
"  > kk.out
proccess_out "insert test VM 2" '^        "id"'
echo $value
server2=$value
DEL_server="$DEL_server $value"

echo 
echo finsish. Check connections!!
echo

del_rubbish
exit 0


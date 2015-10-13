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
#using images already inserted
#

function usage(){
    echo -e "usage: ${BASH_SOURCE[0]} [OPTIONS] \n  test openvim "
    echo -e "  OPTIONS:"
    echo -e "    -f --force       does not prompt for confirmation"
    echo -e "    -v --same-vlan   use this if the parameter 'of_controller_nets_with_same_vlan'"
    echo -e "                     is not false at openvimd.cfg to avoid test unrealizable openflow nets"
    echo -e "    -h --help        shows this help"
}

#detect if is called with a source to use the 'exit'/'return' command for exiting
[[ ${BASH_SOURCE[0]} != $0 ]] && echo "Do not execute this script as SOURCE" >&2 && return 1

#check correct arguments
force=n
same_vlan=n
for param in $*
do
   if [[ $param == -h ]] || [[ $param == --help ]]
   then
       usage
       exit 0
   elif [[ $param == -v ]] || [[ $param == --same-vlan ]]
   then
       same_vlan=y
   elif [[ $param == -f ]] || [[ $param == --force ]]
   then
       force=y
   else
       echo "invalid argument '$param'?" &&  usage >&2 && exit 1
   fi
done

#detect if environment variables are set
fail=""
[[ -z $VIM_TEST_NETWORK_INTERNET ]] && echo "VIM_TEST_NETWORK_INTERNET not defined" >&2 && fail=1
[[ -z $VIM_TEST_IMAGE_PATH ]] && echo "VIM_TEST_IMAGE_PATH not defined" >&2 && fail=1
[[ -z $VIM_TEST_IMAGE_PATH_EXTRA ]] && echo "VIM_TEST_IMAGE_PATH_EXTRA not defined" >&2 && fail=1
[[ -n $fail ]] && exit 1

TODELETE=""
export _exit=delete_and_exit

function delete_and_exit(){
  echo
  [[ $force != y ]] && read -e -p "  Press enter to delete the deployed things " kk
  echo
  for f in $TODELETE
  do
      openvim ${f%%:*}-delete  ${f##*:} -f
  done
  exit $1
}


function is_valid_uuid(){
    echo "$1" | grep -q -E '^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$' && return 0
    return 1
}

function process_cmd(){
  # test the result of the previos command, if fails execute the $_exit command
  # params:
  #   uuid <variable> <result...>  : test that the first word of <result> is a valid uuid, stored it at <variable>. Print uuid
  #   fail <reason>   <result...>  : test that the previous command has failed. If not print the <reason> why it needs to fail
  #   ok   <result...>             : test that the previos command has not failed. Print OK
  cmd_result=$?
  if [[ $1 == uuid ]]
  then
    [[ $cmd_result == 0 ]] || ! shift 2 || ! echo "FAIL: $*" >&2 || $_exit 1
    is_valid_uuid $3 || ! shift 2 || ! echo "FAIL: $*" >&2 || $_exit 1
    eval $2=$3
    echo $3
  elif [[ $1 == fail ]]
  then
    [[ $cmd_result != "0" ]] || ! echo "NOT FAIL:  $2" >&2 || $_exit 1
    echo "fail OK" 
  elif  [[ $1 == ok ]]
  then
    [[ $cmd_result == 0 ]] || ! shift 1 || ! echo "FAIL: $*" >&2 || $_exit 1
    echo OK
  fi

}

function test_of_rules(){
  #test the number of rules of a network, wait until 10 seconds
  timeout_=10
  while true 
  do #it can take some seconds to get it ready
    result=`openvim openflow-net-list $1`
    nb_rules=`echo $result | grep actions -o | wc -l`
    [[ $nb_rules == $2 ]] && echo "OK" && break
    [[ $timeout_ == 0 ]] && echo "FAIL $result" >&2 && $_exit 1  
    sleep 1
    timeout_=$((timeout_ - 1))
  done
}

echo " Test VIM with 3 VM deployments. It delete the created items at the end"
echo " "
[[ $force != y ]] && read -e -p "Press enter to continue, CTRL+C to abort " kk


printf "%-50s" "get ${VIM_TEST_IMAGE_PATH##*/} image: "
image1=`openvim image-list -F"path=${VIM_TEST_IMAGE_PATH}" | gawk '{print $1}'`
if is_valid_uuid $image1 
then
    echo $image1
else
    #create the image
    result=`openvim image-create --name=test-image1 --path=${VIM_TEST_IMAGE_PATH} --description=for-test`
    process_cmd uuid image1 $result
    TODELETE="image:$image1 $TODELETE"
fi
    
printf "%-50s" "get ${VIM_TEST_IMAGE_PATH_EXTRA##*/} image: "
image2=`openvim image-list -F"path=${VIM_TEST_IMAGE_PATH_EXTRA}" | gawk '{print $1}'`
if is_valid_uuid $image2 
then
    echo $image2
else
    #create the image
    result=`openvim image-create --name=test-image1 --path=${VIM_TEST_IMAGE_PATH_EXTRA} --description=for-test`
     process_cmd uuid image2 $result
    TODELETE="image:$image2 $TODELETE"
fi
    

printf "%-50s" "get ${VIM_TEST_NETWORK_INTERNET} network: "
result=`openvim net-list -F"name=$VIM_TEST_NETWORK_INTERNET"`
process_cmd uuid network_eth0 $result

echo -n "insert flavor:                                    "
result=`openvim flavor-create '
---
flavor:
  name: 5PTh_8G_2I
  description: flavor to test openvim
  extended: 
    processor_ranking: 205
    numas:
    -  memory: 8
       paired-threads: 5
       interfaces:
       - name: xe0
         dedicated: "yes"
         bandwidth: "10 Gbps"
         vpci: "0000:00:10.0"
         #mac_address: "10:10:10:10:10:12"
       - name: xe1
         dedicated: "no"
         bandwidth: "10 Gbps"
         vpci: "0000:00:11.0"
         mac_address: "10:10:10:10:10:13"
'`
process_cmd uuid flavor1 $result 
TODELETE="flavor:$flavor1 $TODELETE"

printf "%-50s" "insert net-ptp: "
result=`openvim net-create '
---
network:
  name: test_ptp_net
  type: ptp
'`
process_cmd uuid net_ptp  $result
TODELETE="net:$net_ptp $TODELETE"

printf "%-50s" "insert net-data: "
result=`openvim net-create '
---
network:
  name: test_data_net
  type: data
'`
process_cmd uuid net_data $result
TODELETE="net:$net_data $TODELETE"

printf "%-50s" "insert bridge network net2: "
result=`openvim net-create '
---
network:
  name: test_bridge_net2
  type: bridge_data
' | gawk '{print $1}'`
process_cmd uuid network2 $result
TODELETE="net:$network2 $TODELETE"

printf "%-50s" "add VM1 dataplane not connected: "
result=`openvim vm-create "
---
server:
  name: test_VM1
  descrition: US or server with 1 SRIOV 1 PASSTHROUGH
  imageRef: '$image1'
  flavorRef: '$flavor1'
  networks:
  - name: mgmt0
    vpci: '0000:00:0a.0'
    uuid: ${network_eth0}
    mac_address: '10:10:10:10:10:10'
  - name: eth0
    vpci: '0000:00:0b.0'
    uuid: '$network2'
    mac_address: '10:10:10:10:10:11'
"`
process_cmd uuid  server1 $result
TODELETE="vm:$server1 $TODELETE"

printf "%-50s" "add VM2 oversubscribe flavor: "
result=`openvim vm-create "
---
server:
  name: test_VM2
  descrition: US or server with direct network attach
  imageRef: '$image1'
  flavorRef: '$flavor1'
  networks:
  - name: mgmt0
    vpci: '0000:00:0a.0'
    uuid: ${network_eth0}
    mac_address: '10:10:10:10:11:10'
  - name: eth0
    vpci: '0000:00:0b.0'
    uuid: '$network2'
    mac_address: '10:10:10:10:11:11'
  extended:
    processor_ranking: 205
    numas:
    -  memory: 8
       threads: 10
       interfaces:
       - name: xe0
         dedicated: 'yes:sriov'
         bandwidth: '10 Gbps'
         vpci: '0000:00:11.0'
         mac_address: '10:10:10:10:11:12'
         uuid: '$net_ptp'
    devices:
    - type: disk
      imageRef: '$image2'
"`
process_cmd uuid  server2 $result
TODELETE="vm:$server2 $TODELETE"

printf "%-50s" "test VM with reapeted vpci: "
result=`openvim vm-create "
---
server:
  name: test_VMfail
  descrition: repeated mac address
  imageRef: '$image1'
  flavorRef: '$flavor1'
  networks:
  - name: mgmt0
    vpci: '0000:00:10.0'
    uuid: ${network_eth0}
"`
process_cmd fail "Duplicate vpci 0000:00:10.0" $result

printf "%-50s" "test VM with reapeted mac address: "
result=`openvim vm-create "
---
server:
  name: test_VMfail
  descrition: repeated mac address
  imageRef: '$image1'
  flavorRef: '$flavor1'
  networks:
  - name: mgmt0
    vpci: '0000:00:0a.0'
    uuid: ${network_eth0}
    mac_address: '10:10:10:10:10:10'
"`
process_cmd fail "Duplicate mac 10:10:10:10:10:10" $result


printf "%-50s" "test VM with wrong iface name at networks: "
result=`openvim vm-create "
---
server:
  name: test_VMfail
  descrition: repeated mac address
  imageRef: '$image1'
  flavorRef: '$flavor1'
  networks:
  - name: missing
    type: PF
    uuid: '$net_ptp'
"`
process_cmd fail "wrong iface name at networks" $result


printf "%-50s" "test VM with wrong iface type at networks: "
result=`openvim vm-create "
---
server:
  name: test_VMfail
  descrition: repeated mac address
  imageRef: '$image1'
  flavorRef: '$flavor1'
  networks:
  - name: xe0
    type: VF
    uuid: '$net_ptp'
"`
process_cmd fail "wrong iface type at networks" $result


printf "%-50s" "add VM3 dataplane connected: "
result=`openvim vm-create "
---
server:
  name: test_VM3
  descrition: US or server with 2 dataplane connected
  imageRef: '$image1'
  flavorRef: '$flavor1'
  networks:
  - name: mgmt0
    vpci: '0000:00:0a.0'
    uuid: ${network_eth0}
    mac_address: '10:10:10:10:12:10'
  - name: eth0
    vpci: '0000:00:0b.0'
    uuid: '$network2'
    type: virtual
    mac_address: '10:10:10:10:12:11'
  - name: xe0
    type: PF
    uuid: '$net_data'
  - name: xe1
    type: VF
    uuid: '$net_ptp'
    mac_address: '10:10:10:10:12:13'
"`
process_cmd uuid server3 $result
TODELETE="vm:$server3 $TODELETE"

printf "%-50s" "check openflow 2 ptp rules for net_ptp: "
test_of_rules $net_ptp 2

printf "%-50s" "check openflow 0 ptp rules for net_data: "
test_of_rules $net_data 0

[[ $force != y ]] && read -e -p "  Test control plane, and server2:xe0 to server3:xe1 connectivity. Press enter to continue " kk

printf "%-50s" "get xe0 iface uuid from server1: "
result=`openvim port-list -F"device_id=${server1}&name=xe0"`
process_cmd uuid server1_xe0 $result

printf "%-50s" "get xe1 iface uuid from server1: "
result=`openvim port-list -F"device_id=${server1}&name=xe1"`
process_cmd uuid server1_xe1 $result

printf "%-50s" "get xe0 iface uuid from server3: "
result=`openvim port-list -F"device_id=${server3}&name=xe0"`
process_cmd uuid server3_xe0 $result

printf "%-50s" "get xe1 iface uuid from server3: "
result=`openvim port-list -F"device_id=${server3}&name=xe1"`
process_cmd uuid server3_xe1 $result

printf "%-50s" "test ptp 3connex server1:xe0 -> net_ptp: "
result=`openvim port-edit $server1_xe0 "network_id: $net_ptp" -f`
process_cmd fail "Can not connect 3 interfaces to ptp network"

printf "%-50s" "attach server1:xe0 to net_data: "
result=`openvim port-edit $server1_xe0 "network_id: $net_data" -f | gawk '{print $1}'`
process_cmd ok $result

printf "%-50s" "check openflow 2 ptp rules for net_data: "
test_of_rules $net_data 2

[[ $force != y ]] && read -e -p "  Test server1:xe0 to server3:xe0 connectivity. Press enter to continue " kk

if [[ $same_vlan == n ]]
then

  printf "%-50s" "attach server1:xe1 to net-data: "
  result=`openvim port-edit $server1_xe1 "network_id: $net_data" -f | gawk '{print $1}'`
  process_cmd ok $result

  printf "%-50s" "check openflow 9 ptp rules for net_data: "
  test_of_rules $net_data 9

  [[ $force != y ]] && read -e -p "  Test server1:xe0,server1:xe1,server3:xe0 connectivity. Press enter to continue " kk

  printf "%-50s" "re-attach server3:xe1 to net-data: "
  result=`openvim port-edit $server3_xe1 "network_id: $net_data" -f | gawk '{print $1}'`
  process_cmd ok $result

  printf "%-50s" "check openflow 16 ptp rules for net_data: "
  test_of_rules $net_data 16

  printf "%-50s" "check openflow 0 ptp rules for net_ptp: "
  test_of_rules $net_ptp 0

  [[ $force != y ]] && read -e -p "  Test server1:xe0,server1:xe1,server3:xe0,server3:xe1 connectivity. Press enter to continue " kk
fi

echo 
echo DONE

$_exit 0


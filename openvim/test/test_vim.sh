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
#script to test openvim with the creation of flavors and interfaces, openflow rules
#using images already inserted
#

function usage(){
    echo -e "usage: ${BASH_SOURCE[0]} [OPTIONS] \n  test openvim "
    echo -e "  OPTIONS:"
    echo -e "    -f --force       does not prompt for confirmation"
    echo -e "    -v --same-vlan   use this if the parameter 'of_controller_nets_with_same_vlan'"
    echo -e "                     is not false at openvimd.cfg to avoid test unrealizable openflow nets"
    echo -e "    -h --help        shows this help"
    echo -e "    -c --create      create management network and two images (valid for test mode)"
    echo
    echo    "This script test openvim, creating flavors, images, vms, de-attaching dataplane port"
    echo    "from one network to other and testing openflow generated rules."
    echo    "By default (unless -c option) uses and already created management network and two valid images."
    echo    "If -c option is set, it creates the network and images with fake content (only usefull for"
    echo    "openvim in 'test' mode) This is speccified in this shell variables:"
    echo    "     VIM_TEST_NETWORK_INTERNET name of the mamagement network to use"
    echo    "     VIM_TEST_IMAGE_PATH       path of a vm image to use, the image is created if not exist"
    echo    "     VIM_TEST_IMAGE_PATH_EXTRA path of another vm image to use, the image is created if not exist"
}

#detect if is called with a source to use the 'exit'/'return' command for exiting
[[ ${BASH_SOURCE[0]} != $0 ]] && echo "Do not execute this script as SOURCE" >&2 && return 1

#check correct arguments
force=n
same_vlan=n
create=n
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
   elif [[ $param == -c ]] || [[ $param == --create ]]
   then
       create=y
   else
       echo "invalid argument '$param'?" &&  usage >&2 && exit 1
   fi
done

#detect if environment variables are set
fail=""
[[ $create == n ]] && [[ -z $VIM_TEST_NETWORK_INTERNET ]] && echo "VIM_TEST_NETWORK_INTERNET not defined" >&2 && fail=1
[[ $create == n ]] && [[ -z $VIM_TEST_IMAGE_PATH ]] && echo "VIM_TEST_IMAGE_PATH not defined" >&2 && fail=1
[[ $create == n ]] && [[ -z $VIM_TEST_IMAGE_PATH_EXTRA ]] && echo "VIM_TEST_IMAGE_PATH_EXTRA not defined" >&2 && fail=1
[[ -n $fail ]] && exit 1

[[ $create == y ]] && [[ -z $VIM_TEST_IMAGE_PATH ]] &&       VIM_TEST_IMAGE_PATH="/test/path/of/image1"
[[ $create == y ]] && [[ -z $VIM_TEST_IMAGE_PATH_EXTRA ]] && VIM_TEST_IMAGE_PATH_EXTRA="/test/path2/of/image2"
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


printf "%-50s" "1   get ${VIM_TEST_IMAGE_PATH##*/} image: "
image1=`openvim image-list -F"path=${VIM_TEST_IMAGE_PATH}" | gawk '{print $1}'`
if is_valid_uuid $image1 
then
    echo $image1
else
    #create the image
    echo not found
    printf "%-50s" " b  create ${VIM_TEST_IMAGE_PATH##*/} image: "
    result=`openvim image-create --name=test-image1 --path=${VIM_TEST_IMAGE_PATH} --description=for-test`
    process_cmd uuid image1 $result
    TODELETE="image:$image1 $TODELETE"
fi
    
printf "%-50s" "2   get ${VIM_TEST_IMAGE_PATH_EXTRA##*/} image: "
image2=`openvim image-list -F"path=${VIM_TEST_IMAGE_PATH_EXTRA}" | gawk '{print $1}'`
if is_valid_uuid $image2 
then
    echo $image2
else
    #create the image
    echo not found
    printf "%-50s" " b  create ${VIM_TEST_IMAGE_PATH_EXTRA##*/} image: "
    result=`openvim image-create --name=test-image1 --path=${VIM_TEST_IMAGE_PATH_EXTRA} --description=for-test`
    process_cmd uuid image2 $result
    TODELETE="image:$image2 $TODELETE"
fi
    
if [[ $create == y ]]
then
    printf "%-50s" "3   create management network: "
    result=`openvim net-create "name: test_mgmt_net
type: bridge_man"`
    process_cmd uuid network_eth0 $result
    TODELETE="net:$network_eth0 $TODELETE"
else
    printf "%-50s" "3   get ${VIM_TEST_NETWORK_INTERNET} network: "
    result=`openvim net-list -F"name=$VIM_TEST_NETWORK_INTERNET"`
    process_cmd uuid network_eth0 $result
fi

printf "%-50s" "4   insert flavor1: "
result=`openvim flavor-create '
---
flavor:
  name: flavor1
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

printf "%-50s" "5   insert net_ptp: "
result=`openvim net-create '
---
network:
  name: test_net_ptp
  type: ptp
'`
process_cmd uuid net_ptp  $result
TODELETE="net:$net_ptp $TODELETE"

printf "%-50s" " b  insert net_data: "
result=`openvim net-create '
---
network:
  name: test_net_data
  type: data
'`
process_cmd uuid net_data $result
TODELETE="net:$net_data $TODELETE"

printf "%-50s" "6   insert net_bind network bound to net_data: "
result=`openvim net-create 'name: test_net_binded
type: data
bind_net: test_net_data'`
process_cmd uuid net_bind $result
TODELETE="net:$net_bind $TODELETE"

printf "%-50s" "7   insert bridge network net2: "
result=`openvim net-create '
---
network:
  name: test_bridge_net2
  type: bridge_data'`
process_cmd uuid network2 $result
TODELETE="net:$network2 $TODELETE"

printf "%-50s" "8   add VM1 dataplane not connected: "
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

printf "%-50s" "9   add VM2 oversubscribe flavor: "
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

printf "%-50s" "10  test VM with repeated vpci: "
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

printf "%-50s" " b  test VM with repeated mac address: "
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


printf "%-50s" " c  test VM with wrong iface name at networks: "
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


printf "%-50s" " d  test VM with wrong iface type at networks: "
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


printf "%-50s" "11  add VM3 dataplane connected: "
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

printf "%-50s" "12  check 2 openflow rules for net_ptp: "
test_of_rules $net_ptp 2

printf "%-50s" "13  check net-down  net_ptp: "
result=`openvim net-down -f ${net_ptp}`
process_cmd ok $result

printf "%-50s" " b  check 0 openflow rules for net_ptp: "
test_of_rules $net_ptp 0

printf "%-50s" " c  check net-up  net_ptp: "
result=`openvim net-up -f ${net_ptp}`
process_cmd ok $result

printf "%-50s" " d  check 2 openflow rules for net_ptp: "
test_of_rules $net_ptp 2

printf "%-50s" "14  check 0 openflow rules for net_data: "
test_of_rules $net_data 0

[[ $force != y ]] && read -e -p "  Test control plane, and server2:xe0 to server3:xe1 connectivity. Press enter to continue " kk

printf "%-50s" "15  get xe0 iface uuid from server1: "
result=`openvim port-list -F"device_id=${server1}&name=xe0"`
process_cmd uuid server1_xe0 $result

printf "%-50s" " b  get xe1 iface uuid from server1: "
result=`openvim port-list -F"device_id=${server1}&name=xe1"`
process_cmd uuid server1_xe1 $result

printf "%-50s" " c  get xe0 iface uuid from server3: "
result=`openvim port-list -F"device_id=${server3}&name=xe0"`
process_cmd uuid server3_xe0 $result

printf "%-50s" " d  get xe1 iface uuid from server3: "
result=`openvim port-list -F"device_id=${server3}&name=xe1"`
process_cmd uuid server3_xe1 $result

printf "%-50s" " e  get xe0 iface uuid from server3: "
result=`openvim port-list -F"device_id=${server2}&name=xe0"`
process_cmd uuid server2_xe0 $result

printf "%-50s" "16  test ptp 3connex server1:xe0 -> net_ptp: "
result=`openvim port-edit $server1_xe0 "network_id: $net_ptp" -f`
process_cmd fail "Can not connect 3 interfaces to ptp network"

printf "%-50s" "17  attach server1:xe0 to net_data: "
result=`openvim port-edit $server1_xe0 "network_id: $net_data" -f`
process_cmd ok $result

printf "%-50s" "18  check 2 openflow rules for net_data: "
test_of_rules $net_data 2

[[ $force != y ]] && read -e -p "  Test server1:xe0 to server3:xe0 connectivity. Press enter to continue " kk

if [[ $same_vlan == n ]]
then

  printf "%-50s" "19  attach server1:xe1 to net-data: "
  result=`openvim port-edit $server1_xe1 "network_id: $net_data" -f`
  process_cmd ok $result

  printf "%-50s" " b  check 9 openflow rules for net_data: "
  test_of_rules $net_data 9

  [[ $force != y ]] && read -e -p "  Test server1:xe0,server1:xe1,server3:xe0 connectivity. Press enter to continue " kk

  printf "%-50s" " c  re-attach server3:xe1 to net-data: "
  result=`openvim port-edit $server3_xe1 "network_id: $net_data" -f`
  process_cmd ok $result

  printf "%-50s" " d  check 16 openflow rules for net_data: "
  test_of_rules $net_data 16

  printf "%-50s" " e  check 0 openflow rules for net_ptp: "
  test_of_rules $net_ptp 0

  [[ $force != y ]] && read -e -p "  Test server1:xe0,server1:xe1,server3:xe0,server3:xe1 connectivity. Press enter to continue " kk

  printf "%-50s" " f  detach server1:xe1 from net-data: "
  result=`openvim port-edit $server1_xe1 "network_id: null" -f `
  process_cmd ok $result

  printf "%-50s" " g  detach server3:xe1 to net-data: "
  result=`openvim port-edit $server3_xe1 "network_id: null" -f`
  process_cmd ok $result

  printf "%-50s" " h  check 2 openflow rules for net_data: "
  test_of_rules $net_data 2

else
  echo "19  skipping unrealizable test because --same_vlan option "
fi

printf "%-50s" "20  check 2 openflow rules for net_data: "
test_of_rules $net_data 2

printf "%-50s" " a  attach server2:xe0 to net_bind: "
result=`openvim port-edit $server2_xe0 "network_id: $net_bind" -f`
process_cmd ok $result

printf "%-50s" " b  check 6 openflow rules for net_data: "
   #type      src_net	   src_port    => dst_port       dst_net
   #unicast   net_data     server1:xe0 => server3:xe0    net_data
   #unicast   net_data     server3:xe0 => server1:xe0    net_data
   #unicast   net_data     server1:xe0 => server2:xe0    net_bind
   #unicast   net_data     server3:xe0 => server2:xe0    net_bind
   #broadcast net_data     server1:xe0 => server3:xe0,server2:xe0    net_data,net_bind
   #broadcast net_data     server3:xe0 => server1:xe0,server2:xe0    net_data,net_bind
test_of_rules $net_data 6


printf "%-50s" " c  check 3 openflow rules for net_bind: "
   #type      src_net	   src_port    => dst_port       dst_net
   #unicast   net_bind     server2:xe0 => server1:xe0    net_data
   #unicast   net_bind     server2:xe0 => server3:xe0    net_data
   #broadcast net_bind     server2:xe0 => server1:xe0,server3:xe0    net_data,net_data
test_of_rules $net_bind 3

printf "%-50s" " d  attach server1:xe1 to net_bind: "
result=`openvim port-edit $server1_xe1 "network_id: $net_bind" -f`
process_cmd ok $result

printf "%-50s" " e  check 8 openflow rules for net_data: "
   #type      src_net      src_port    => dst_port       dst_net
   #unicast   net_data     server1:xe0 => server3:xe0    net_data
   #unicast   net_data     server3:xe0 => server1:xe0    net_data
   #unicast   net_data     server1:xe0 => server2:xe0    net_bind
   #unicast   net_data     server1:xe0 => server1:xe1    net_bind
   #unicast   net_data     server3:xe0 => server2:xe0    net_bind
   #unicast   net_data     server3:xe0 => server1:xe1    net_bind
   #broadcast net_data     server1:xe0 => server3:xe0,server2:xe0,server1:xe1    net_data,net_bind,net_bind
   #broadcast net_data     server3:xe0 => server1:xe0,server2:xe0,server1:xe1    net_data,net_bind,net_bind
test_of_rules $net_data 8


printf "%-50s" " f  check 8 openflow rules for net_bind: "
test_of_rules $net_bind 8

printf "%-50s" " d  put net_data down: "
result=`openvim net-down $net_data -f`
process_cmd ok $result

printf "%-50s" " e  check 0 openflow rules for net_data: "
test_of_rules $net_data 0

printf "%-50s" " e  check 2 openflow rules for net_bind: "
test_of_rules $net_bind 2



echo 
echo DONE

$_exit 0


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

#Get configuration of a host for using it as a compute node

function usage(){
    echo  -e "usage: $0 user ip_name nb_cores GiB_memory nb_10GB_interfaces [hostname] [>> host.yaml]\n  Get host parameters and generated a yaml file to be used for openvim host-add"
    echo -e "  - In case hostname is not specified it will be used the name of the machine where the script is run"
    echo -e "  - nb_cores must be an odd number and bigger or equal to 4."
    echo -e "  - GiB_memory must be an odd number and bigger or equal to 16. 4GiB of memory will be reserved for the host OS, the rest will be used by VM."
    echo -e "  - nb_10GB_interfaces must be an odd number and bigger or equal to 4."
    echo -e "  - The output will be a server descriptor with two numas and resources (memory, cores and interfaces) equally distributed between them."
    echo -e "  - Each interface (physical funtion) will have defined 8 SR-IOV (virtual functions)."
    exit 1
}

function get_hash_value() {   echo `eval  echo $\{\`echo $1[$2]\`\}`; }

function get_mac(){
  seed=$1
  b1=$((seed%16)); seed=$((seed/16))
  b2=$((seed%16)); seed=$((seed/16))
  b3=$((seed%16)); seed=$((seed/16))
  b4=$((seed%16)); seed=$((seed/16))
  b5=$((seed%16)); seed=$((seed/16))
  mac=`printf "%02X:%02X:%02X:%02X:%02X:%02X" 2 $b5 $b4 $b3 $b2 $b1`
  echo $mac
}


#check root privileges and non a root user behind

[ "$#" -lt "5" ] && echo "Missing parameters" && usage
[ "$#" -gt "6" ] && echo "Too many parameters" && usage
HOST_NAME=`cat /etc/hostname`
[ "$#" -eq "6" ] && HOST_NAME=$6
FEATURES_LIST="lps,dioc,hwsv,tlbps,ht,lps,64b,iommu"
NUMAS=2
CORES=$3
MEMORY=$4
INTERFACES=$5

#Ensure the user input is big enough
([ $((CORES%2)) -ne 0 ] || [ $CORES -lt 4 ] ) && echo -e "ERROR: Wrong number of cores\n" && usage
([ $((MEMORY%2)) -ne 0 ] || [ $MEMORY -lt 16 ] ) && echo -e "ERROR: Wrong number of memory\n" && usage
([ $((INTERFACES%2)) -ne 0 ] || [ $INTERFACES -lt 4 ] ) && echo -e "ERROR: Wrong number of interfaces\n" && usage

#Generate a cpu topology for 4 numas with hyperthreading
CPUS=`pairs_gap=$((CORES/NUMAS));numa=0;inc=0;sibling=0;for((thread=0;thread<=$((pairs_gap-1));thread++)); do printf " ${numa}-${sibling}-${thread} ${numa}-${sibling}-$((thread+pairs_gap))";numa=$(((numa+1)%$NUMAS)); sibling=$((sibling+inc)); inc=$(((inc+1)%2));  done`     

#in this developing/fake server all cores can be used

echo "#This file was created by $0"
echo "#for adding this compute node to openvim"
echo "#copy this file to openvim controller and run"
echo "#openvim host-add <this>"
echo
echo "host:"
echo "  name:    $HOST_NAME"
echo "  user:    $1"
echo "  ip_name: $2"
echo "host-data:"
echo "  name:        $HOST_NAME"
echo "  user:        $1"
echo "  ip_name:     $2"
echo "  ranking:     100"
echo "  description: $HOST_NAME"
echo "  features:    $FEATURES_LIST"
echo "  numas:"

numa=0
last_iface=0
iface_counter=0
while [ $numa -lt $NUMAS ]
do
  echo "  - numa_socket:  $numa"
#MEMORY
  echo "    hugepages: $((MEMORY/2-2))"
  echo "    memory:    $((MEMORY/2))"

#CORES
  echo "    cores:"
  for cpu in $CPUS
  do
    PHYSICAL=`echo $cpu | cut -f 1 -d"-"`
    CORE=`echo $cpu | cut -f 2 -d"-"`
    THREAD=`echo $cpu | cut -f 3 -d"-"`
    [ $PHYSICAL != $numa ] && continue   #skip non physical
    echo "    - core_id:   $CORE"
    echo "      thread_id: $THREAD"
    [ $CORE -eq 0 ] && echo "      status:    noteligible"
  done
 

  #GENERATE INTERFACES INFORMATION AND PRINT IT
  seed=$RANDOM
  echo "    interfaces:"
  for ((iface=0;iface<$INTERFACES;iface+=2))
  do
    name="iface$iface_counter"
    bus=$((iface+last_iface))
    pci=`printf "0000:%02X:00.0" $bus`
    mac=`get_mac $seed`
    seed=$((seed+1))
  
    echo "    - source_name: $name"
    echo "      Mbps: 10000"
    echo "      pci: \"$pci\""
    echo "      mac: \"$mac\""
    echo "      switch_dpid: \"01:02:03:04:05:06\""
    echo "      switch_port: fake0/$iface_counter"
    echo "      sriovs:"

    for((nb_sriov=0;nb_sriov<8;nb_sriov++))
    do
      pci=`printf "0000:%02X:10.%i" $bus $nb_sriov`
      mac=`get_mac $seed`
      seed=$((seed+1))
      echo "      - mac: \"$mac\""
      echo "        pci: \"$pci\""
      echo "        source_name: $nb_sriov"
    done
  
  iface_counter=$((iface_counter+1))
  done
  last_iface=$(((numa+1)*127/NUMAS+5)) #made-up formula for more realistic pci numbers 
  

  numa=$((numa+1))
done


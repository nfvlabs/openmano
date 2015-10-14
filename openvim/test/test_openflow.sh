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
#script to test openflow connector with the creation of rules
#

function usage(){
    echo -e "usage: ${BASH_SOURCE[0]} [OPTIONS] \n  test openflow connector "
    echo -e "  OPTIONS:"
    echo -e "    -f --force       does not prompt for confirmation"
    echo -e "    -v --same-vlan   use this if the parameter 'of_controller_nets_with_same_vlan'"
    echo -e "                     is not false at openvimd.cfg to avoid test unrealizable openflow nets"
    echo -e "    -d --debug       show debug information at each command. It is quite verbose"
    echo -e "    -h --help        shows this help"
}


function delete_and_exit(){
  echo
  [[ $force != y ]] && read -e -p "  Press enter to delete the deployed things " kk
  echo
  for f in $TODELETE
  do
    if [[ $f == restore ]]
    then
      printf "%-50s" "restoring back old rules: "
      result=`openflow install ./test_openflow_old_rules.bk $debug `
      if [[ $? != 0 ]]
      then 
        echo  "FAIL cannot install old rules:"
        echo  "$result"
      else
        rm ./test_openflow_old_rules.bk
        echo OK "./test_openflow_old_rules.bk deleted"
      fi
    else
      printf "%-50s" "removing $f rule: "
      result=`openflow delete  $f -f $debug`
      [[ $? != 0 ]] && echo  "FAIL cannot delete" &&  echo  "$result" || echo OK
    fi
  done
  exit $1
}

force=n
same_vlan=n
debug=""
TODELETE=""
#detect if is called with a source to use the 'exit'/'return' command for exiting
[[ ${BASH_SOURCE[0]} != $0 ]] && echo "Do not execute this script as SOURCE" >&2 && return 1

#check correct arguments
for param in $*
do
   if [[ $param == -h ]] || [[ $param == --help ]]
   then
       usage
       exit 0
   elif [[ $param == -d ]] || [[ $param == --debug ]]
   then
       debug="--debug"
   elif [[ $param == -v ]] || [[ $param == --same-vlan ]]
   then
       same_vlan=y
   elif [[ $param == -f ]] || [[ $param == --force ]]
   then
       force=y
   else
       echo "invalid argument '$param'?. See $0 --help" && exit 1
   fi
done

#detect if environment variables are set
fail=""
[[ -z $OF_CONTROLLER_TYPE ]] && echo "OF_CONTROLLER_TYPE not defined" >&2 && fail=1
[[ -z $OF_CONTROLLER_IP ]] &&   echo "OF_CONTROLLER_IP not defined" >&2 && fail=1
[[ -z $OF_CONTROLLER_PORT ]] && echo "OF_CONTROLLER_PORT not defined" >&2 && fail=1
[[ -z $OF_CONTROLLER_DPID ]] && echo "OF_CONTROLLER_DPID not defined" >&2 && fail=1
[[ -n $fail ]] && exit 1


export _exit=delete_and_exit
if [[ $force != y ]]
then
  echo " This will remove temporally the existing openflow rules and restored back a the end"
  read -e -p "Press enter to continue, CTRL+C to abort " kk
fi


printf "%-50s" "obtain port list: "
result=`openflow port-list $debug | gawk '/^ /{print substr($1,0,length($1)-1)}'`
[[ $? != 0 ]] && echo  "FAIL" && echo "$result" && $_exit 1
ports=`echo $result | wc -w`
[[ $ports -lt 4 ]] && echo  "FAIL not enough ports managed by this DPID, needed at least 4" && $_exit 1
echo OK $ports ports
port0=`echo $result | cut -d" " -f1`
port1=`echo $result | cut -d" " -f2`
port2=`echo $result | cut -d" " -f3`
port3=`echo $result | cut -d" " -f4`


printf "%-50s" "saving the current rules: "
openflow list $debug > ./test_openflow_old_rules.bk
[[ $? != 0 ]] && echo  "FAIL cannot obtain existing rules" && $_exit 1
echo OK "> ./test_openflow_old_rules.bk"

printf "%-50s" "clearing all current rules: "
openflow clear -f $debug 
[[ $? != 0 ]] && echo  "FAIL cannot clear existing rules" && $_exit 1
result=`openflow list | wc -l`
[[ $result != 1 ]] && echo  "FAIL rules not completely cleared" && $_exit 1
echo OK
TODELETE="restore"

printf "%-50s" "clearing again all rules: "
openflow clear -f $debug
[[ $? != 0 ]] && echo  "FAIL when there are not any rules" && $_exit 1
result=`openflow list | wc -l`
[[ $result != 1 ]] && echo  "FAIL rules not completely cleared" && $_exit 1
echo OK
TODELETE="restore"


printf "%-50s" "new rule vlan,mac -> no vlan: "
rule_name=fromVlanMac_to_NoVlan1
openflow add $rule_name --priority 1000 --matchmac "aa:bb:cc:dd:ee:ff" --matchvlan 500 --inport $port0 --stripvlan --out $port1 $debug 
[[ $? != 0 ]] && echo  "FAIL cannot insert new rule" && $_exit 1
expected="$OF_CONTROLLER_DPID 1000 $rule_name $port0 aa:bb:cc:dd:ee:ff 500 vlan=None,out=$port1"
result=`openflow list | grep $rule_name`
[[ $? != 0 ]] && echo  "FAIL rule bad inserted"  && $_exit 1
result=`echo $result` #remove blanks
[[ "$result" != "$expected" ]]  && echo "FAIL" && echo "    expected: $expected\n    obtained: $result" && $_exit 1
echo OK $rule_name
TODELETE="$rule_name $TODELETE"

printf "%-50s" "new rule mac -> vlan: "
rule_name=fromMac_to_Vlan2
openflow add $rule_name --priority 1001 --matchmac "ff:ff:ff:ff:ff:ff" --inport $port1 --setvlan 501 --out $port2 --out $port3 $debug 
[[ $? != 0 ]] && echo  "FAIL cannot insert new rule" && $_exit 1
expected="$OF_CONTROLLER_DPID 1001 $rule_name $port1 ff:ff:ff:ff:ff:ff any vlan=501,out=$port2,out=$port3"
result=`openflow list | grep $rule_name`
[[ $? != 0 ]] && echo  "FAIL rule bad inserted"  && $_exit 1
result=`echo $result` #remove blanks
[[ "$result" != "$expected" ]]  && echo "FAIL" && echo "    expected: $expected\n    obtained: $result"  && $_exit 1
echo OK  $rule_name
TODELETE="$rule_name $TODELETE"

printf "%-50s" "new rule None -> None: "
rule_name=fromNone_to_None
openflow add $rule_name --priority 1002 --inport $port2 --out $port0 $debug 
[[ $? != 0 ]] && echo  "FAIL cannot insert new rule" && $_exit 1
expected="$OF_CONTROLLER_DPID 1002 $rule_name $port2 any any out=$port0"
result=`openflow list | grep $rule_name`
[[ $? != 0 ]] && echo  "FAIL rule bad inserted" && $_exit 1
result=`echo $result` #remove blanks
[[ "$result" != "$expected" ]]  && echo "FAIL" && echo "    expected: $expected\n    obtained: $result" && $_exit 1
echo OK $rule_name
TODELETE="$rule_name $TODELETE"

printf "%-50s" "new rule vlan -> vlan: "
rule_name=fromVlan_to_Vlan1
openflow add $rule_name --priority 1003 --matchvlan 504 --inport $port3 --setvlan 505 --out $port0 $debug 
[[ $? != 0 ]] && echo  "FAIL cannot insert new rule" && $_exit 1
expected="$OF_CONTROLLER_DPID 1003 $rule_name $port3 any 504 vlan=505,out=$port0"
result=`openflow list | grep $rule_name`
[[ $? != 0 ]] && echo  "FAIL rule bad inserted" && $_exit 1
result=`echo $result` #remove blanks
[[ "$result" != "$expected" ]]  && echo "FAIL" && echo "    expected: $expected\n    obtained: $result"  && $_exit 1
echo OK $rule_name
TODELETE="$rule_name $TODELETE"


if [[ $same_vlan == n ]]
then

  printf "%-50s" "new rule Vlan -> Vlan_Vlan: "
  rule_name=fromVlan_to_Vlan1Vlan1
  openflow add $rule_name --priority 1005 --inport $port3 --matchvlan 505 --setvlan 510 --out $port0 --setvlan 511 --out $port1 --stripvlan --out=$port2 $debug 
  [[ $? != 0 ]] && echo  "FAIL cannot insert new rule" && $_exit 1
  expected="$OF_CONTROLLER_DPID 1005 $rule_name $port3 any 505 vlan=510,out=$port0,vlan=511,out=$port1,vlan=None,out=$port2"
  result=`openflow list | grep $rule_name`
  [[ $? != 0 ]] && echo  "FAIL rule bad inserted" && $_exit 1
  result=`echo $result` #remove blanks
  [[ "$result" != "$expected" ]]  && echo "FAIL" && echo "    expected: $expected\n    obtained: $result" && $_exit 1
  echo OK $rule_name
  TODELETE="$rule_name $TODELETE"

fi

echo 
echo DONE

$_exit 0


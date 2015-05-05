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

#It generates a report for debugging

DIRNAME=`dirname $0`
OMCLIENT=$DIRNAME/../openmano/openmano
OVCLIENT=$DIRNAME/../openvim/openvim
verbose=""
echo "-------------------------------"
echo "OPENMANO"
echo "-------------------------------"
echo "$OMCLIENT config"
$OMCLIENT config
echo "-------------------------------"
echo "$OMCLIENT tenant-list"
$OMCLIENT tenant-list $verbose
echo "-------------------------------"
echo "$OMCLIENT datacenter-list --all"
$OMCLIENT datacenter-list --all
echo "-------------------------------"
echo "$OMCLIENT datacenter-list"
$OMCLIENT datacenter-list $verbose
echo "-------------------------------"
dclist=`$OMCLIENT datacenter-list |awk '{print $1}'`
for dc in $dclist; do
  echo "$OMCLIENT datacenter-net-list $dc $verbose"
  $OMCLIENT datacenter-net-list $dc $verbose
  echo "-------------------------------"
done
echo "$OMCLIENT vnf-list"
$OMCLIENT vnf-list $verbose
echo "-------------------------------"
echo "$OMCLIENT scenario-list"
$OMCLIENT scenario-list $verbose
echo "-------------------------------"
echo "$OMCLIENT instance-scenario-list"
$OMCLIENT instance-scenario-list $verbose
echo "-------------------------------"
echo
echo "-------------------------------"
echo "OPENVIM"
echo "-------------------------------"
echo "$OVCLIENT config"
$OVCLIENT config
echo "-------------------------------"
echo "$OVCLIENT tenant-list"
$OVCLIENT tenant-list $verbose
echo "-------------------------------"
echo "$OVCLIENT host-list"
$OVCLIENT host-list $verbose
echo "-------------------------------"
echo "$OVCLIENT net-list"
$OVCLIENT net-list $verbose
echo "-------------------------------"
echo "$OVCLIENT port-list"
$OVCLIENT port-list $verbose
echo "-------------------------------"
echo "$OVCLIENT flavor-list"
$OVCLIENT flavor-list $verbose
echo "-------------------------------"
echo "$OVCLIENT image-list"
$OVCLIENT image-list $verbose
echo "-------------------------------"
echo "$OVCLIENT vm-list"
$OVCLIENT vm-list $verbose
echo "-------------------------------"
echo
echo "-------------------------------"
echo "Verbose"
echo "-------------------------------"
verbose="-vvv"
echo "-------------------------------"
echo "OPENMANO"
echo "-------------------------------"
echo "$OMCLIENT config"
$OMCLIENT config
echo "-------------------------------"
echo "$OMCLIENT tenant-list"
$OMCLIENT tenant-list $verbose
echo "-------------------------------"
echo "$OMCLIENT datacenter-list --all"
$OMCLIENT datacenter-list --all
echo "-------------------------------"
echo "$OMCLIENT datacenter-list"
$OMCLIENT datacenter-list $verbose
echo "-------------------------------"
dclist=`$OMCLIENT datacenter-list |awk '{print $1}'`
for dc in $dclist; do
  echo "$OMCLIENT datacenter-net-list $dc $verbose"
  $OMCLIENT datacenter-net-list $dc $verbose
  echo "-------------------------------"
done
echo "$OMCLIENT vnf-list"
$OMCLIENT vnf-list $verbose
echo "-------------------------------"
echo "$OMCLIENT scenario-list"
$OMCLIENT scenario-list $verbose
echo "-------------------------------"
echo "$OMCLIENT instance-scenario-list"
$OMCLIENT instance-scenario-list $verbose
echo "-------------------------------"
echo
echo "-------------------------------"
echo "OPENVIM"
echo "-------------------------------"
echo "$OVCLIENT config"
$OVCLIENT config
echo "-------------------------------"
echo "$OVCLIENT tenant-list"
$OVCLIENT tenant-list $verbose
echo "-------------------------------"
echo "$OVCLIENT host-list"
$OVCLIENT host-list $verbose
echo "-------------------------------"
echo "$OVCLIENT net-list"
$OVCLIENT net-list $verbose
echo "-------------------------------"
echo "$OVCLIENT port-list"
$OVCLIENT port-list $verbose
echo "-------------------------------"
echo "$OVCLIENT flavor-list"
$OVCLIENT flavor-list $verbose
echo "-------------------------------"
echo "$OVCLIENT image-list"
$OVCLIENT image-list $verbose
echo "-------------------------------"
echo "$OVCLIENT vm-list"
$OVCLIENT vm-list $verbose
echo "-------------------------------"
echo
echo "-------------------------------"
echo "Configuration files"
echo "-------------------------------"
echo "-------------------------------"
echo "OPENMANO"
echo "-------------------------------"
echo "cat $DIRNAME/../openmano/openmanod.cfg"
cat $DIRNAME/../openmano/openmanod.cfg
echo "-------------------------------"
echo "OPENVIM"
echo "-------------------------------"
echo "cat $DIRNAME/../openvim/openvimd.cfg"
cat $DIRNAME/../openvim/openvimd.cfg
echo "-------------------------------"


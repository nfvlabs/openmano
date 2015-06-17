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

DIRNAME=$(readlink -f ${BASH_SOURCE[0]})
DIRNAME=$(dirname $DIRNAME )
OMCLIENT=$DIRNAME/../openmano/openmano
OVCLIENT=$DIRNAME/../openvim/openvim

#get screen log files at the beginning
echo
echo "-------------------------------"
echo "log files"
echo "-------------------------------"
echo "-------------------------------"
echo "OPENMANO"
echo "-------------------------------"
echo "cat $DIRNAME/../logs/openmano.?"
cat $DIRNAME/../logs/openmano.?
echo
echo "-------------------------------"
echo "OPENVIM"
echo "-------------------------------"
echo "cat $DIRNAME/../logs/openvim.?"
cat $DIRNAME/../logs/openvim.?
echo
echo "-------------------------------"
echo

#get version
echo
echo "-------------------------------"
echo "version"
echo "-------------------------------"
echo "-------------------------------"
echo "OPENMANO"
echo "-------------------------------"
echo "cat $DIRNAME/../openmano/openmanod.py|grep ^__version__"
cat $DIRNAME/../openmano/openmanod.py|grep ^__version__
echo
echo "-------------------------------"
echo "OPENVIM"
echo "-------------------------------"
echo "cat $DIRNAME/../openvim/openvimd.py|grep ^__version__"
cat $DIRNAME/../openvim/openvimd.py|grep ^__version__
echo
echo "-------------------------------"
echo

#get configuration files
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
echo

#get list of items
for verbose in "" "-vvv"
do
  echo "-------------------------------"
  echo "OPENMANO$verbose"
  echo "-------------------------------"
  echo "$OMCLIENT config $verbose"
  $OMCLIENT config
  echo "-------------------------------"
  echo "$OMCLIENT tenant-list $verbose"
  $OMCLIENT tenant-list $verbose
  echo "-------------------------------"
  echo "$OMCLIENT datacenter-list --all"
  $OMCLIENT datacenter-list --all
  echo "-------------------------------"
  echo "$OMCLIENT datacenter-list $verbose"
  $OMCLIENT datacenter-list $verbose
  echo "-------------------------------"
  dclist=`$OMCLIENT datacenter-list |awk '{print $1}'`
  for dc in $dclist; do
    echo "$OMCLIENT datacenter-net-list $dc $verbose"
    $OMCLIENT datacenter-net-list $dc $verbose
    echo "-------------------------------"
  done
  echo "$OMCLIENT vnf-list $verbose"
  $OMCLIENT vnf-list $verbose
  echo "-------------------------------"
  vnflist=`$OMCLIENT vnf-list |awk '$1!="No" {print $1}'`
  for vnf in $vnflist; do
    echo "$OMCLIENT vnf-list $vnf $verbose"
    $OMCLIENT vnf-list $vnf $verbose
    echo "-------------------------------"
  done
  echo "$OMCLIENT scenario-list $verbose"
  $OMCLIENT scenario-list $verbose
  echo "-------------------------------"
  scenariolist=`$OMCLIENT scenario-list |awk '$1!="No" {print $1}'`
  for sce in $scenariolist; do
    echo "$OMCLIENT scenario-list $sce $verbose"
    $OMCLIENT scenario-list $sce $verbose
    echo "-------------------------------"
  done
  echo "$OMCLIENT instance-scenario-list $verbose"
  $OMCLIENT instance-scenario-list $verbose
  echo "-------------------------------"
  instancelist=`$OMCLIENT instance-scenario-list |awk '$1!="No" {print $1}'`
  for i in $instancelist; do
    echo "$OMCLIENT instance-scenario-list $i $verbose"
    $OMCLIENT instance-scenario-list $i $verbose
    echo "-------------------------------"
  done
  echo
  echo "-------------------------------"
  echo "OPENVIM$verbose"
  echo "-------------------------------"
  echo "$OVCLIENT config"
  $OVCLIENT config
  echo "-------------------------------"
  echo "$OVCLIENT tenant-list $verbose"
  $OVCLIENT tenant-list $verbose
  echo "-------------------------------"
  echo "$OVCLIENT host-list $verbose"
  $OVCLIENT host-list $verbose
  echo "-------------------------------"
  echo "$OVCLIENT net-list $verbose"
  $OVCLIENT net-list $verbose
  echo "-------------------------------"
  echo "$OVCLIENT port-list $verbose"
  $OVCLIENT port-list $verbose
  echo "-------------------------------"
  echo "$OVCLIENT flavor-list $verbose"
  $OVCLIENT flavor-list $verbose
  echo "-------------------------------"
  echo "$OVCLIENT image-list $verbose"
  $OVCLIENT image-list $verbose
  echo "-------------------------------"
  echo "$OVCLIENT vm-list $verbose"
  $OVCLIENT vm-list $verbose
  echo "-------------------------------"
  echo

done
echo

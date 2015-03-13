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
#script that obtain the parameters from the configuration file
#it is a bit unsafe because a comment in the yaml configuration file
#can wrong this script  

#get params from configuration file

[ -z "$1" ] && echo "usage: $0 [openvim_cfg_file]" && exit

OPENVIM_PORT=`grep http_port: $1`
OPENVIM_PORT=${OPENVIM_PORT#http_port:}
OPENVIM_PORT=${OPENVIM_PORT%%#*}
OPENVIM_PORT=`eval echo ${OPENVIM_PORT}`  # remove white spaces

OPENVIM_ADMIN_PORT=`grep http_admin_port: $1`
OPENVIM_ADMIN_PORT=${OPENVIM_ADMIN_PORT#http_admin_port:}
OPENVIM_ADMIN_PORT=${OPENVIM_ADMIN_PORT%%#*}
OPENVIM_ADMIN_PORT=`eval echo ${OPENVIM_ADMIN_PORT}`  # remove white spaces

OPENVIM_HOST=`grep http_host: $1`
OPENVIM_HOST=${OPENVIM_HOST#http_host:}
OPENVIM_HOST=${OPENVIM_HOST%%#*}
OPENVIM_HOST=`eval echo ${OPENVIM_HOST}`  # remove white spaces

OPENVIM_OF_IP=`grep of_controller_ip: $1`
OPENVIM_OF_IP=${OPENVIM_OF_IP#of_controller_ip:}
OPENVIM_OF_IP=${OPENVIM_OF_IP%%#*}
OPENVIM_OF_IP=`eval echo ${OPENVIM_OF_IP}`  # remove white spaces

OPENVIM_OF_PORT=`grep of_controller_port: $1`
OPENVIM_OF_PORT=${OPENVIM_OF_PORT#of_controller_port:}
OPENVIM_OF_PORT=${OPENVIM_OF_PORT%%#*}
OPENVIM_OF_PORT=`eval echo ${OPENVIM_OF_PORT}`  # remove white spaces

OPENVIM_OF_DPID=`grep of_controller_dpid: $1`
OPENVIM_OF_DPID=${OPENVIM_OF_DPID#of_controller_dpid:}
OPENVIM_OF_DPID=${OPENVIM_OF_DPID%%#*}
OPENVIM_OF_DPID=`eval echo ${OPENVIM_OF_DPID}`  # remove white spaces


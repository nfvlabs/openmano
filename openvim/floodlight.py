#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

'''
This thread interacts with a openflow floodligth controller to create dataplane connections
'''

__author__="Pablo Montes, Alfonso Tierno"
__date__ ="$28-oct-2014 12:07:15$"


import json
import utils.auxiliary_functions as af
import threading
import time
import Queue
import requests
import itertools

class FL_conn():
    '''Floodlight connector. No MAC learning is used'''
    def __init__(self, of_url, of_dpid, of_test):

        self.name = "Floodlight_v0.9_connector"
        self.dpid = str(of_dpid)
        self.url = of_url
        self.test = of_test

        self.pp2ofi={}  # Physical Port 2 OpenFlow Index
        self.headers = {'content-type':'application/json', 'Accept':'application/json'}


    def obtain_port_correspondence(self):
        if self.test:
            return 0, None
        try:
            of_response = requests.get(self.url+"/wm/core/controller/switches/json", headers=self.headers)
            #print vim_response.status_code
            if of_response.status_code != 200:
                print self.name, ": get_of_controller_info:", self.url, of_response
                raise requests.exceptions.RequestException("Openflow response " + str(of_response.status_code))
            info = of_response.json()
            
            if type(info) != list and type(info) != tuple:
                return -1, "unexpected openflow response, not a list. Wrong version?"
            index = -1
            for i in range(0,len(info)):
                if "dpid" not in info[0]:
                    return -1, "unexpected openflow response. Not 'dpdi' in field. Wrong version?"
                if info[i]["dpid"] == self.dpid:
                    index = i
                    break
            if index == -1:
                text = "Error "+self.dpid+" not present in controller "+self.url
                print self.name, ": get_of_controller_info ERROR", text 
                return -1, text
            else:
                for port in info[index]["ports"]:
                    self.pp2ofi[ str(port["name"]) ] = str(port["portNumber"] )
            print self.name, ": get_of_controller_info ports:", self.pp2ofi
            return 0, self.pp2ofi
        except requests.exceptions.RequestException, e:
            print self.name, ": get_of_controller_info Exception:", str(e)
            return -1, str(e)
        except ValueError, e: # the case that JSON can not be decoded
            print self.name, ": get_of_controller_info Exception:", str(e)
            return -1, str(e)
            
    def del_flow(self, flow_name):
        if self.test:
            print self.name, ": FAKE del_flow", flow_name
            return 0, None
        try:
            of_response = requests.delete(self.url+"/wm/staticflowentrypusher/json",
                                headers=self.headers, data='{"switch": "'+self.dpid+'","name":"'+flow_name+'"}')
            print self.name, ": del_flow", flow_name, of_response
            #print vim_response.status_code
            if of_response.status_code != 200:
                raise requests.exceptions.RequestException("Openflow response " + str(of_response.status_code))
            return 0, None

        except requests.exceptions.RequestException, e:
            print self.name, ": del_flow", flow_name, "Exception:", str(e)
            return -1, str(e)

    def new_flow(self, data):
        if self.test:
            print self.name, ": FAKE new_flow", data
            return 0, None
        try:
            #We have to build the data for the floodlight call from the generic data
            sdata = dict(data)
            sdata['actions'] = ""

            actions_nb = len(data['actions'])
            for action in data['actions']:
                actions_nb -= 1
                add_comma = True
                if action == 'set-vlan-id' or action == 'output':
                    sdata['actions'] +=  action + '='
                    add_comma = False
                else:
                    sdata['actions'] +=  action

                if actions_nb > 0 and add_comma:
                    sdata['actions'] +=  ', '


            of_response = requests.post(self.url+"/wm/staticflowentrypusher/json",
                                headers=self.headers, data=json.dumps(sdata) )
            print self.name, ": new_flow():", sdata, of_response
            #print vim_response.status_code
            if of_response.status_code != 200:
                raise requests.exceptions.RequestException("Openflow response " + str(of_response.status_code))
            return 0, None

        except requests.exceptions.RequestException, e:
            print self.name, ": new_flow Exception:", str(e)
            return -1, str(e)

    def clear_all_flows(self):
        try:
            if not self.test:
                of_response = requests.get(self.url+"/wm/staticflowentrypusher/clear/"+str(self.dpid)+"/json")
                print self.name, ": clear_all_flows:", of_response
                if of_response.status_code != 200:
                    raise requests.exceptions.RequestException("Openflow response " + str(of_response.status_code))
            return 0, None
        except requests.exceptions.RequestException, e:
            print self.name, ": clear_all_flows Exception:", str(e)
            return -1, str(e)

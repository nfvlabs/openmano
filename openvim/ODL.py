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
import base64

class ODL_conn():
    '''OpenDayLight connector. No MAC learning is used'''
    def __init__(self, of_url, of_dpid, of_test, of_user, of_password):

        self.name = "OpenDayLight"
        self.dpid = str(of_dpid)
        self.id = 'openflow:'+str(int(self.dpid.replace(':', ''), 16))
        self.url = of_url
        self.test = of_test
        self.auth = base64.b64encode(of_user+":"+of_password)

        self.pp2ofi={}  # Physical Port 2 OpenFlow Index
        self.headers = {'content-type':'application/json', 'Accept':'application/json',
                        'Authorization': 'Basic '+self.auth}


    def obtain_port_correspondence(self):
        if self.test:
            return 0, None
        try:
            of_response = requests.get(self.url+"/restconf/operational/opendaylight-inventory:nodes",
                                       headers=self.headers)
            #print vim_response.status_code
            if of_response.status_code != 200:
                print self.name, ": obtain_port_correspondence:", self.url, of_response
                raise requests.exceptions.RequestException("Openflow response " + str(of_response.status_code))
            info = of_response.json()
            
            if type(info) != dict:
                return -1, "unexpected openflow response, not a dict. Wrong version?"

            nodes = info.get('nodes')
            if nodes is None:
                return -1, "unexpected openflow response, 'nodes' element not found. Wrong version?"

            node_list = nodes.get('node')
            if node_list is None or type(node_list) is not list:
                return -1, "unexpected openflow response, 'node' element not found or is not a list. Wrong version?"

            for node in node_list:
                node_id = node.get('id')
                if node_id is None:
                    return -1, "unexpected openflow response, 'id' element not found in one of the nodes. " \
                               "Wrong version?"

                if node_id == 'controller-config':
                    continue

                # Figure out if this is the appropriate switch. The 'id' is 'openflow:' plus the decimal value
                # of the dpid
                #  In case this is not the desired switch, continue
                if self.id != node_id:
                    continue

                node_connector_list = node.get('node-connector')
                if node_connector_list is None or type(node_connector_list) is not list:
                    return -1, "unexpected openflow response, 'node-connector' element not found in the node" \
                               "or is not a list. Wrong version?"

                for node_connector in node_connector_list:
                    self.pp2ofi[ str(node_connector['flow-node-inventory:name']) ] = str(node_connector['id'] )

                #If we found the appropriate dpid no need to continue in the for loop
                break

            print self.name, ": obtain_port_correspondence ports:", self.pp2ofi
            return 0, self.pp2ofi
        except requests.exceptions.RequestException, e:
            print self.name, ": obtain_port_correspondence Exception:", str(e)
            return -1, str(e)
        except ValueError, e: # the case that JSON can not be decoded
            print self.name, ": obtain_port_correspondence Exception:", str(e)
            return -1, str(e)
            
    def del_flow(self, flow_name):
        if self.test:
            print self.name, ": FAKE del_flow", flow_name
            return 0, None
        try:
            of_response = requests.delete(self.url+"/restconf/config/opendaylight-inventory:nodes/node/" + self.id +
                                          "/table/0/flow/"+flow_name, headers=self.headers)
            print self.name, ": del_flow", flow_name, of_response
            print self.url+"/restconf/config/opendaylight-inventory:nodes/node/" + self.id + \
                                          "/table/0/flow/"+flow_name
            print self.headers
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
            #We have to build the data for the opendaylight call from the generic data
            sdata = dict()
            sdata['flow-node-inventory:flow'] = list()
            sdata['flow-node-inventory:flow'].append(dict())
            flow = sdata['flow-node-inventory:flow'][0]
            flow['id'] = data['name']
            flow['flow-name'] = data['name']
            flow['idle-timeout'] = 0
            flow['hard-timeout'] = 0
            flow['table_id'] = 0
            flow['priority'] = data['priority']
            flow['match'] = dict()
            flow['match']['in-port'] = self.pp2ofi[data['ingress_port']]
            if 'dst-mac' in data:
                flow['match']['ethernet-match'] = dict()
                flow['match']['ethernet-match']['ethernet-destination'] = dict()
                flow['match']['ethernet-match']['ethernet-destination']['address'] = data['dst_mac']
            if data.get('vlan_id'):
                flow['match']['vlan-match'] = dict()
                flow['match']['vlan-match']['vlan-id'] = dict()
                flow['match']['vlan-match']['vlan-id']['vlan-id-present'] = True
                flow['match']['vlan-match']['vlan-id']['vlan-id'] = int(data['vlan_id'])
            flow['instructions'] = dict()
            flow['instructions']['instruction'] = list()
            flow['instructions']['instruction'].append(dict())
            flow['instructions']['instruction'][0]['order'] = 1
            flow['instructions']['instruction'][0]['apply-actions'] = dict()
            flow['instructions']['instruction'][0]['apply-actions']['action'] = list()
            actions = flow['instructions']['instruction'][0]['apply-actions']['action']

            order = 0
            for action in data['actions']:
                new_action = { 'order': order }
                if  action[0] == "vlan":
                    if action[1] == None:
                        #TODO strip vlan
                        pass  #TODO !!!!!!!!!!!!!!!!!!!!!!
                    else:
                        new_action['set-field'] = dict()
                        new_action['set-field']['vlan-match'] = dict()
                        new_action['set-field']['vlan-match']['vlan-id'] = dict()
                        new_action['set-field']['vlan-match']['vlan-id']['vlan-id-present'] = True
                        new_action['set-field']['vlan-match']['vlan-id']['vlan-id'] = int(action[1])
                elif action[0] == 'out':
                    new_action['output-action'] = dict()
                    new_action['output-action']['output-node-connector'] = self.pp2ofi[ action[1] ]
                else:
                    error_msj = 'Error. Data information used to create a new flow has not the expected format'
                    print error_msj
                    return -1, error_msj

                actions.append(new_action)
                order += 1

            print json.dumps(sdata)
            of_response = requests.put(self.url+"/restconf/config/opendaylight-inventory:nodes/node/" + self.id +
                          "/table/0/flow/" + data['name'],
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
                of_response = requests.delete(self.url+"/restconf/config/opendaylight-inventory:nodes/node/" + self.id +
                                          "/table/0", headers=self.headers)
                print self.name, ": clear_all_flows:", of_response
                if of_response.status_code != 200:
                    raise requests.exceptions.RequestException("Openflow response " + str(of_response.status_code))
            return 0, None
        except requests.exceptions.RequestException, e:
            print self.name, ": clear_all_flows Exception:", str(e)
            return -1, str(e)

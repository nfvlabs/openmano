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
import requests
import base64

class ODL_conn():
    '''OpenDayLight connector. No MAC learning is used'''
    def __init__(self, of_ip ,of_port, of_dpid, of_user, of_password):

        self.name = "OpenDayLight"
        self.dpid = str(of_dpid)
        self.id = 'openflow:'+str(int(self.dpid.replace(':', ''), 16))
        self.url = "http://%s:%s" %( str(of_ip), str(of_port) )
        self.auth = base64.b64encode(of_user+":"+of_password)

        self.pp2ofi={}  # From Physical Port to OpenFlow Index
        self.ofi2pp={}  # From OpenFlow Index to Physical Port
        self.headers = {'content-type':'application/json', 'Accept':'application/json',
                        'Authorization': 'Basic '+self.auth}

    def get_of_switches(self):
        ''' Obtain a a list of switches or DPID detected by this controller
            Return
                <number>, <list>: where each element of the list is a tuple pair (DPID, ip address)
                <0, text_error: uppon error
        '''  
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

            switch_list=[]
            for node in node_list:
                node_id = node.get('id')
                if node_id is None:
                    return -1, "unexpected openflow response, 'id' element not found in one of the nodes. " \
                               "Wrong version?"

                if node_id == 'controller-config':
                    continue

                node_ip_address = node.get('flow-node-inventory:ip-address')
                if node_ip_address is None:
                    return -1, "unexpected openflow response, 'flow-node-inventory:ip-address' element not found in " \
                               "the node. Wrong version?"

                node_id_hex=hex(int(node_id.split(':')[1])).split('x')[1].zfill(16)
                switch_list.append( (':'.join(a+b for a,b in zip(node_id_hex[::2], node_id_hex[1::2])), node_ip_address))

            return len(switch_list), switch_list
        except requests.exceptions.RequestException, e:
            print self.name, ": obtain_port_correspondence Exception:", str(e)
            return -1, str(e)
        except ValueError, e: # the case that JSON can not be decoded
            print self.name, ": obtain_port_correspondence Exception:", str(e)
            return -1, str(e)
        
    def obtain_port_correspondence(self):
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
                    self.ofi2pp[ node_connector['id'] ] =  str(node_connector['flow-node-inventory:name'])


                node_ip_address = node.get('flow-node-inventory:ip-address')
                if node_ip_address is None:
                    return -1, "unexpected openflow response, 'flow-node-inventory:ip-address' element not found in the node" \
                               "or is not a string. Wrong version?"
                self.ip_address = node_ip_address

                #If we found the appropriate dpid no need to continue in the for loop
                break

           # print self.name, ": obtain_port_correspondence ports:", self.pp2ofi
            return 0, self.pp2ofi
        except requests.exceptions.RequestException, e:
            print self.name, ": obtain_port_correspondence Exception:", str(e)
            return -1, str(e)
        except ValueError, e: # the case that JSON can not be decoded
            print self.name, ": obtain_port_correspondence Exception:", str(e)
            return -1, str(e)
        
    def get_of_rules(self, translate_of_ports=True):
        ''' Obtain the rules inserted at openflow controller
            Params:
                translate_of_ports: if True it translates ports from openflow index to switch name
            Return:
                0, dict if ok: with the rule name as key and value is another dictionary with the rule parameters
                -1, text_error on fail
        '''   
        
        if len(self.ofi2pp) == 0:
            r,c = self.obtain_port_correspondence()
            if r<0:
                return r,c
        #get rules
        try:
            #print self.url+"/restconf/config/opendaylight-inventory:nodes/node/"+self.id+"/table/0  "+str(self.headers)
            of_response = requests.get(self.url+"/restconf/config/opendaylight-inventory:nodes/node/" + self.id +
                                          "/table/0", headers=self.headers)

            # The configured page does not exist if there are no rules installed. In that case we return an empty dict
            if of_response.status_code == 404:
                return 0, {}

            if of_response.status_code != 200:
                raise requests.exceptions.RequestException("Openflow response " + str(of_response.status_code))
            
            info = of_response.json()

            if type(info) != dict:
                return -1, "unexpected openflow response, not a dict. Wrong version?"

            table = info.get('flow-node-inventory:table')
            if table is None:
                return -1, "unexpected openflow response, 'flow-node-inventory:table' element not found. Wrong version?"

            flow_list = table[0].get('flow')
            if flow_list is None:
               return 0, {}

            if type(flow_list) is not list:
                return -1, "unexpected openflow response, 'flow' element not found or is not a list. Wrong version?"

            #TODO translate ports according to translate_of_ports parameter

            rules = dict()
            for flow in flow_list:
                if not ('priority' in flow and 'id' in flow and 'match' in flow and 'instructions' in flow and \
                   'instruction' in flow['instructions'] and 'apply-actions' in flow['instructions']['instruction'][0] and \
                    'action' in flow['instructions']['instruction'][0]['apply-actions']):
                        return -1, "unexpected openflow response, one or more elementa are missing. Wrong version?"

                flow['instructions']['instruction'][0]['apply-actions']['action']

                rule = dict()
                rule['switch'] = self.dpid
                rule['priority'] = flow['priority']
                #rule['name'] = flow['id']
                #rule['cookie'] = flow['cookie']
                if 'in-port' in flow['match']:
                    in_port = flow['match']['in-port']
                    if not in_port in self.ofi2pp:
                        return -1, "Error: Ingress port "+in_port+" is not in switch port list"

                    if translate_of_ports:
                        in_port = self.ofi2pp[in_port]

                    rule['ingress_port'] = in_port

                    if 'vlan-match' in flow['match'] and 'vlan-id' in flow['match']['vlan-match'] and \
                                'vlan-id' in flow['match']['vlan-match']['vlan-id'] and \
                                'vlan-id-present' in flow['match']['vlan-match']['vlan-id'] and \
                                flow['match']['vlan-match']['vlan-id']['vlan-id-present'] == True:
                        rule['vlan_id'] = flow['match']['vlan-match']['vlan-id']['vlan-id']

                    if 'ethernet-match' in flow['match'] and 'ethernet-destination' in flow['match']['ethernet-match'] and \
                        'address' in flow['match']['ethernet-match']['ethernet-destination']:
                        rule['dst_mac'] = flow['match']['ethernet-match']['ethernet-destination']['address']

                instructions=flow['instructions']['instruction'][0]['apply-actions']['action']

                max_index=0
                for instruction in instructions:
                    if instruction['order'] > max_index:
                       max_index = instruction['order']

                actions=[None]*(max_index+1)
                for instruction in instructions:
                    if 'output-action' in instruction:
                        if not 'output-node-connector' in instruction['output-action']:
                            return -1, "unexpected openflow response, one or more elementa are missing. Wrong version?"

                        out_port = instruction['output-action']['output-node-connector']
                        if not out_port in self.ofi2pp:
                            return -1, "Error: Output port "+out_port+" is not in switch port list"

                        if translate_of_ports:
                            out_port = self.ofi2pp[out_port]

                        actions[instruction['order']] = ('out',out_port)

                    elif 'strip-vlan-action' in instruction:
                        actions[instruction['order']] = ('vlan', None)

                    elif 'set-field' in instruction:
                        if not ('vlan-match' in instruction['set-field'] and 'vlan-id' in  instruction['set-field']['vlan-match'] and 'vlan-id' in instruction['set-field']['vlan-match']['vlan-id']):
                            return -1, "unexpected openflow response, one or more elementa are missing. Wrong version?"

                        actions[instruction['order']] = ('vlan', instruction['set-field']['vlan-match']['vlan-id']['vlan-id'])

                actions = [x for x in actions if x != None]

                rule['actions'] = list(actions)
                rules[flow['id']] = dict(rule)

                #flow['id']
                #flow['priority']
                #flow['cookie']
                #flow['match']['in-port']
                #flow['match']['vlan-match']['vlan-id']['vlan-id']
                # match -> in-port
                #      -> vlan-match -> vlan-id -> vlan-id
                #flow['match']['vlan-match']['vlan-id']['vlan-id-present']
                #TODO se asume que no se usan reglas con vlan-id-present:false
                #instructions -> instruction -> apply-actions -> action
                #instructions=flow['instructions']['instruction'][0]['apply-actions']['action']
                #Es una lista. Posibles elementos:
                #max_index=0
                #for instruction in instructions:
                #  if instruction['order'] > max_index:
                #    max_index = instruction['order']
                #actions=[None]*(max_index+1)
                #for instruction in instructions:
                #   if 'output-action' in instruction:
                #     actions[instruction['order']] = ('out',instruction['output-action']['output-node-connector'])
                #   elif 'strip-vlan-action' in instruction:
                #     actions[instruction['order']] = ('vlan', None)
                #   elif 'set-field' in instruction:
                #     actions[instruction['order']] = ('vlan', instruction['set-field']['vlan-match']['vlan-id']['vlan-id'])
                #
                #actions = [x for x in actions if x != None]
                #                                                       -> output-action -> output-node-connector
                #                                                       -> pop-vlan-action

            return 0, rules

        except requests.exceptions.RequestException, e:
            print self.name, ": get_of_rules Exception:", str(e)
            return -1, str(e)
        except ValueError, e: # the case that JSON can not be decoded
            print self.name, ": get_of_rules Exception:", str(e)
            return -1, str(e)



            
    def del_flow(self, flow_name):
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
        if len(self.pp2ofi) == 0:
            r,c = self.obtain_port_correspondence()
            if r<0:
                return r,c
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
            if 'dst_mac' in data:
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
                        #strip vlan
                        new_action['strip-vlan-action'] = dict()
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
            of_response = requests.delete(self.url+"/restconf/config/opendaylight-inventory:nodes/node/" + self.id +
                                      "/table/0", headers=self.headers)
            print self.name, ": clear_all_flows:", of_response
            if of_response.status_code != 200:
                raise requests.exceptions.RequestException("Openflow response " + str(of_response.status_code))
            return 0, None
        except requests.exceptions.RequestException, e:
            print self.name, ": clear_all_flows Exception:", str(e)
            return -1, str(e)

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
Implement the plugging for OpendayLight openflow controller
It creates the class OF_conn to create dataplane connections
with static rules based on packet destination MAC address
'''

__author__="Pablo Montes, Alfonso Tierno"
__date__ ="$28-oct-2014 12:07:15$"


import json
import requests
import base64
import logging

class OF_conn():
    '''OpenDayLight connector. No MAC learning is used'''
    def __init__(self, params):
        ''' Constructor. 
            Params: dictionary with the following keys:
                of_dpid:     DPID to use for this controller
                of_ip:       controller IP address
                of_port:     controller TCP port
                of_user:     user credentials, can be missing or None
                of_password: password credentials
                of_debug:    debug level for logging. Default to ERROR
                other keys are ignored
            Raise an exception if same parameter is missing or wrong
        '''
        #check params
        if "of_ip" not in params or params["of_ip"]==None or "of_port" not in params or params["of_port"]==None:
            raise ValueError("IP address and port must be provided")
        #internal variables
        self.name = "OpenDayLight"
        self.headers = {'content-type':'application/json', 
                        'Accept':'application/json'
        }
        self.auth=None
        self.pp2ofi={}  # From Physical Port to OpenFlow Index
        self.ofi2pp={}  # From OpenFlow Index to Physical Port

        self.dpid = str(params["of_dpid"])
        self.id = 'openflow:'+str(int(self.dpid.replace(':', ''), 16))
        self.url = "http://%s:%s" %( str(params["of_ip"]), str(params["of_port"] ) )
        if "of_user" in params and params["of_user"]!=None:
            if not params.get("of_password"):
                of_password=""
            else:
                of_password=str(params["of_password"])
            self.auth = base64.b64encode(str(params["of_user"])+":"+of_password)
            self.headers['Authorization'] = 'Basic '+self.auth
            

        self.logger = logging.getLogger('vim.OF.ODL')
        self.logger.setLevel( getattr(logging, params.get("of_debug", "ERROR")) )

    def get_of_switches(self):
        ''' Obtain a a list of switches or DPID detected by this controller
            Return
                >=0, list:      list length, and a list where each element a tuple pair (DPID, IP address)
                <0, text_error: if fails
        '''  
        try:
            of_response = requests.get(self.url+"/restconf/operational/opendaylight-inventory:nodes",
                                       headers=self.headers)
            error_text = "Openflow response %d: %s" % (of_response.status_code, of_response.text)
            if of_response.status_code != 200:
                self.logger.warning("get_of_switches " + error_text)
                return -1 , error_text
            self.logger.debug("get_of_switches " + error_text)
            info = of_response.json()
            
            if type(info) != dict:
                self.logger.error("get_of_switches. Unexpected response, not a dict: %s", str(info))
                return -1, "Unexpected response, not a dict. Wrong version?"

            nodes = info.get('nodes')
            if type(nodes) is not dict:
                self.logger.error("get_of_switches. Unexpected response at 'nodes', not found or not a dict: %s", str(type(info)))
                return -1, "Unexpected response at 'nodes', not found or not a dict. Wrong version?"

            node_list = nodes.get('node')
            if type(node_list) is not list:
                self.logger.error("get_of_switches. Unexpected response, at 'nodes':'node', not found or not a list: %s", str(type(node_list)))
                return -1, "Unexpected response, at 'nodes':'node', not found or not a list. Wrong version?"

            switch_list=[]
            for node in node_list:
                node_id = node.get('id')
                if node_id is None:
                    self.logger.error("get_of_switches. Unexpected response at 'nodes':'node'[]:'id', not found: %s", str(node))
                    return -1, "Unexpected response at 'nodes':'node'[]:'id', not found . Wrong version?"

                if node_id == 'controller-config':
                    continue

                node_ip_address = node.get('flow-node-inventory:ip-address')
                if node_ip_address is None:
                    self.logger.error("get_of_switches. Unexpected response at 'nodes':'node'[]:'flow-node-inventory:ip-address', not found: %s", str(node))
                    return -1, "Unexpected response at 'nodes':'node'[]:'flow-node-inventory:ip-address', not found. Wrong version?"

                node_id_hex=hex(int(node_id.split(':')[1])).split('x')[1].zfill(16)
                switch_list.append( (':'.join(a+b for a,b in zip(node_id_hex[::2], node_id_hex[1::2])), node_ip_address))

            return len(switch_list), switch_list
        except (requests.exceptions.RequestException, ValueError) as e:
            #ValueError in the case that JSON can not be decoded
            error_text = type(e).__name__ + ": " + str(e)
            self.logger.error("get_of_switches " + error_text)
            return -1, error_text
        
    def obtain_port_correspondence(self):
        '''Obtain the correspondence between physical and openflow port names
        return:
             0, dictionary: with physical name as key, openflow name as value
            -1, error_text: if fails
        '''
        try:
            of_response = requests.get(self.url+"/restconf/operational/opendaylight-inventory:nodes",
                                       headers=self.headers)
            error_text = "Openflow response %d: %s" % (of_response.status_code, of_response.text)
            if of_response.status_code != 200:
                self.logger.warning("obtain_port_correspondence " + error_text)
                return -1 , error_text
            self.logger.debug("obtain_port_correspondence " + error_text)
            info = of_response.json()
            
            if type(info) != dict:
                self.logger.error("obtain_port_correspondence. Unexpected response not a dict: %s", str(info))
                return -1, "Unexpected openflow response, not a dict. Wrong version?"

            nodes = info.get('nodes')
            if type(nodes) is not dict:
                self.logger.error("obtain_port_correspondence. Unexpected response at 'nodes', not found or not a dict: %s", str(type(nodes)))
                return -1, "Unexpected response at 'nodes',not found or not a dict. Wrong version?"

            node_list = nodes.get('node')
            if type(node_list) is not list:
                self.logger.error("obtain_port_correspondence. Unexpected response, at 'nodes':'node', not found or not a list: %s", str(type(node_list)))
                return -1, "Unexpected response, at 'nodes':'node', not found or not a list. Wrong version?"

            for node in node_list:
                node_id = node.get('id')
                if node_id is None:
                    self.logger.error("obtain_port_correspondence. Unexpected response at 'nodes':'node'[]:'id', not found: %s", str(node))
                    return -1, "Unexpected response at 'nodes':'node'[]:'id', not found . Wrong version?"

                if node_id == 'controller-config':
                    continue

                # Figure out if this is the appropriate switch. The 'id' is 'openflow:' plus the decimal value
                # of the dpid
                #  In case this is not the desired switch, continue
                if self.id != node_id:
                    continue

                node_connector_list = node.get('node-connector')
                if type(node_connector_list) is not list:
                    self.logger.error("obtain_port_correspondence. Unexpected response at 'nodes':'node'[]:'node-connector', not found or not a list: %s", str(node))
                    return -1, "Unexpected response at 'nodes':'node'[]:'node-connector', not found  or not a list. Wrong version?"

                for node_connector in node_connector_list:
                    self.pp2ofi[ str(node_connector['flow-node-inventory:name']) ] = str(node_connector['id'] )
                    self.ofi2pp[ node_connector['id'] ] =  str(node_connector['flow-node-inventory:name'])


                node_ip_address = node.get('flow-node-inventory:ip-address')
                if node_ip_address is None:
                    self.logger.error("obtain_port_correspondence. Unexpected response at 'nodes':'node'[]:'flow-node-inventory:ip-address', not found: %s", str(node))
                    return -1, "Unexpected response at 'nodes':'node'[]:'flow-node-inventory:ip-address', not found. Wrong version?"
                self.ip_address = node_ip_address

                #If we found the appropriate dpid no need to continue in the for loop
                break

            #print self.name, ": obtain_port_correspondence ports:", self.pp2ofi
            return 0, self.pp2ofi
        except (requests.exceptions.RequestException, ValueError) as e:
            #ValueError in the case that JSON can not be decoded
            error_text = type(e).__name__ + ": " + str(e)
            self.logger.error("obtain_port_correspondence " + error_text)
            return -1, error_text
        
    def get_of_rules(self, translate_of_ports=True):
        ''' Obtain the rules inserted at openflow controller
            Params:
                translate_of_ports: if True it translates ports from openflow index to physical switch name
            Return:
                0, dict if ok: with the rule name as key and value is another dictionary with the following content:
                    priority: rule priority
                    name:         rule name (present also as the master dict key)
                    ingress_port: match input port of the rule
                    dst_mac:      match destination mac address of the rule, can be missing or None if not apply
                    vlan_id:      match vlan tag of the rule, can be missing or None if not apply
                    actions:      list of actions, composed by a pair tuples:
                        (vlan, None/int): for stripping/setting a vlan tag
                        (out, port):      send to this port 
                    switch:       DPID, all 
                -1, text_error if fails
        '''   
        
        if len(self.ofi2pp) == 0:
            r,c = self.obtain_port_correspondence()
            if r<0:
                return r,c
        #get rules
        try:
            of_response = requests.get(self.url+"/restconf/config/opendaylight-inventory:nodes/node/" + self.id +
                                          "/table/0", headers=self.headers)
            error_text = "Openflow response %d: %s" % (of_response.status_code, of_response.text)

            # The configured page does not exist if there are no rules installed. In that case we return an empty dict
            if of_response.status_code == 404:
                return 0, {}

            elif of_response.status_code != 200:
                self.logger.warning("get_of_rules " + error_text)
                return -1 , error_text
            self.logger.debug("get_of_rules " + error_text)
            
            info = of_response.json()

            if type(info) != dict:
                self.logger.error("get_of_rules. Unexpected response not a dict: %s", str(info))
                return -1, "Unexpected openflow response, not a dict. Wrong version?"

            table = info.get('flow-node-inventory:table')
            if type(table) is not list:
                self.logger.error("get_of_rules. Unexpected response at 'flow-node-inventory:table', not a list: %s", str(type(table)))
                return -1, "Unexpected response at 'flow-node-inventory:table', not a list. Wrong version?"

            flow_list = table[0].get('flow')
            if flow_list is None:
                return 0, {}

            if type(flow_list) is not list:
                self.logger.error("get_of_rules. Unexpected response at 'flow-node-inventory:table'[0]:'flow', not a list: %s", str(type(flow_list)))
                return -1, "Unexpected response at 'flow-node-inventory:table'[0]:'flow', not a list. Wrong version?"

            #TODO translate ports according to translate_of_ports parameter

            rules = dict()
            for flow in flow_list:
                if not ('id' in flow and 'match' in flow and 'instructions' in flow and \
                   'instruction' in flow['instructions'] and 'apply-actions' in flow['instructions']['instruction'][0] and \
                    'action' in flow['instructions']['instruction'][0]['apply-actions']):
                        return -1, "unexpected openflow response, one or more elements are missing. Wrong version?"

                flow['instructions']['instruction'][0]['apply-actions']['action']

                rule = dict()
                rule['switch'] = self.dpid
                rule['priority'] = flow.get('priority')
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
                            return -1, "unexpected openflow response, one or more elements are missing. Wrong version?"

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
        except (requests.exceptions.RequestException, ValueError) as e:
            #ValueError in the case that JSON can not be decoded
            error_text = type(e).__name__ + ": " + str(e)
            self.logger.error("get_of_rules " + error_text)
            return -1, error_text
            
    def del_flow(self, flow_name):
        ''' Delete an existing rule
            Params: flow_name, this is the rule name
            Return
                0, None if ok
                -1, text_error if fails
        '''           
        try:
            of_response = requests.delete(self.url+"/restconf/config/opendaylight-inventory:nodes/node/" + self.id +
                                          "/table/0/flow/"+flow_name, headers=self.headers)
            error_text = "Openflow response %d: %s" % (of_response.status_code, of_response.text)
            if of_response.status_code != 200:
                self.logger.warning("del_flow " + error_text)
                return -1 , error_text
            self.logger.debug("del_flow OK " + error_text)
            return 0, None

        except requests.exceptions.RequestException as e:
            error_text = type(e).__name__ + ": " + str(e)
            self.logger.error("del_flow " + error_text)
            return -1, error_text

    def new_flow(self, data):
        ''' Insert a new static rule
            Params: data: dictionary with the following content:
                priority:     rule priority
                name:         rule name
                ingress_port: match input port of the rule
                dst_mac:      match destination mac address of the rule, missing or None if not apply
                vlan_id:      match vlan tag of the rule, missing or None if not apply
                actions:      list of actions, composed by a pair tuples with these posibilities:
                    ('vlan', None/int): for stripping/setting a vlan tag
                    ('out', port):      send to this port
            Return
                0, None if ok
                -1, text_error if fails
        '''   
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
            flow['priority'] = data.get('priority')
            flow['match'] = dict()
            if not data['ingress_port'] in self.pp2ofi:
                error_text = 'Error. Port '+data['ingress_port']+' is not present in the switch'
                self.logger.warning("new_flow " + error_text)
                return -1, error_text
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
                    if not action[1] in self.pp2ofi:
                        error_msj = 'Port '+action[1]+' is not present in the switch'
                        return -1, error_msj

                    new_action['output-action']['output-node-connector'] = self.pp2ofi[ action[1] ]
                else:
                    error_msj = "Unknown item '%s' in action list" % action[0]
                    self.logger.error("new_flow " + error_msj)
                    return -1, error_msj

                actions.append(new_action)
                order += 1

            #print json.dumps(sdata)
            of_response = requests.put(self.url+"/restconf/config/opendaylight-inventory:nodes/node/" + self.id +
                          "/table/0/flow/" + data['name'],
                                headers=self.headers, data=json.dumps(sdata) )
            error_text = "Openflow response %d: %s" % (of_response.status_code, of_response.text)
            if of_response.status_code != 200:
                self.logger.warning("new_flow " + error_text)
                return -1 , error_text
            self.logger.debug("new_flow OK " + error_text)
            return 0, None

        except requests.exceptions.RequestException as e:
            error_text = type(e).__name__ + ": " + str(e)
            self.logger.error("new_flow " + error_text)
            return -1, error_text

    def clear_all_flows(self):
        ''' Delete all existing rules
            Return:
                0, None if ok
                -1, text_error if fails
        '''           
        try:
            of_response = requests.delete(self.url+"/restconf/config/opendaylight-inventory:nodes/node/" + self.id +
                                      "/table/0", headers=self.headers)
            error_text = "Openflow response %d: %s" % (of_response.status_code, of_response.text)
            if of_response.status_code != 200 and of_response.status_code != 404: #HTTP_Not_Found
                self.logger.warning("clear_all_flows " + error_text)
                return -1 , error_text
            self.logger.debug("clear_all_flows OK " + error_text)
            return 0, None
        except requests.exceptions.RequestException as e:
            error_text = type(e).__name__ + ": " + str(e)
            self.logger.error("clear_all_flows " + error_text)
            return -1, error_text

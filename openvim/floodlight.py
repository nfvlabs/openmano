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
Implement the plugging for floodligth openflow controller
It creates the class OF_conn to create dataplane connections
with static rules based on packet destination MAC address
'''

__author__="Pablo Montes, Alfonso Tierno"
__date__ ="$28-oct-2014 12:07:15$"


import json
import requests
import logging

class OF_conn():
    ''' Openflow Connector for Floodlight.
         No MAC learning is used
        version 0.9 or 1.X is autodetected
        version 1.X is in progress, not finished!!!
    '''
    def __init__(self, params):
        ''' Constructor. 
            params is a dictionay with the following keys:
                of_dpid:     DPID to use for this controller
                of_ip:       controller IP address
                of_port:     controller TCP port
                of_version:  version, can be "0.9" or "1.X". By default it is autodetected
                of_debug:    debug level for logging. Default to ERROR
                other keys are ignored
            Raise an exception if same parameter is missing or wrong
        '''
        #check params
        if "of_ip" not in params or params["of_ip"]==None or "of_port" not in params or params["of_port"]==None:
            raise ValueError("IP address and port must be provided")

        self.name = "Floodlight"
        self.dpid = str(params["of_dpid"])
        self.url = "http://%s:%s" %( str(params["of_ip"]), str(params["of_port"]) )

        self.pp2ofi={}  # From Physical Port to OpenFlow Index
        self.ofi2pp={}  # From OpenFlow Index to Physical Port
        self.headers = {'content-type':'application/json', 'Accept':'application/json'}
        self.version= None
        self.logger = logging.getLogger('vim.OF.FL')
        self.logger.setLevel( getattr(logging, params.get("of_debug", "ERROR") ) )
        self._set_version(params.get("of_version") )
    
    def _set_version(self, version):
        '''set up a version of the controller.
         Depending on the version it fills the self.ver_names with the naming used in this version
        '''
        #static version names
        if version==None:
            self.version= None
        elif version=="0.9":
            self.version= version
            self.name = "Floodlightv0.9"
            self.ver_names={
                "dpid":         "dpid",
                "URLmodifier":  "staticflowentrypusher",
                "destmac":      "dst-mac",
                "vlanid":       "vlan-id",
                "inport":       "ingress-port",
                "setvlan":      "set-vlan-id",
                "stripvlan":    "strip-vlan",
            }
        elif version[0]=="1" : #version 1.X
            self.version= version
            self.name = "Floodlightv1.X"
            self.ver_names={
                "dpid":         "switchDPID",
                "URLmodifier":  "staticflowpusher",
                "destmac":      "eth_dst",
                "vlanid":       "eth_vlan_vid",
                "inport":       "in_port",
                "setvlan":      "set_vlan_vid",
                "stripvlan":    "strip_vlan",
            }
        else:
            raise ValueError("Invalid version for floodlight controller")
            
    def get_of_switches(self):
        ''' Obtain a a list of switches or DPID detected by this controller
            Return
                >=0, list:      list length, and a list where each element a tuple pair (DPID, IP address)
                <0, text_error: if fails
        '''  
        try:
            of_response = requests.get(self.url+"/wm/core/controller/switches/json", headers=self.headers)
            error_text = "Openflow response %d: %s" % (of_response.status_code, of_response.text)
            if of_response.status_code != 200:
                self.logger.warning("get_of_switches " + error_text)
                return -1 , error_text
            self.logger.debug("get_of_switches " + error_text)
            info = of_response.json()
            if type(info) != list and type(info) != tuple:
                self.logger.error("get_of_switches. Unexpected response not a list %s", str(type(info)))
                return -1, "Unexpected response, not a list. Wrong version?"
            if len(info)==0:
                return 0, info
            #autodiscover version
            if self.version == None:
                if 'dpid' in info[0] and 'inetAddress' in info[0]:
                    self._set_version("0.9")
                elif 'switchDPID' in info[0] and 'inetAddress' in info[0]:
                    self._set_version("1.X")
                else:
                    self.logger.error("get_of_switches. Unexpected response, not found 'dpid' or 'switchDPID' field: %s", str(info[0]))
                    return -1, "Unexpected response, not found 'dpid' or 'switchDPID' field. Wrong version?"
            
            switch_list=[]
            for switch in info:
                switch_list.append( (switch[ self.ver_names["dpid"] ], switch['inetAddress']) )
            return len(switch_list), switch_list
        except (requests.exceptions.RequestException, ValueError) as e:
            #ValueError in the case that JSON can not be decoded
            error_text = type(e).__name__ + ": " + str(e)
            self.logger.error("get_of_switches " + error_text)
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
        
        #get translation, autodiscover version
        if len(self.ofi2pp) == 0:
            r,c = self.obtain_port_correspondence()
            if r<0:
                return r,c
        #get rules
        try:
            of_response = requests.get(self.url+"/wm/%s/list/%s/json" %(self.ver_names["URLmodifier"], self.dpid),
                                        headers=self.headers)
            error_text = "Openflow response %d: %s" % (of_response.status_code, of_response.text)
            if of_response.status_code != 200:
                self.logger.warning("get_of_rules " + error_text)
                return -1 , error_text
            self.logger.debug("get_of_rules " + error_text)
            info = of_response.json()
            if type(info) != dict:
                self.logger.error("get_of_rules. Unexpected response not a dict %s", str(type(info)))
                return -1, "Unexpected response, not a dict. Wrong version?"
            rule_dict={}
            for switch,switch_info in info.iteritems():
                if switch_info == None:
                    continue
                if str(switch) != self.dpid:
                    continue
                for name,details in switch_info.iteritems():
                    rule = {}
                    rule["switch"] = str(switch)
                    #rule["active"] = "true"
                    rule["priority"] = int(details["priority"])
                    if self.version[0]=="0":
                        if translate_of_ports:
                            rule["ingress_port"] = self.ofi2pp[ details["match"]["inputPort"] ] 
                        else:
                            rule["ingress_port"] = str(details["match"]["inputPort"])
                        dst_mac = details["match"]["dataLayerDestination"]
                        if dst_mac != "00:00:00:00:00:00":
                            rule["dst_mac"] = dst_mac
                        vlan = details["match"]["dataLayerVirtualLan"]
                        if vlan != -1:
                            rule["vlan_id"] = vlan
                        actionlist=[]
                        for action in details["actions"]:
                            if action["type"]=="OUTPUT":
                                if translate_of_ports:
                                    port = self.ofi2pp[ action["port"] ]
                                else:
                                    port = action["port"]
                                actionlist.append( ("out", port) )
                            elif action["type"]=="STRIP_VLAN":
                                actionlist.append( ("vlan",None) )
                            elif action["type"]=="SET_VLAN_ID":
                                actionlist.append( ("vlan", action["virtualLanIdentifier"]) )
                            else:
                                actionlist.append( (action["type"], str(action) ))
                                self.logger.warning("get_of_rules() Unknown action in rule %s: %s", rule["name"], str(action))
                            rule["actions"] = actionlist
                    elif self.version[0]=="1":
                        if translate_of_ports:
                            rule["ingress_port"] = self.ofi2pp[ details["match"]["in_port"] ]
                        else:
                            rule["ingress_port"] = details["match"]["in_port"]
                        if "eth_dst" in details["match"]:
                            dst_mac = details["match"]["eth_dst"]
                            if dst_mac != "00:00:00:00:00:00":
                                rule["dst_mac"] = dst_mac
                        if "eth_vlan_vid" in details["match"]:
                            vlan = int(details["match"]["eth_vlan_vid"],16) & 0xFFF
                            rule["vlan_id"] = str(vlan)
                        actionlist=[]
                        for action in details["instructions"]["instruction_apply_actions"]:
                            if action=="output":
                                if translate_of_ports:
                                    port = self.ofi2pp[ details["instructions"]["instruction_apply_actions"]["output"] ]
                                else:
                                    port = details["instructions"]["instruction_apply_actions"]["output"]
                                actionlist.append( ("out",port) )
                            elif action=="strip_vlan":
                                actionlist.append( ("vlan",None) )
                            elif action=="set_vlan_vid":
                                actionlist.append( ("vlan", details["instructions"]["instruction_apply_actions"]["set_vlan_vid"]) )
                            else:
                                self.logger.error("get_of_rules Unknown action in rule %s: %s", rule["name"], str(action))
                                #actionlist.append( (action, str(details["instructions"]["instruction_apply_actions"]) ))
                    rule_dict[str(name)] = rule
            return 0, rule_dict
        except (requests.exceptions.RequestException, ValueError) as e:
            #ValueError in the case that JSON can not be decoded
            error_text = type(e).__name__ + ": " + str(e)
            self.logger.error("get_of_rules " + error_text)
            return -1, error_text

    def obtain_port_correspondence(self):
        '''Obtain the correspondence between physical and openflow port names
        return:
             0, dictionary: with physical name as key, openflow name as value
            -1, error_text: if fails
        '''
        try:
            of_response = requests.get(self.url+"/wm/core/controller/switches/json", headers=self.headers)
            #print vim_response.status_code
            error_text = "Openflow response %d: %s" % (of_response.status_code, of_response.text)
            if of_response.status_code != 200:
                self.logger.warning("obtain_port_correspondence " + error_text)
                return -1 , error_text
            self.logger.debug("obtain_port_correspondence " + error_text)
            info = of_response.json()
            
            if type(info) != list and type(info) != tuple:
                return -1, "unexpected openflow response, not a list. Wrong version?"
            
            index = -1
            if len(info)>0:
                #autodiscover version
                if self.version == None:
                    if 'dpid' in info[0] and 'ports' in info[0]:
                        self._set_version("0.9")
                    elif 'switchDPID' in info[0]:
                        self._set_version("1.X")
                    else:
                        return -1, "unexpected openflow response, Wrong version?"

            for i in range(0,len(info)):
                if info[i][ self.ver_names["dpid"] ] == self.dpid:
                    index = i
                    break
            if index == -1:
                text = "DPID '"+self.dpid+"' not present in controller "+self.url
                #print self.name, ": get_of_controller_info ERROR", text 
                return -1, text
            else:
                if self.version[0]=="0":
                    ports = info[index]["ports"]
                else: #version 1.X
                    of_response = requests.get(self.url+"/wm/core/switch/%s/port-desc/json" %self.dpid, headers=self.headers)
                    #print vim_response.status_code
                    error_text = "Openflow response %d: %s" % (of_response.status_code, of_response.text)
                    if of_response.status_code != 200:
                        self.logger.warning("obtain_port_correspondence " + error_text)
                        return -1 , error_text
                    self.logger.debug("obtain_port_correspondence " + error_text)
                    info = of_response.json()
                    if type(info) != dict:
                        return -1, "unexpected openflow port-desc response, not a dict. Wrong version?"
                    if "portDesc" not in info:
                        return -1, "unexpected openflow port-desc response, 'portDesc' not found. Wrong version?"
                    if type(info["portDesc"]) != list and type(info["portDesc"]) != tuple:
                        return -1, "unexpected openflow port-desc response at 'portDesc', not a list. Wrong version?"
                    ports = info["portDesc"]
                for port in ports:
                    self.pp2ofi[ str(port["name"]) ] = str(port["portNumber"] )
                    self.ofi2pp[ port["portNumber"]] = str(port["name"]) 
            #print self.name, ": get_of_controller_info ports:", self.pp2ofi
            return 0, self.pp2ofi
        except (requests.exceptions.RequestException, ValueError) as e:
            #ValueError in the case that JSON can not be decoded
            error_text = type(e).__name__ + ": " + str(e)
            self.logger.error("obtain_port_correspondence " + error_text)
            return -1, error_text
            
    def del_flow(self, flow_name):
        ''' Delete an existing rule
            Params: flow_name, this is the rule name
            Return
                0, None if ok
                -1, text_error if fails
        '''           
        #autodiscover version
        if self.version == None:
            r,c = self.get_of_switches()
            if r<0:
                return r,c
            elif r==0:
                return -1, "No dpid found "
        try:
            of_response = requests.delete(self.url+"/wm/%s/json" % self.ver_names["URLmodifier"],
                                headers=self.headers, data='{"switch":"%s","name":"%s"}' %(self.dpid, flow_name)
                            )
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
        #get translation, autodiscover version
        if len(self.pp2ofi) == 0:
            r,c = self.obtain_port_correspondence()
            if r<0:
                return r,c
        try:
            #We have to build the data for the floodlight call from the generic data
            sdata = {'active': "true", "name":data["name"]}
            if data.get("priority"):
                sdata["priority"] = str(data["priority"])
            if data.get("vlan_id"):
                sdata[ self.ver_names["vlanid"]  ] = data["vlan_id"]
            if data.get("dst_mac"):
                sdata[  self.ver_names["destmac"]  ] = data["dst_mac"]
            sdata['switch'] = self.dpid
            if not data['ingress_port'] in self.pp2ofi:
                error_text = 'Error. Port '+data['ingress_port']+' is not present in the switch'
                self.logger.warning("new_flow " + error_text)
                return -1, error_text
            
            sdata[  self.ver_names["inport"]  ] = self.pp2ofi[data['ingress_port']]
            sdata['actions'] = ""

            for action in data['actions']:
                if len(sdata['actions']) > 0:
                    sdata['actions'] +=  ','
                if action[0] == "vlan":
                    if action[1]==None:
                        sdata['actions'] += self.ver_names["stripvlan"]
                    else:
                        sdata['actions'] += self.ver_names["setvlan"] + "=" + str(action[1])
                elif action[0] == 'out':
                    sdata['actions'] += "output=" + self.pp2ofi[ action[1] ]


            of_response = requests.post(self.url+"/wm/%s/json" % self.ver_names["URLmodifier"],
                                headers=self.headers, data=json.dumps(sdata) )
            error_text = "Openflow response %d: %s" % (of_response.status_code, of_response.text)
            if of_response.status_code != 200:
                self.logger.warning("new_flow " + error_text)
                return -1 , error_text
            self.logger.debug("new_flow OK" + error_text)
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
        #autodiscover version
        if self.version == None:
            r,c = self.get_of_switches()
            if r<0:
                return r,c
            elif r==0: #empty
                return 0, None
        try:
            url = self.url+"/wm/%s/clear/%s/json" % (self.ver_names["URLmodifier"], self.dpid)
            of_response = requests.get(url )
            error_text = "Openflow response %d: %s" % (of_response.status_code, of_response.text)
            if of_response.status_code < 200 or of_response.status_code >= 300:
                self.logger.warning("clear_all_flows " + error_text)
                return -1 , error_text
            self.logger.debug("clear_all_flows OK " + error_text)
            return 0, None
        except requests.exceptions.RequestException as e:
            error_text = type(e).__name__ + ": " + str(e)
            self.logger.error("clear_all_flows " + error_text)
            return -1, error_text

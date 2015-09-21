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

class FL_conn():
    '''Floodlight connector. No MAC learning is used'''
    def __init__(self, of_ip, of_port, of_dpid, of_version=None):

        self.name = "Floodlight"
        self.dpid = str(of_dpid)
        self.url = "http://%s:%s" %( str(of_ip), str(of_port) )

        self.pp2ofi={}  # Physical Port 2 OpenFlow Index
        self.headers = {'content-type':'application/json', 'Accept':'application/json'}
        self.version= None
        if of_version!=None:
            self._set_version(of_version)
    
    def _set_version(self, version):
        #static version names
        if version=="0.9":
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
                "rule_inport":  "inputPort",
                "rule_dstmac":  "dataLayerDestination",
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
                "rule_inport":  "in_port",
                "rule_dstmac":  "eth_dst",
            }
        else:
            self.version= None
            
    def get_of_switches(self):
        try:
            of_response = requests.get(self.url+"/wm/core/controller/switches/json", headers=self.headers)
            #print vim_response.status_code
            if of_response.status_code != 200:
                print self.name, ": get_of_controller_info:", self.url, of_response
                raise requests.exceptions.RequestException("Openflow response " + str(of_response.status_code))
            info = of_response.json()
            if type(info) != list and type(info) != tuple:
                return -1, "unexpected openflow response, not a list. Wrong version?"
            if len(info)==0:
                return 0, info
            #autodiscover version
            if self.version == None:
                if 'dpid' in info[0] and 'inetAddress' in info[0]:
                    self._set_version("0.9")
                elif 'switchDPID' in info[0] and 'inetAddress' in info[0]:
                    self._set_version("1.X")
                else:
                    return -1, "unexpected openflow response, Wrong version?"
            
            switch_list=[]
            for switch in info:
                switch_list.append( (switch[ self.ver_names["dpid"] ], switch['inetAddress']) )
            return 0, switch_list
        except requests.exceptions.RequestException, e:
            print self.name, ": get_of_switches Exception:", str(e)
            return -1, str(e)
        except ValueError, e: # the case that JSON can not be decoded
            print self.name, ": get_of_switches Exception:", str(e)
            return -1, str(e)

    def get_of_rules(self, dpid=None):
        if dpid==None:
            if self.dpid==None:
                return -1, "You must provide a dpid"
            else:
                dpid=self.dpid
        
        #autodiscover version
        if self.version == None:
            r,c = self.get_of_switches()
            if r<0:
                return r,c
            elif r==0:
                return -1, "No dpid found "
        #get rules
        try:
            of_response = requests.get(self.url+"/wm/%s/list/%s/json" %(self.ver_names["URLmodifier"], dpid),
                                        headers=self.headers)
            #print vim_response.status_code
            if of_response.status_code != 200:
                print self.name, ": get_of_rules:", self.url, of_response
                raise requests.exceptions.RequestException("Openflow response " + str(of_response.status_code))
            info = of_response.json()
            rule_list=[]
            for switch,switch_info in info.iteritems():
                for name,details in switch_info.iteritems():
                    rule = {}
                    rule["switch"] = str(switch)
                    rule["active"] = "true"
                    rule["name"] = str(name)
                    rule["priority"] = str(int(details["priority"]))
                    if self.version[0]=="0":
                        rule["inport"] = str(details["match"]["inputPort"]) 
                        dst_mac = details["match"]["dataLayerDestination"]
                        if dst_mac != "00:00:00:00:00:00":
                            rule["dst_mac"] = dst_mac
                        vlan = details["match"]["dataLayerVirtualLan"]
                        if vlan != -1:
                            rule["vlan_id"] = str(vlan)
                        actionlist=[]
                        for action in details["actions"]:
                            if action["type"]=="OUTPUT":
                                actionlist.append( ("out",action["port"]) )
                            elif action["type"]=="STRIP_VLAN":
                                actionlist.append( ("vlan",None) )
                            elif action["type"]=="SET_VLAN_ID":
                                actionlist.append( ("vlan", action["virtualLanIdentifier"]) )
                            else:
                                actionlist.append( (action["type"], str(action) ))
                                print "Unknown action in rule %s: %s" % (rule["name"], str(action))
                            rule["actions"] = actionlist
                        rule_list.append(rule)
                    elif self.version[0]=="1":
                        rule["inport"] = details["match"]["in_port"]
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
                                actionlist.append( ("out",details["instructions"]["instruction_apply_actions"]["output"]) )
                            elif action=="strip_vlan":
                                actionlist.append( ("vlan",None) )
                            elif action=="set_vlan_vid":
                                actionlist.append( ("vlan", details["instructions"]["instruction_apply_actions"]["set_vlan_vid"]) )
                            else:
                                actionlist.append( (action, str(details["instructions"]["instruction_apply_actions"]) ))
                                print "Unknown action in rule %s: %s" % (rule["name"], str(action))
            return 0, rule_list
        except requests.exceptions.RequestException, e:
            print self.name, ": get_of_rules Exception:", str(e)
            return -1, str(e)
        except ValueError, e: # the case that JSON can not be decoded
            print self.name, ": get_of_rules Exception:", str(e)
            return -1, str(e)

    def obtain_port_correspondence(self):
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
            if len(info)>0:
                #autodiscover version
                if self.version == None:
                    if 'dpid' in info[0] and 'ports' in info[0]:
                        self._set_version("0.9")
                    elif 'switchDPID' in info[0] and 'ports' in info[0]:
                        self._set_version("1.X")
                    else:
                        return -1, "unexpected openflow response, Wrong version?"

            for i in range(0,len(info)):
                if info[i][ self.ver_names["dpid"] ] == self.dpid:
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
            print self.name, ": del_flow", flow_name, of_response
            #print vim_response.status_code
            if of_response.status_code != 200:
                raise requests.exceptions.RequestException("Openflow response " + str(of_response.status_code))
            return 0, None

        except requests.exceptions.RequestException, e:
            print self.name, ": del_flow", flow_name, "Exception:", str(e)
            return -1, str(e)

    def new_flow(self, data):
        #autodiscover version
        if self.version == None:
            r,c = self.get_of_switches()
            if r<0:
                return r,c
            elif r==0:
                return -1, "No dpid found "
        try:
            #We have to build the data for the floodlight call from the generic data
            sdata = {'active': "true", "priority":str(data["priority"]), "name":data["name"]}
            if data.get("vlan_id"):
                sdata[ self.ver_names["vlanid"]  ] = data["vlan_id"]
            if data.get("dst_mac"):
                sdata[  self.ver_names["dstmac"]  ] = data["dst_mac"]
            sdata['switch'] = self.dpid
            sdata[  self.ver_names["inport"]  ] = self.pp2ofi[data['ingress_port']]
            sdata['actions'] = ""

            for action in data['actions']:
                if len(sdata['actions']) > 0:
                    sdata['actions'] +=  ', '
                if action[0] == "vlan":
                    if action[1]==None:
                        sdata['actions'] += self.ver_names["stripvlan"]
                    else:
                        sdata['actions'] += self.ver_names["setvlan"] + "=" + str(action[1])
                elif action[0] == 'out':
                    sdata['actions'] += "output=" + self.pp2ofi[ action[1] ]


            of_response = requests.post(self.url+"/wm/%s/json" % self.ver_names["URLmodifier"],
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
        #autodiscover version
        if self.version == None:
            r,c = self.get_of_switches()
            if r<0:
                return r,c
            elif r==0: #empty
                return 0, None
        try:
            of_response = requests.get(self.url+"/wm/%s/clear/%s/json" % (self.ver_names["URLmodifier"], self.dpid) )
            print self.name, ": clear_all_flows:", of_response
            if of_response.status_code != 200:
                raise requests.exceptions.RequestException("Openflow response " + str(of_response.status_code))
            return 0, None
        except requests.exceptions.RequestException, e:
            print self.name, ": clear_all_flows Exception:", str(e)
            return -1, str(e)

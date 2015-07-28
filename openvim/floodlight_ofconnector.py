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
This is the class extending ofconnector class that implements the methods to interact
with a Floodlight Openflow Controller through the openflow program.
'''

import os
import requests
import json
import sys
from ofconnector import ofconnector

class floodlight_ofconnector(ofconnector):
    of_controller_version = "0.9"
    of_controller_ip = "localhost"
    of_controller_port = "7070"
    of_controller_dpid = "00:01:02:03:04:05:06:07"
    
    def __init__(self, version, ip, port, dpid):
        of_controller_version = version
        of_controller_ip = ip
        of_controller_port = port
        of_controller_dpid = dpid
        return
        
    def print_of_switches(self, verbose):
        URLrequest = "http://%s:%s/wm/core/controller/switches/json" %(of_controller_ip, of_controller_port)
        ofc_response = requests.get(URLrequest)
        #print ofc_response
        if verbose==None:
            verbose=0
        if ofc_response.status_code == 200:
            content = ofc_response.json()
            if verbose>0:
                print json.dumps(content, indent=4)
            else:
                for switch in content:
                    if of_controller_version[0]=="0":
                        print "%s %s" %(switch['dpid'], switch['inetAddress'])
                    elif of_controller_version[0]>"0":
                        print "%s %s" %(switch['switchDPID'], switch['inetAddress'])                                 
        else:
            print ofc_response.text
        return

    def print_of_list(self, verbose):
        if of_controller_version[0]=="0":
            URLrequest = "http://%s:%s/wm/staticflowentrypusher/list/%s/json" %(of_controller_ip, of_controller_port, of_controller_dpid)
        elif of_controller_version[0]>"0":
            URLrequest = "http://%s:%s/wm/staticflowpusher/list/%s/json" %(of_controller_ip, of_controller_port, of_controller_dpid)
        ofc_response = requests.get(URLrequest)
        #print ofc_response
        if verbose==None:
            verbose=0
        if ofc_response.status_code == 200:
            content = ofc_response.json()
            if verbose>0:
                print json.dumps(content, indent=4)
            else:
                #print json.dumps(content, indent=4)
                if of_controller_version[0]=="0":
                    for switch,switch_info in content.iteritems():
                        for name,details in switch_info.iteritems():
                            rule = {}
                            rule["switch"] = str(switch)
                            rule["active"] = "true"
                            rule["name"] = str(name)
                            rule["priority"] = str(int(details["priority"]))
                            rule["ingress-port"] = str(details["match"]["inputPort"]) 
                            dst_mac = details["match"]["dataLayerDestination"]
                            if dst_mac <> "00:00:00:00:00:00":
                                rule["dst-mac"] = dst_mac
                            vlan = details["match"]["dataLayerVirtualLan"]
                            if vlan <> -1:
                                rule["vlan-id"] = str(vlan)
                            actionlist=[]
                            for action in details["actions"]:
                                if action["type"]=="OUTPUT":
                                    actionlist.append("output=%s" %(action["port"]))
                                elif action["type"]=="STRIP_VLAN":
                                    actionlist.append("strip-vlan")
                                elif action["type"]=="SET_VLAN_ID":
                                    actionlist.append("set-vlan-id=%s" %(action["virtualLanIdentifier"]))
                                else:
                                    print "Unknown action in rule %s" %(rule["name"])
                                    continue
                            rule["actions"] = ",".join(actionlist)
                            print "%s  %s  %s  input=%s  dst-mac=%s  vlan-id=%s  actions=%s" %(rule["switch"], rule["priority"].ljust(6), rule["name"].ljust(20), rule["ingress-port"].ljust(3), \
                                                                 rule.get("dst-mac","any").ljust(18), rule.get("vlan-id","any").ljust(4), rule["actions"])
                elif of_controller_version[0]>"0":
                    for switch,switch_info in content.iteritems():
                        for info in switch_info:
                            for rule_name,details in info.iteritems():
                                rule = {}
                                rule["switch"] = str(switch)
                                rule["active"] = "true"
                                rule["name"] = rule_name
                                rule["priority"] = details["priority"]
                                rule["ingress-port"] = details["match"]["in_port"] 
                                if "eth_dst" in details["match"]:
                                    dst_mac = details["match"]["eth_dst"]
                                    if dst_mac <> "00:00:00:00:00:00":
                                        rule["dst-mac"] = dst_mac
                                if "eth_vlan_vid" in details["match"]:
                                    vlan = int(details["match"]["eth_vlan_vid"],16) & 0xFFF
                                    rule["vlan-id"] = str(vlan)
                                actionlist=[]
                                for action in details["instructions"]["instruction_apply_actions"]:
                                    if action=="output":
                                        actionlist.append("output=%s" %details["instructions"]["instruction_apply_actions"]["output"])
                                    elif action=="strip_vlan":
                                        actionlist.append("strip_vlan")
                                    elif action=="set_vlan_vid":
                                        actionlist.append("set_vlan_vid=%s" %details["instructions"]["instruction_apply_actions"]["set_vlan_vid"])
                                    else:
                                        print "Unknown action in rule %s" %(rule["name"])
                                        continue
                                rule["actions"] = ",".join(actionlist)
                                print "%s  %s  %s  input=%s  dst-mac=%s  vlan-id=%s  actions=%s" %(rule["switch"], rule["priority"].ljust(6), rule["name"].ljust(20), rule["ingress-port"].ljust(3), \
                                                                     rule.get("dst-mac","any").ljust(18), rule.get("vlan-id","any").ljust(4), rule["actions"])
        else:
            print ofc_response.text
        return
    
    def print_of_dump(self):
        if of_controller_version[0]=="0":
            URLrequest = "http://%s:%s/wm/staticflowentrypusher/list/%s/json" %(of_controller_ip, of_controller_port, of_controller_dpid)
        elif of_controller_version[0]>"0":
            URLrequest = "http://%s:%s/wm/staticflowpusher/list/%s/json" %(of_controller_ip, of_controller_port, of_controller_dpid)
        ofc_response = requests.get(URLrequest)
        #print ofc_response
        if ofc_response.status_code == 200:
            content = ofc_response.json()
            print json.dumps(content, indent=4)
        else:
            print ofc_response.text
        return

    def of_clear(self):
        if of_controller_version[0]=="0":
            URLrequest = "http://%s:%s/wm/staticflowentrypusher/clear/%s/json" %(of_controller_ip, of_controller_port, of_controller_dpid)
        elif of_controller_version[0]>"0":
            URLrequest = "http://%s:%s/wm/staticflowpusher/clear/%s/json" %(of_controller_ip, of_controller_port, of_controller_dpid)
        ofc_response = requests.get(URLrequest)
        #print ofc_response
        if ofc_response.status_code == 200:
            content = ofc_response.json()
            print json.dumps(content, indent=4)
        else:
            print ofc_response.text
        return

    def of_install(self, dumpfile):
        f = file(dumpfile, "r")
        ofrules = f.read()
        f.close()
        
        ofrules = json.loads(ofrules)
        #print json.dumps(ofrules, indent=4)
        if of_controller_version[0]=="0":
            ofc_version_URLmodifier="staticflowentrypusher"
        elif of_controller_version[0]>"0":
            ofc_version_URLmodifier="staticflowpusher"
        #Edit the rules conveniently
        if of_controller_version[0]=="0":
            for switch,switch_info in ofrules.iteritems():
                for name,details in switch_info.iteritems():
                    rule = {}
                    rule["switch"] = str(switch)
                    rule["active"] = "true"
                    rule["name"] = str(name)
                    rule["priority"] = str(int(details["priority"]))
                    rule["ingress-port"] = str(details["match"]["inputPort"]) 
                    dst_mac = details["match"]["dataLayerDestination"]
                    if dst_mac <> "00:00:00:00:00:00":
                        rule["dst-mac"] = dst_mac
                    vlan = details["match"]["dataLayerVirtualLan"]
                    if vlan <> -1:
                        rule["vlan-id"] = vlan
                    actionlist=[]
                    for action in details["actions"]:
                        actionlist.append("output=%s" %(action["port"]))
                    rule["actions"] = ",".join(actionlist)
                    payload_req = json.dumps(rule, indent=4)
                    print payload_req
                    headers_req = {'content-type': 'application/json'}
                    URLrequest = "http://%s:%s/wm/%s/json" %(of_controller_ip, of_controller_port, ofc_version_URLmodifier)
                    ofc_response = requests.post(URLrequest, headers = headers_req, data=payload_req)
                    print ofc_response
        elif of_controller_version[0]>"0":
            for switch,switch_info in ofrules.iteritems():
                for info in switch_info:
                    for rule_name,details in info.iteritems():
                        rule = {}
                        rule["switch"] = str(switch)
                        rule["active"] = "true"
                        rule["name"] = rule_name
                        rule["priority"] = details["priority"]
                        rule["in_port"] = details["match"]["in_port"] 
                        dst_mac = details["match"]["eth_dst"]
                        if dst_mac <> "00:00:00:00:00:00":
                            rule["eth_dst"] = dst_mac
                        if "eth_vlan_vid" in details["match"]:
                            vlan = int(details["match"]["eth_vlan_vid"],16) & 0xFFF
                            rule["eth_vlan_vid"] = str(vlan)
                        actionlist=[]
                        for action in details["instructions"]["instruction_apply_actions"]:
                            if action=="output":
                                actionlist.append("output=%s" %details["instructions"]["instruction_apply_actions"]["output"])
                            elif action=="strip_vlan":
                                actionlist.append("strip_vlan")
                            elif action=="set_vlan_vid":
                                actionlist.append("set_vlan_vid=%s" %details["instructions"]["instruction_apply_actions"]["set_vlan_vid"])
                            else:
                                print "Unknown action in rule %s" %(rule["name"])
                                continue
                        rule["actions"] = ",".join(actionlist)
                        payload_req = json.dumps(rule, indent=4)
                        print payload_req
                        headers_req = {'content-type': 'application/json'}
                        URLrequest = "http://%s:%s/wm/%s/json" %(of_controller_ip, of_controller_port, ofc_version_URLmodifier)
                        ofc_response = requests.post(URLrequest, headers = headers_req, data=payload_req)
                        print ofc_response
        return

    def of_add(self, name, inport, outport, verbose, priority, matchmac, matchvlan, stripvlan, setvlan):
        rule = {}
        rule["switch"] = of_controller_dpid
        rule["active"] = "true"
        rule["name"] = name
        rule["priority"] = str(priority)
        ofc_version_URLmodifier=""
        match_destmac_string=""
        match_vlanid_string=""
        action_ingress_port_string=""
        action_vlanid_string=""
        action_stripvlan_string=""
        if of_controller_version[0]=="0":
            ofc_version_URLmodifier="staticflowentrypusher"
            match_destmac_string="dst-mac"
            match_vlanid_string="vlan-id"
            action_ingress_port_string="ingress-port"
            action_vlanid_string="set-vlan-id"
            action_stripvlan_string="strip-vlan"
        elif of_controller_version[0]>"0":
            ofc_version_URLmodifier="staticflowpusher"
            match_destmac_string="eth_dst"
            match_vlanid_string="eth_vlan_vid"
            action_ingress_port_string="in_port"
            action_vlanid_string="set_vlan_vid"
            action_stripvlan_string="strip_vlan"
        rule[action_ingress_port_string] = str(inport) 
        if matchmac!=None:
            rule[match_destmac_string] = matchmac
        if matchvlan!=None:
            rule[match_vlanid_string] = str(matchvlan)
        actionlist=[]
        if stripvlan!=None:
            actionlist.append(action_stripvlan_string)
        if setvlan!=None:
            actionlist.append("%s=%d" %(action_vlanid_string, setvlan))
        actionlist.append("output=%d" %(outport))
        rule["actions"] = ",".join(actionlist)
        payload_req = json.dumps(rule, indent=4)
        #print payload_req
        headers_req = {'content-type': 'application/json'}
        URLrequest = "http://%s:%s/wm/%s/json" %(of_controller_ip, of_controller_port, ofc_version_URLmodifier)
        ofc_response = requests.post(URLrequest, headers = headers_req, data=payload_req)
        if verbose==None:
            verbose=0
        if ofc_response.status_code == 200:
            content = ofc_response.json()
            if verbose>0:
                print json.dumps(content, indent=4)
            else:
                print "OK"
        else:
            print ofc_response.text
        return
                
        return

    def of_delete(self, name, verbose):
        rule = {}
        rule["switch"] = of_controller_dpid
        rule["name"] = name
        payload_req = json.dumps(rule, indent=4)
        #print payload_req
        if of_controller_version[0]=="0":
            ofc_version_URLmodifier="staticflowentrypusher"
        elif of_controller_version[0]>"0":
            ofc_version_URLmodifier="staticflowpusher"
        URLrequest = "http://%s:%s/wm/%s/json" %(of_controller_ip, of_controller_port, ofc_version_URLmodifier)
        headers_req = {'content-type': 'application/json'}
        ofc_response = requests.delete(URLrequest, headers = headers_req, data=payload_req)
        if ofc_response.status_code == 200:
            content = ofc_response.json()
            if verbose>0:
                print json.dumps(content, indent=4)
            else:
                print "DELETED"
        else:
            print ofc_response.text
        return


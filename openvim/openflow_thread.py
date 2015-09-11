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
__date__ ="17-jul-2015"


#import json
import threading
import time
import Queue
import requests

class openflow_thread(threading.Thread):
    def __init__(self, OF_connector, db, db_lock, of_test, pmp_with_same_vlan):
        threading.Thread.__init__(self)

        self.db = db
        self.pmp_with_same_vlan = pmp_with_same_vlan
        self.name = "openflow"
        self.test = of_test
        self.db_lock = db_lock
        self.OF_connector = OF_connector

        self.queueLock = threading.Lock()
        self.taskQueue = Queue.Queue(2000)
        
    def insert_task(self, task, *aditional):
        try:
            self.queueLock.acquire()
            task = self.taskQueue.put( (task,) + aditional, timeout=5) 
            self.queueLock.release()
            return 1, None
        except Queue.Full:
            return -1, "timeout inserting a task over openflow thread " + self.name

    def run(self):
        while True:
            self.queueLock.acquire()
            if not self.taskQueue.empty():
                task = self.taskQueue.get()
            else:
                task = None
            self.queueLock.release()

            if task is None:
                time.sleep(1)
                continue        

            print self.name, ": processing task", task
            if task[0] == 'update-net':
                r,c = self.update_of_flows(task[1])
                #updata database status
                self.db_lock.acquire()
                if r<0:
                    UPDATE={'status':'ERROR', 'last_error': str(c)}
                else:
                    UPDATE={'status':'ACTIVE'}
                self.db.update_rows('nets', UPDATE, WHERE={'uuid':task[1]})
                self.db_lock.release()

            elif task[0] == 'clear-all':
                self.clear_all_flows()
            elif task[0] == 'exit':
                self.terminate()
                return 0
            else:
                print self.name, ": unknown task", task
                
    def terminate(self):
        print self.name, ": exit from openflow_thread"

    def update_of_flows(self, net_id):
        self.db_lock.acquire()
        result, content = self.db.get_table(FROM='nets', SELECT=('type','admin_state_up', 'vlan', 'bind'),
                                            WHERE={'uuid':net_id} )
        self.db_lock.release()
        if result < 0:
            print self.name, ": update_of_flows() ERROR getting net", content
            return -1, "ERROR getting net " + content
        elif result==0:
            #net has been deleted
            ifaces_nb = 0
        else:
            net = content[0]
        
            if net['admin_state_up'] == 'false':
                ifaces_nb = 0
            else:
                self.db_lock.acquire()
                ifaces_nb, ports = self.db.get_table(
                        FROM='ports',
                        SELECT=('switch_port','vlan','uuid','mac','type','model'),
                        WHERE={'net_id':net_id, 'admin_state_up':'true', 'status':'ACTIVE'} )
                self.db_lock.release()
                if ifaces_nb < 0:
                    print self.name, ": update_of_flows() ERROR getting ports", ports
                    return -1, "ERROR getting ports "+ ports
                
                #add the binding as an external port
                if net['bind'] and net['bind'][:9]=="openflow:":
                    external_port={"type":"external","mac":None}
                    if net['bind'][-5:]==":vlan":
                        external_port["vlan"] = net["vlan"]
                        external_port["switch_port"] = net['bind'][9:-5]
                    else:
                        external_port["vlan"] = None
                        external_port["switch_port"] = net['bind'][9:]
                    ports = ports + (external_port,)
                    ifaces_nb+=1
        
        # Get the name of flows that will be affected by this NET or net_id==NULL that means
        # net deleted (At DB foreign key: On delete set null)
        self.db_lock.acquire()
        result, old_flows = self.db.get_table(FROM='of_flows', WHERE={'net_id':net_id},
                                          WHERE_OR={'net_id':None} )
        self.db_lock.release()
        if result < 0:
            print self.name, ": update_of_flows() ERROR getting flows", old_flows
            return -1, "ERROR getting flows " + old_flows

        if ifaces_nb < 2:
            pass
        elif net['type'] == 'ptp':
            if ifaces_nb > 2:
                print self.name, 'Error, network '+str(net_id)+' has been defined as ptp but it has '+\
                                 str(ifaces_nb)+' interfaces.'
                return -1, 'Error, network '+str(net_id)+' has been defined as ptp but it has '+\
                       str(ifaces_nb)+' interfaces.'
        elif net['type'] == 'data':
            if ifaces_nb > 2 and self.pmp_with_same_vlan:
                # check all ports are VLAN (tagged) or none
                vlan_tag = None
                for port in ports:
                    if port["type"]=="external":
                        if port["vlan"] != None:
                            if port["vlan"]!=net["vlan"]:
                                text="Error external port vlan-tag and net vlan-tag must be the same when flag 'of_controller_nets_with_same_vlan' is True"
                                print self.name, text
                                return -1, text
                            if vlan_tag == None:
                                vlan_tag=True
                            elif vlan_tag==False:
                                text="Error passthrough and external port vlan-tagged can not be connected when flag 'of_controller_nets_with_same_vlan' is True"
                                print self.name, text
                                return -1, text
                        else:
                            if vlan_tag == None:
                                vlan_tag=False
                            elif vlan_tag == True:
                                text="Error SR-IOV and external port not vlan-tagged can not be connected when flag 'of_controller_nets_with_same_vlan' is True"
                                print self.name, text
                                return -1, text
                    elif port["model"]=="PF" or port["model"]=="VFnotShared":
                        if vlan_tag == None:
                            vlan_tag=False
                        elif vlan_tag==True:
                            text="Error passthrough and SR-IOV ports cannot be connected when flag 'of_controller_nets_with_same_vlan' is True"
                            print self.name, text
                            return -1, text
                    elif port["model"] == "VF":
                        if vlan_tag == None:
                            vlan_tag=True
                        elif vlan_tag==False:
                            text="Error passthrough and SR-IOV ports cannot be connected when flag 'of_controller_nets_with_same_vlan' is True"
                            print self.name, text
                            return -1, text
        else:
            return -1, 'Only ptp and data networks are supported for openflow'
            
        # calculate new flows to be inserted
        result, new_flows = self._compute_net_flows(net_id, ports)
        if result < 0:
            return result, new_flows

        #modify database flows format and get the used names
        used_names=[]
        for flow in old_flows:
            self._change_db2of(flow)
            used_names.append(flow['name'])
        name_index=0
        #insert at database the new flows, change actions to human text
        for flow in new_flows:
            #1 check if an equal flow is already present
            index = self._check_flow_already_present(flow, old_flows)
            if index>=0:
                old_flows[index]["not delete"]=True
                print self.name, ": skipping already present flow", flow
                continue
            #2 look for a non used name
            flow_name=flow["net_id"]+"_"+str(name_index)
            while flow_name in used_names:         
                name_index += 1   
                flow_name=flow["net_id"]+"_"+str(name_index)
            used_names.append(flow_name)
            flow['name'] = flow_name
            #3 insert at openflow
            r,c = self.OF_connector.new_flow(flow)
            if r < 0:
                print self.name, ": Error '%s' at flow insertion" % c, flow
                return -1, content
            #4 insert at database
            self._change_of2db(flow)
            self.db_lock.acquire()
            result, content = self.db.new_row('of_flows', flow)
            self.db_lock.release()
            if result < 0:
                print self.name, ": Error '%s' at database insertion" % content, flow
                return -1, content

        #delete not needed old flows from openflow and from DDBB
        for flow in old_flows:
            if "not delete" in flow:
                continue
            #print self.name, ": update_of_flows() Deleting", flow['name']
            r,c= self.OF_connector.del_flow(flow['name'])
            self.db_lock.acquire()
            if r>=0:
                self.db.delete_row_by_key('of_flows', 'id', flow['id'])
            else:
                #keep the flow, but put in actions the error
                #self.db.update_rows('of_flows', {'actions':c}, {'id':flow['id']})
                print self.name, ": Error '%s' at flow deletion" % c, flow
            self.db_lock.release()
        
        return 0, 'Success'

    def clear_all_flows(self):
        try:
            if not self.test:
                self.OF_connector.clear_all_flows()
            #remove from database
            self.db_lock.acquire()
            self.db.delete_row_by_key('of_flows', None, None) #this will delete all lines
            self.db_lock.release()
            return 0, None
        except requests.exceptions.RequestException, e:
            print self.name, ": clear_all_flows Exception:", str(e)
            return -1, str(e)

    flow_fields=('priority', 'vlan', 'ingress_port', 'actions', 'dst_mac', 'src_mac', 'net_id')
    def _check_flow_already_present(self, new_flow, flow_list):
        '''check if the same flow is already present in the flow list
        The flow is repeated if all the fields, apart from name, are equal
        Return the index of matching flow, -1 if not match'''
        index=0
        for flow in flow_list:
            equal=True
            for f in self.flow_fields:
                if flow.get(f) != new_flow.get(f):
                    equal=False
                    break
            if equal:
                return index
            index += 1
        return -1
        
    def _change_of2db(self, flow):
        '''Change 'flow' dictionary from openflow format to database format
        Basically the change consist of changing 'flow[actions] from a list of
        double tuple to a string
        from [(A,B),(C,D),..] to "A=B,C=D" '''
        action_str_list=[]
        for action in flow['actions']:
            action_str_list.append( action[0] + "=" + str(action[1]) )
        flow['actions'] = ",".join(action_str_list)
            
    def _change_db2of(self, flow):
        '''Change 'flow' dictionary from database format to openflow format
        Basically the change consist of changing 'flow[actions] from a string to 
        a double tuple list
        from "A=B,C=D,..." to [(A,B),(C,D),..] '''
        actions=[]
        action_list = flow['actions'].split(",")
        for action_item in action_list:
            action_tuple = action_item.split("=")
            if action_tuple[1]=="None":
                action_tuple[1] = None
            elif action_tuple[0]=="vlan":
                action_tuple[1] = int(action_tuple[1])
            actions.append( (action_tuple[0],action_tuple[1]) )
        flow['actions'] = actions

    def _compute_net_flows(self, net_id, ports):
        new_flows=[]
        nb_rules = len(ports)

        # Check switch_port information is right
        if not self.test:
            for port in ports:
                if str(port['switch_port']) not in self.OF_connector.pp2ofi and not self.test:
                    error_text= "switch port name '%s' is not valid for the openflow controller" % str(port['switch_port'])
                    print self.name, ": ERROR " + error_text
                    return -1, error_text
            
        # Insert rules so each point can reach other points using dest mac information
        for src_port in ports:
            for dst_port in ports:
                #if src_port == dst_port:
                #    continue
                if src_port['switch_port'] == dst_port['switch_port'] and src_port['vlan'] == dst_port['vlan']:
                    continue
                flow = {
                    "priority": 1000,
                    'net_id':  net_id,
                    "ingress_port": str(src_port['switch_port']),
                    'actions': []
                }
                # allow that one port have no mac
                if dst_port['mac'] is None or nb_rules==2:  # point to point or nets with 2 elements
                    flow['priority'] = 990  # less priority
                else:
                    flow['dst_mac'] = str(dst_port['mac'])
                    
                if src_port['vlan'] is not None:
                    flow['vlan_id'] = str(src_port['vlan'])
    
                if dst_port['vlan'] is None:
                    if src_port['vlan'] is not None:
                        flow['actions'].append( ('vlan',None) )
                else:
                    flow['actions'].append( ('vlan', dst_port['vlan']) )
                flow['actions'].append( ('out', str(dst_port['switch_port'])) )
    
                if self._check_flow_already_present(flow, new_flows) >= 0:
                    print self.name, ": skipping repeated flow", flow
                    continue
                
                new_flows.append(flow)
        
        # BROADCAST:
        if nb_rules > 2:  # point to multipoint or nets with more than 2 elements
            for src_port in ports:
                flow = {'priority': 1000,
                    'net_id':  net_id,
                    'dst_mac': 'ff:ff:ff:ff:ff:ff',
                    'actions': []
                }

                flow['ingress_port'] = str(src_port['switch_port'])
                if src_port['vlan'] is not None:
                    flow['vlan_id'] = str(src_port['vlan'])
                    last_vlan = 0  # indicates that a packet contains a vlan, and the vlan
                else:
                    last_vlan = None
                
                for dst_port in ports:
                    if src_port == dst_port: continue
                    if src_port['switch_port']==dst_port['switch_port'] and src_port['vlan']==dst_port['vlan']:
                        continue #same physical port and same vlan, skip
                    if last_vlan != dst_port['vlan']:
                        flow['actions'].append( ('vlan', dst_port['vlan']) ) #dst_port["vlan"]==None means strip-vlan
                        last_vlan = dst_port['vlan']
                    out= ('out', str(dst_port['switch_port']))
                    if out not in flow['actions']:
                        flow['actions'].append( out )
                
                if len(flow['actions'])==0:
                    continue #nothing to do, skip

                if self._check_flow_already_present(flow, new_flows) >= 0:
                    print self.name, ": skipping repeated flow", flow
                    continue
                
                new_flows.append(flow)
            
        return 0, new_flows


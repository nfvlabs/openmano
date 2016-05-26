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
import logging

class FlowBadFormat(Exception):
    '''raise when a bad format of flow is found''' 

def change_of2db(flow):
    '''Change 'flow' dictionary from openflow format to database format
    Basically the change consist of changing 'flow[actions] from a list of
    double tuple to a string
    from [(A,B),(C,D),..] to "A=B,C=D" '''
    action_str_list=[]
    if type(flow)!=dict or "actions" not in flow:
        raise FlowBadFormat("Bad input parameters, expect dictionary with 'actions' as key")
    try:
        for action in flow['actions']:
            action_str_list.append( action[0] + "=" + str(action[1]) )
        flow['actions'] = ",".join(action_str_list)
    except:
        raise FlowBadFormat("Unexpected format at 'actions'")

def change_db2of(flow):
    '''Change 'flow' dictionary from database format to openflow format
    Basically the change consist of changing 'flow[actions]' from a string to 
    a double tuple list
    from "A=B,C=D,..." to [(A,B),(C,D),..] 
    raise FlowBadFormat '''
    actions=[]
    if type(flow)!=dict or "actions" not in flow or type(flow["actions"])!=str:
        raise FlowBadFormat("Bad input parameters, expect dictionary with 'actions' as key")
    action_list = flow['actions'].split(",")
    for action_item in action_list:
        action_tuple = action_item.split("=")
        if len(action_tuple) != 2:
            raise FlowBadFormat("Expected key=value format at 'actions'")
        if action_tuple[0].strip().lower()=="vlan":
            if action_tuple[1].strip().lower() in ("none", "strip"):
                actions.append( ("vlan",None) )
            else:
                try:
                    actions.append( ("vlan", int(action_tuple[1])) )
                except:
                    raise FlowBadFormat("Expected integer after vlan= at 'actions'")
        elif action_tuple[0].strip().lower()=="out":
            actions.append( ("out", str(action_tuple[1])) )
        else:
            raise FlowBadFormat("Unexpected '%s' at 'actions'"%action_tuple[0])
    flow['actions'] = actions



class of_test_connector():
    '''This is a fake openflow connector for testing.
        It does nothing and it is used for running openvim without an openflow controller 
    '''
    def __init__(self, params):
        self.name = "ofc_test"
        self.rules={}
        self.logger = logging.getLogger('vim.OF.TEST')
        self.logger.setLevel( getattr(logging, params.get("of_debug", "ERROR") ) )
    def get_of_switches(self):
        return 0, ()
    def obtain_port_correspondence(self):
        return 0, ()
    def del_flow(self, flow_name):
        if flow_name in self.rules:
            self.logger.debug("del_flow OK")
            del self.rules[flow_name]
            return 0, None
        else:
            self.logger.warning("del_flow not found")
            return -1, "flow %s not found"
    def new_flow(self, data):
        self.rules[ data["name"] ] = data
        self.logger.debug("new_flow OK")
        return 0, None
    def get_of_rules(self, translate_of_ports=True):
        return 0, self.rules

    def clear_all_flows(self):
        self.logger.debug("clear_all_flows OK")
        self.rules={}
        return 0, None



class openflow_thread(threading.Thread):
    def __init__(self, OF_connector, db, db_lock, of_test, pmp_with_same_vlan, debug='ERROR'):
        threading.Thread.__init__(self)

        self.db = db
        self.pmp_with_same_vlan = pmp_with_same_vlan
        self.name = "openflow"
        self.test = of_test
        self.db_lock = db_lock
        self.OF_connector = OF_connector
        self.logger = logging.getLogger('vim.OF')
        self.logger.setLevel( getattr(logging, debug) )

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

            if task[0] == 'update-net':
                r,c = self.update_of_flows(task[1])
                #update database status
                self.db_lock.acquire()
                if r<0:
                    UPDATE={'status':'ERROR', 'last_error': str(c)}
                    self.logger.error("processing task 'update-net' %s: %s", str(task[1]), c)
                else:
                    UPDATE={'status':'ACTIVE', 'last_error': None}
                    self.logger.debug("processing task 'update-net' %s: OK", str(task[1]))
                self.db.update_rows('nets', UPDATE, WHERE={'uuid':task[1]})
                self.db_lock.release()

            elif task[0] == 'clear-all':
                r,c = self.clear_all_flows()
                if r<0:
                    self.logger.error("processing task 'clear-all': %s", c)
                else:
                    self.logger.debug("processing task 'clear-all': OK")
            elif task[0] == 'exit':
                self.logger.debug("exit from openflow_thread")
                self.terminate()
                return 0
            else:
                self.logger.error("unknown task %s", str(task))
                
    def terminate(self):
        pass
        #print self.name, ": exit from openflow_thread"

    def update_of_flows(self, net_id):
        ports=()
        self.db_lock.acquire()
        select_= ('type','admin_state_up', 'vlan', 'provider', 'bind_net','bind_type','uuid')
        result, nets = self.db.get_table(FROM='nets', SELECT=select_, WHERE={'uuid':net_id} )
        #get all the networks binding to this
        if result > 0:
            if nets[0]['bind_net']:
                bind_id = nets[0]['bind_net']
            else:
                bind_id = net_id
            #get our net and all bind_nets
            result, nets = self.db.get_table(FROM='nets', SELECT=select_,
                                                WHERE_OR={'bind_net':bind_id, 'uuid':bind_id} )
            
        self.db_lock.release()
        if result < 0:
            return -1, "DB error getting net: " + nets
        #elif result==0:
            #net has been deleted
        ifaces_nb = 0
        database_flows = []
        for net in nets:
            net_id = net["uuid"]
            if net['admin_state_up'] == 'false':
                net['ports'] = ()
            else:
                self.db_lock.acquire()
                nb_ports, net_ports = self.db.get_table(
                        FROM='ports',
                        SELECT=('switch_port','vlan','uuid','mac','type','model'),
                        WHERE={'net_id':net_id, 'admin_state_up':'true', 'status':'ACTIVE'} )
                self.db_lock.release()
                if nb_ports < 0:
                    #print self.name, ": update_of_flows() ERROR getting ports", ports
                    return -1, "DB error getting ports from net '%s': %s" % (net_id, net_ports)
                
                #add the binding as an external port
                if net['provider'] and net['provider'][:9]=="openflow:":
                    external_port={"type":"external","mac":None}
                    external_port['uuid'] = net_id + ".1" #fake uuid
                    if net['provider'][-5:]==":vlan":
                        external_port["vlan"] = net["vlan"]
                        external_port["switch_port"] = net['provider'][9:-5]
                    else:
                        external_port["vlan"] = None
                        external_port["switch_port"] = net['provider'][9:]
                    net_ports = net_ports + (external_port,)
                    nb_ports += 1
                net['ports'] = net_ports
                ifaces_nb += nb_ports
        
            # Get the name of flows that will be affected by this NET 
            self.db_lock.acquire()
            result, database_net_flows = self.db.get_table(FROM='of_flows', WHERE={'net_id':net_id})
            self.db_lock.release()
            if result < 0:
                #print self.name, ": update_of_flows() ERROR getting flows from database", database_flows
                return -1, "DB error getting flows from net '%s': %s" %(net_id, database_net_flows)
            database_flows += database_net_flows
        # Get the name of flows where net_id==NULL that means net deleted (At DB foreign key: On delete set null)
        self.db_lock.acquire()
        result, database_net_flows = self.db.get_table(FROM='of_flows', WHERE={'net_id':None})
        self.db_lock.release()
        if result < 0:
            #print self.name, ": update_of_flows() ERROR getting flows from database", database_flows
            return -1, "DB error getting flows from net 'null': %s" %(database_net_flows)
        database_flows += database_net_flows

        #Get the existing flows at openflow controller
        result, of_flows = self.OF_connector.get_of_rules() 
        if result < 0:
            #print self.name, ": update_of_flows() ERROR getting flows from controller", of_flows
            return -1, "OF error getting flows: " + of_flows

        if ifaces_nb < 2:
            pass
        elif net['type'] == 'ptp':
            if ifaces_nb > 2:
                #print self.name, 'Error, network '+str(net_id)+' has been defined as ptp but it has '+\
                #                 str(ifaces_nb)+' interfaces.'
                return -1, "'ptp' type network cannot connect %d interfaces, only 2" % ifaces_nb
        elif net['type'] == 'data':
            if ifaces_nb > 2 and self.pmp_with_same_vlan:
                # check all ports are VLAN (tagged) or none
                vlan_tag = None
                for port in ports:
                    if port["type"]=="external":
                        if port["vlan"] != None:
                            if port["vlan"]!=net["vlan"]:
                                text="External port vlan-tag and net vlan-tag must be the same when flag 'of_controller_nets_with_same_vlan' is True"
                                #print self.name, "Error", text
                                return -1, text
                            if vlan_tag == None:
                                vlan_tag=True
                            elif vlan_tag==False:
                                text="Passthrough and external port vlan-tagged can not be connected when flag 'of_controller_nets_with_same_vlan' is True"
                                #print self.name, "Error", text
                                return -1, text
                        else:
                            if vlan_tag == None:
                                vlan_tag=False
                            elif vlan_tag == True:
                                text="SR-IOV and external port not vlan-tagged can not be connected when flag 'of_controller_nets_with_same_vlan' is True"
                                #print self.name, "Error", text
                                return -1, text
                    elif port["model"]=="PF" or port["model"]=="VFnotShared":
                        if vlan_tag == None:
                            vlan_tag=False
                        elif vlan_tag==True:
                            text="Passthrough and SR-IOV ports cannot be connected when flag 'of_controller_nets_with_same_vlan' is True"
                            #print self.name, "Error", text
                            return -1, text
                    elif port["model"] == "VF":
                        if vlan_tag == None:
                            vlan_tag=True
                        elif vlan_tag==False:
                            text="Passthrough and SR-IOV ports cannot be connected when flag 'of_controller_nets_with_same_vlan' is True"
                            #print self.name, "Error", text
                            return -1, text
        else:
            return -1, 'Only ptp and data networks are supported for openflow'
            
        # calculate new flows to be inserted
        result, new_flows = self._compute_net_flows(nets)
        if result < 0:
            return result, new_flows

        #modify database flows format and get the used names
        used_names=[]
        for flow in database_flows:
            try:
                change_db2of(flow)
            except FlowBadFormat as e:
                self.logger.error("Exception FlowBadFormat: '%s', flow: '%s'",str(e), str(flow))
                continue
            used_names.append(flow['name'])
        name_index=0
        #insert at database the new flows, change actions to human text
        for flow in new_flows:
            #1 check if an equal flow is already present
            index = self._check_flow_already_present(flow, database_flows)
            if index>=0:
                database_flows[index]["not delete"]=True
                self.logger.debug("Skipping already present flow %s", str(flow))
                continue
            #2 look for a non used name
            flow_name=flow["net_id"]+"."+str(name_index)
            while flow_name in used_names or flow_name in of_flows:         
                name_index += 1   
                flow_name=flow["net_id"]+"."+str(name_index)
            used_names.append(flow_name)
            flow['name'] = flow_name
            #3 insert at openflow
            result, content = self.OF_connector.new_flow(flow)
            if result < 0:
                #print self.name, ": Error '%s' at flow insertion" % c, flow
                return -1, content
            #4 insert at database
            try:
                change_of2db(flow)
            except FlowBadFormat as e:
                #print self.name, ": Error Exception FlowBadFormat '%s'" % str(e), flow
                return -1, str(e)
            self.db_lock.acquire()
            result, content = self.db.new_row('of_flows', flow)
            self.db_lock.release()
            if result < 0:
                #print self.name, ": Error '%s' at database insertion" % content, flow
                return -1, content

        #delete not needed old flows from openflow and from DDBB, 
        #check that the needed flows at DDBB are present in controller or insert them otherwise
        for flow in database_flows:
            if "not delete" in flow:
                if flow["name"] not in of_flows:
                    #not in controller, insert it
                    result, content = self.OF_connector.new_flow(flow)
                    if result < 0:
                        #print self.name, ": Error '%s' at flow insertion" % c, flow
                        return -1, content
                continue
            #Delete flow
            if flow["name"] in of_flows:
                result, content = self.OF_connector.del_flow(flow['name'])
                if result<0:
                    self.logger.error("cannot delete flow '%s' from OF: %s", flow['name'], content )
                    continue #skip deletion from database
            #delete from database
            self.db_lock.acquire()
            result, content = self.db.delete_row_by_key('of_flows', 'id', flow['id'])
            self.db_lock.release()
            if result<0:
                self.logger.error("cannot delete flow '%s' from DB: %s", flow['name'], content )
        
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
        except requests.exceptions.RequestException as e:
            #print self.name, ": clear_all_flows Exception:", str(e)
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
        
    def _compute_net_flows(self, nets):
        new_flows=[]
        new_broadcast_flows={}
        nb_ports = 0

        # Check switch_port information is right
        self.logger.debug("_compute_net_flows nets: %s", str(nets))
        for net in nets:
            for port in net['ports']:
                nb_ports += 1
                if not self.test and str(port['switch_port']) not in self.OF_connector.pp2ofi:
                    error_text= "switch port name '%s' is not valid for the openflow controller" % str(port['switch_port'])
                    #print self.name, ": ERROR " + error_text
                    return -1, error_text

        for net_src in nets:
            net_id = net_src["uuid"]
            for net_dst in nets:
                vlan_net_in  = None
                vlan_net_out = None
                if net_src == net_dst:
                    #intra net rules    
                    priority = 1000
                elif net_src['bind_net'] == net_dst['uuid']:
                    if net_src.get('bind_type') and net_src['bind_type'][0:5] == "vlan:":
                        vlan_net_out = int(net_src['bind_type'][5:])
                    priority = 1100
                elif net_dst['bind_net'] == net_src['uuid']:
                    if net_dst.get('bind_type') and net_dst['bind_type'][0:5] == "vlan:":
                        vlan_net_in = int(net_dst['bind_type'][5:])
                    priority = 1100
                else:
                    #nets not binding
                    continue
                for src_port in net_src['ports']:
                    vlan_in  = vlan_net_in
                    if vlan_in == None  and src_port['vlan'] != None:
                        vlan_in  = src_port['vlan']
                    elif vlan_in != None  and src_port['vlan'] != None:
                        #TODO this is something that we can not do. It requires a double VLAN check
                        #outer VLAN should be src_port['vlan'] and inner VLAN should be vlan_in
                        continue

                    # BROADCAST:
                    broadcast_key = src_port['uuid'] + "." + str(vlan_in)
                    if broadcast_key in new_broadcast_flows:
                        flow_broadcast = new_broadcast_flows[broadcast_key]
                    else:
                        flow_broadcast = {'priority': priority,
                            'net_id':  net_id,
                            'dst_mac': 'ff:ff:ff:ff:ff:ff',
                            "ingress_port": str(src_port['switch_port']),
                            'actions': [] 
                        }
                        new_broadcast_flows[broadcast_key] = flow_broadcast
                        if vlan_in is not None:
                            flow_broadcast['vlan_id'] = str(vlan_in)

                    for dst_port in net_dst['ports']:
                        vlan_out = vlan_net_out 
                        if vlan_out == None and dst_port['vlan'] != None:
                            vlan_out = dst_port['vlan']
                        elif vlan_out != None and dst_port['vlan'] != None:
                            #TODO this is something that we can not do. It requires a double VLAN set
                            #outer VLAN should be dst_port['vlan'] and inner VLAN should be vlan_out
                            continue
                        #if src_port == dst_port:
                        #    continue
                        if src_port['switch_port'] == dst_port['switch_port'] and vlan_in == vlan_out:
                            continue
                        flow = {
                            "priority": priority,
                            'net_id':  net_id,
                            "ingress_port": str(src_port['switch_port']),
                            'actions': []
                        }
                        if vlan_in is not None:
                            flow['vlan_id'] = str(vlan_in)
                        # allow that one port have no mac
                        if dst_port['mac'] is None or nb_ports==2:  # point to point or nets with 2 elements
                            flow['priority'] = priority-5  # less priority
                        else:
                            flow['dst_mac'] = str(dst_port['mac'])
            
                        if vlan_out == None:
                            if vlan_in != None:
                                flow['actions'].append( ('vlan',None) )
                        else:
                            flow['actions'].append( ('vlan', vlan_out ) )
                        flow['actions'].append( ('out', str(dst_port['switch_port'])) )
            
                        if self._check_flow_already_present(flow, new_flows) >= 0:
                            self.logger.debug("Skipping repeated flow '%s'", str(flow))
                            continue
                        
                        new_flows.append(flow)
                    
                        # BROADCAST:
                        if nb_ports <= 2:  # point to multipoint or nets with more than 2 elements
                            continue
                        out = (vlan_out, str(dst_port['switch_port']))
                        if out not in flow_broadcast['actions']:
                            flow_broadcast['actions'].append( out )

        #BROADCAST
        for flow_broadcast in new_broadcast_flows.values():      
            if len(flow_broadcast['actions'])==0:
                continue #nothing to do, skip
            flow_broadcast['actions'].sort()
            if 'vlan_id' in flow_broadcast:
                previous_vlan = 0  # indicates that a packet contains a vlan, and the vlan
            else:
                previous_vlan = None
            final_actions=[]
            action_number = 0
            for action in flow_broadcast['actions']:
                if action[0] != previous_vlan:
                    final_actions.append( ('vlan', action[0]) )
                    previous_vlan = action[0]
                    if self.pmp_with_same_vlan and action_number:
                        return -1, "Can not interconnect different vlan tags in a network when flag 'of_controller_nets_with_same_vlan' is True."
                    action_number += 1
                final_actions.append( ('out', action[1]) )
            flow_broadcast['actions'] = final_actions

            if self._check_flow_already_present(flow_broadcast, new_flows) >= 0:
                self.logger.debug("Skipping repeated flow '%s'", str(flow_broadcast))
                continue
            
            new_flows.append(flow_broadcast)        
        
        #UNIFY openflow rules with the same input port and vlan and the same output actions
        #These flows differ at the dst_mac; and they are unified by not filtering by dst_mac
        #this can happen if there is only two ports. It is converted to a point to point connection
        flow_dict={} # use as key vlan_id+ingress_port and as value the list of flows matching these values
        for flow in new_flows:
            key = str(flow.get("vlan_id"))+":"+flow["ingress_port"]
            if key in flow_dict:
                flow_dict[key].append(flow)
            else:
                flow_dict[key]=[ flow ]
        new_flows2=[]
        for flow_list in flow_dict.values():
            convert2ptp=False
            if len (flow_list)>=2:
                convert2ptp=True
                for f in flow_list:
                    if f['actions'] != flow_list[0]['actions']:
                        convert2ptp=False
                        break
            if convert2ptp: # add only one unified rule without dst_mac
                self.logger.debug("Convert flow rules to NON mac dst_address " + str(flow_list) )
                flow_list[0].pop('dst_mac')
                flow_list[0]["priority"] -= 5
                new_flows2.append(flow_list[0])
            else:  # add all the rules
                new_flows2 += flow_list
        return 0, new_flows2
        

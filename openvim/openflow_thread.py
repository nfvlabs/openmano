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
import utils.auxiliary_functions as af
import threading
import time
import Queue
import requests
import itertools

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

            print self.name, ": processing task", task[0]
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
        result, content = self.db.get_table(FROM='nets', SELECT=('type','admin_state_up', 'vlan'),
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
                        SELECT=('switch_port','vlan','vlan_changed','uuid','mac','type'),
                        WHERE={'net_id':net_id, 'admin_state_up':'true', 'status':'ACTIVE'} )
                self.db_lock.release()
                if ifaces_nb < 0:
                    print self.name, ": update_of_flows() ERROR getting ports", ports
                    return -1, "ERROR getting ports "+ ports
        
        # Get the name of flows that will be affected by this NET or net_id==NULL that means
        # net deleted (At DB foreign key: On delete set null)
        self.db_lock.acquire()
        result, flows = self.db.get_table(FROM='of_flows', SELECT=('name','id'),WHERE={'net_id':net_id},
                                          WHERE_OR={'net_id':None} )
        self.db_lock.release()
        if result < 0:
            print self.name, ": update_of_flows() ERROR getting flows", flows
            return -1, "ERROR getting flows " + flows
        elif result > 0:
            #delete flows
            for flow in flows:
                #print self.name, ": update_of_flows() Deleting", flow['name']
                r,c= self.OF_connector.del_flow(flow['name'])
                self.db_lock.acquire()
                if r>=0:
                    self.db.delete_row_by_key('of_flows', 'id', flow['id'])
                else:
                    #keep the flow, but put in actions the error
                    self.db.update_rows('of_flows', {'actions':c}, {'id':flow['id']})
                self.db_lock.release()
        
        tagged = None
        if ifaces_nb < 2:
            return 0, 'Success'
        if net['type'] == 'ptp':
            if ifaces_nb > 2:
                print self.name, 'Error, network '+str(net_id)+' has been defined as ptp but it has '+\
                                 str(ifaces_nb)+' interfaces.'
                return -1, 'Error, network '+str(net_id)+' has been defined as ptp but it has '+\
                       str(ifaces_nb)+' interfaces.'
        elif net['type'] == 'data':
            if ifaces_nb > 2 and self.pmp_with_same_vlan:
                # Change vlan in host
                # check all ports are VLAN (tagged) or none
                tagged = ports[0]['vlan']
                if ports[0]['type']=='external' and ports[0]['vlan'] != None and ports[0]['vlan']!=net['vlan']:
                    text='Error external port connected with different vlan net to a point to multipoint net'
                    print self.name, text
                    return -1, text
                for port in ports[1:]:
                    if type(port['vlan']) != type(tagged):
                        text='Error Can not connect vlan with no vlan ports'
                        print self.name, text
                        return -1, text
                    if port['type']=='external':
                        if tagged != None and port['vlan']!=net['vlan']:
                            text='Error external port conected with different vlan net to a point to multipoint net'
                            print text
                            return -1, text
                # change VLAN of ports to net vlan
                if tagged != None :
                    for port in ports:
                        port_vlan = port['vlan_changed'] if port['vlan_changed']!=None else port['vlan']
                        if port_vlan != net['vlan']:
                            result, content = self.change_vlan(port['uuid'], net['vlan'])
                            if result < 0:
                                return result, content
                            port_vlan = net['vlan']
                        port['vlan']=port_vlan
            
        else:
            return -1, 'Only ptp and data networks are supported for openflow'

        # ensure SRIOV ports are in the right VLAN, They can have a different VLAN if previosly
        # it is attached to a pmp VLAN
        if tagged == None:
            for port in ports:
                if port['vlan_changed'] != None and port['vlan'] != port['vlan_changed']:
                    result, content = self.change_vlan(port['uuid'], port['vlan'])
                    if result < 0:
                        return result, content
            
        # launch to openflow
        result, db_of_inserts = self.install_netrules(net_id, ports)
        if result < 0:
            return result, db_of_inserts
        for INSERT in db_of_inserts:
            self.db_lock.acquire()
            result, content = self.db.new_row('of_flows', INSERT)
            self.db_lock.release()
            if result < 0:
                print self.name, ": ports=", ports
                return -1, content
        
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

    def change_vlan(self, uuid, net_vlan):
        if self.test:
            return 0, None
        '''Change vlan in server'''
        self.db_lock.acquire()
        result, content = self.db.get_table(
                FROM='( resources_port as rp join resources_port as rp2 on rp.root_id=rp2.id join numas on '
                     'rp.numa_id=numas.id) join hosts on numas.host_id=hosts.uuid',
                SELECT=('hosts.ip_name', 'hosts.user', 'hosts.password', 'rp.source_name',
                        'rp2.source_name as parent_source_name', 'rp.id'),
                WHERE={'rp.port_id':uuid}
            )
        self.db_lock.release()
        if result < 0:
            print self.name, ": ports", content
            return -1, content
        elif result==0: #
            return -1, "change_vlan() Error, no port get from database"

        row = content[0]
        print self.name, ": change_vlan() ports", row
        if row['source_name']!=row['parent_source_name']:
            cmd = 'sudo ip link set '+row['parent_source_name']+' vf '+row['source_name']+' vlan '+str(net_vlan)
            #print cmd
            r,c = af.get_ssh_connection(row['ip_name'], row['user'], row['password'])
            if not r:
                return -1, c
            r,c = af.run_in_remote_server(c,cmd)
            if not r:
                print self.name, ": change_vlan() error ejecutando:", c
                return -1, c
            #print self.name, ": change_vlan() despues ejecutar"
            self.db_lock.acquire()
            r,c = self.db.update_rows('ports', {'vlan_changed':net_vlan}, {'uuid':uuid})
            self.db_lock.release()
            if r<0:
                print self.name, ": change_vlan() error ejecutando:", c
                print self.name, ": change_vlan() Error updating DB", c
        else:
            print self.name, ": change_vlan()  vlan was not changed since it is a physiscal port"
            return 1, None #Its is a physiscal port
        return 0, None  #vlan was changed
        
    def install_netrules(self, net_id, ports):
        error_text=""
        db_list = []
        nb_rules = len(ports)

        # Insert rules so each point can reach other points using dest mac information
        pairs = itertools.product(ports, repeat=2)
        index = 0
        #rules portA to portB
        for pair in pairs:
            if pair[0]['switch_port'] == pair[1]['switch_port'] and pair[0]['vlan'] == pair[1]['vlan']:
                continue
            flow = {
                "name": net_id+'_'+str(index),
                "priority": "1000",
                "ingress-port": str(pair[0]['switch_port']),
                "active": "true",
                'actions': []
            }
            # allow that one port have no mac
            if pair[1]['mac'] is None or nb_rules==2:  # point to point or nets with 2 elements
                flow['priority'] = "990"  # less priority
            else:
                flow['dst-mac'] = str(pair[1]['mac'])
                
            if pair[0]['vlan'] is not None:
                flow['vlan-id'] = str(pair[0]['vlan'])

            if pair[1]['vlan'] is None:
                if pair[0]['vlan'] is not None:
                    flow['actions'].append('strip-vlan')
            else:
                flow['actions'].append('set-vlan-id')
                flow['actions'].append(str(pair[1]['vlan']))
            flow['actions'].append('output')
            flow['actions'].append(str(pair[1]['switch_port']))

            index += 1
            
            self.OF_connector.new_flow(flow)
            
            INSERT={'name':flow['name'], 'net_id':net_id, 'vlan_id':flow.get('vlan-id',None),
                    'ingress_port':flow('ingress-port'),
                    'priority':flow['priority'], 'actions':flow['actions'], 'dst_mac': flow.get('dst-mac', None)}
            db_list.append(INSERT)
        
        # BROADCAST:
        if nb_rules > 2:  # point to multipoint or nets with more than 2 elements
            for p1 in ports:
                flow = {'priority': '1000',
                    'dst-mac': 'ff:ff:ff:ff:ff:ff',
                    'active': "true",
                    'actions': []
                }

                flow['ingress-port'] = str(p1['switch_port'])
                flow['name'] = net_id+'_'+str(index)
                if p1['vlan'] is not None:
                    flow['vlan-id'] = str(p1['vlan'])
                    last_vlan = 0  # indicates that a packet contains a vlan, and the vlan
                else:
                    last_vlan = None
                
                for p2 in ports:
                    if p1 == p2: continue
                    if last_vlan != p2['vlan']:
                        if p2['vlan'] is not None:
                            flow['actions'].append('set-vlan-id')
                            flow['actions'].append(str(p2['vlan']))
                            last_vlan = p2['vlan']
                        else:
                            flow['actions'].append('strip-vlan')
                            last_vlan = None

                    flow['actions'].append('output')
                    flow['actions'].append(str(p2['switch_port']))

                index += 1

                self.OF_connector.new_flow(flow)
                INSERT={'name':flow['name'], 'net_id':net_id, 'vlan_id':flow.get('vlan-id',None),
                        'ingress_port':str(p1['switch_port']),
                        'priority':flow['priority'], 'actions':flow['actions'],
                        'dst_mac': flow.get('dst-mac', None)}
                db_list.append(INSERT)
            
        return 0, db_list


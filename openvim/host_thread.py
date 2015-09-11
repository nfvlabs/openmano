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
This is thread that interact with the host and the libvirt to manage VM
One thread will be launched per host 
'''
__author__="Pablo Montes, Alfonso Tierno"
__date__ ="$10-jul-2014 12:07:15$"


import json
import yaml
import threading
import time
import Queue
import paramiko
from jsonschema import validate as js_v, exceptions as js_e
import libvirt
from vim_schema import localinfo_schema, hostinfo_schema
#import math
#from logging import Logger
#import utils.auxiliary_functions as af

#TODO: insert a logging system

class host_thread(threading.Thread):
    def __init__(self, name, host, user, db, db_lock, test, image_path, host_id, version, develop_mode, develop_bridge_iface):
        '''Init a thread.
        Arguments: thread_info must be a dictionary with:
            'id' number of thead
            'name' name of thread
            'host' host ip or name to manage
        Return: add items to thread_info
            'lock': lock for shared variables, as task queue
            'queue' : queue of tasks. PUSHed by main thread, and POPed by this thread.
                Contain a Queue of tuples. Each tuple with two items: string of task, and params
        '''
        threading.Thread.__init__(self)
        self.name = name
        self.host = host
        self.user = user
        self.db = db
        self.db_lock = db_lock
        self.test = test
        self.develop_mode = develop_mode
        self.develop_bridge_iface = develop_bridge_iface
        self.image_path = image_path
        self.host_id = host_id
        self.version = version
        
        self.xml_level = 0
        #self.pending ={}
        
        self.server_status = {} #dictionary with pairs server_uuid:server_status 
        self.pending_terminate_server =[] #list  with pairs (time,server_uuid) time to send a terminate for a server being destroyed
        self.next_update_server_status = 0 #time when must be check servers status
        
        self.hostinfo = None 
        
        self.queueLock = threading.Lock()
        self.taskQueue = Queue.Queue(20)
        
    def ssh_connect(self):
        try:
            #Connect SSH
            self.ssh_conn = paramiko.SSHClient()
            self.ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_conn.load_system_host_keys()
            self.ssh_conn.connect(self.host, username=self.user, timeout=10) #, None)
        except paramiko.ssh_exception.SSHException, e:
            text = e.args[0]
            print self.name, ": ssh_connect ssh Exception:", text
        
    def load_localinfo(self):
        if not self.test:
            try:
                #Connect SSH
                self.ssh_connect()
    
                command = 'mkdir -p ' +  self.image_path
                #print self.name, ': command:', command
                (_, stdout, stderr) = self.ssh_conn.exec_command(command)
                content = stderr.read()
                if len(content) > 0:
                    print self.name, ': command:', command, "stderr:", content

                command = 'cat ' +  self.image_path + '/.openvim.yaml'
                #print self.name, ': command:', command
                (_, stdout, stderr) = self.ssh_conn.exec_command(command)
                content = stdout.read()
                if len(content) == 0:
                    print self.name, ': command:', command, "stderr:", stderr.read()
                    raise paramiko.ssh_exception.SSHException("Error empty file ")
                self.localinfo = yaml.load(content)
                js_v(self.localinfo, localinfo_schema)
                self.localinfo_dirty=False
                if 'server_files' not in self.localinfo:
                    self.localinfo['server_files'] = {}
                print self.name, ': localinfo load from host'
                return
    
            except paramiko.ssh_exception.SSHException, e:
                text = e.args[0]
                print self.name, ": load_localinfo ssh Exception:", text
            except libvirt.libvirtError, e:
                text = e.get_error_message()
                print self.name, ": load_localinfo libvirt Exception:", text
            except yaml.YAMLError, exc:
                text = ""
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    text = " at position: (%s:%s)" % (mark.line+1, mark.column+1)
                print self.name, ": load_localinfo yaml format Exception", text
            except js_e.ValidationError, e:
                text = ""
                if len(e.path)>0: text=" at '" + ":".join(map(str, e.path))+"'"
                print self.name, ": load_localinfo format Exception:", text, e.message 
            except Exception, e:
                text = str(e)
                print self.name, ": load_localinfo Exception:", text
        
        #not loaded, insert a default data and force saving by activating dirty flag
        self.localinfo = {'files':{}, 'server_files':{} } 
        #self.localinfo_dirty=True
        self.localinfo_dirty=False

    def load_hostinfo(self):
        if self.test:
            return;
        try:
            #Connect SSH
            self.ssh_connect()


            command = 'cat ' +  self.image_path + '/hostinfo.yaml'
            #print self.name, ': command:', command
            (_, stdout, stderr) = self.ssh_conn.exec_command(command)
            content = stdout.read()
            if len(content) == 0:
                print self.name, ': command:', command, "stderr:", stderr.read()
                raise paramiko.ssh_exception.SSHException("Error empty file ")
            self.hostinfo = yaml.load(content)
            js_v(self.hostinfo, hostinfo_schema)
            print self.name, ': hostlinfo load from host', self.hostinfo
            return

        except paramiko.ssh_exception.SSHException, e:
            text = e.args[0]
            print self.name, ": load_hostinfo ssh Exception:", text
        except libvirt.libvirtError, e:
            text = e.get_error_message()
            print self.name, ": load_hostinfo libvirt Exception:", text
        except yaml.YAMLError, exc:
            text = ""
            if hasattr(exc, 'problem_mark'):
                mark = exc.problem_mark
                text = " at position: (%s:%s)" % (mark.line+1, mark.column+1)
            print self.name, ": load_hostinfo yaml format Exception", text
        except js_e.ValidationError, e:
            text = ""
            if len(e.path)>0: text=" at '" + ":".join(map(str, e.path))+"'"
            print self.name, ": load_hostinfo format Exception:", text, e.message 
        except Exception, e:
            text = str(e)
            print self.name, ": load_hostinfo Exception:", text
        
        #not loaded, insert a default data 
        self.hostinfo = None 
        
    def save_localinfo(self, tries=3):
        if self.test:
            self.localinfo_dirty = False
            return
        
        while tries>=0:
            tries-=1
            
            try:
                command = 'cat > ' +  self.image_path + '/.openvim.yaml'
                print self.name, ': command:', command
                (stdin, _, _) = self.ssh_conn.exec_command(command)
                yaml.safe_dump(self.localinfo, stdin, explicit_start=True, indent=4, default_flow_style=False, tags=False, encoding='utf-8', allow_unicode=True)
                self.localinfo_dirty = False
                break #while tries
    
            except paramiko.ssh_exception.SSHException, e:
                text = e.args[0]
                print self.name, ": save_localinfo ssh Exception:", text
                if "SSH session not active" in text:
                    self.ssh_connect()
            except libvirt.libvirtError, e:
                text = e.get_error_message()
                print self.name, ": save_localinfo libvirt Exception:", text
            except yaml.YAMLError, exc:
                text = ""
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    text = " at position: (%s:%s)" % (mark.line+1, mark.column+1)
                print self.name, ": save_localinfo yaml format Exception", text
            except Exception, e:
                text = str(e)
                print self.name, ": save_localinfo Exception:", text

    def load_servers_from_db(self):
        self.db_lock.acquire()
        r,c = self.db.get_table(SELECT=('uuid','status', 'image_id'), FROM='instances', WHERE={'host_id': self.host_id})
        self.db_lock.release()

        self.server_status = {}
        if r<0:
            print self.name, ": Error getting data from database:", c
            return
        for server in c:
            self.server_status[ server['uuid'] ] = server['status']
            
            #convert from old version to new one
            if 'inc_files' in self.localinfo and server['uuid'] in self.localinfo['inc_files']:
                server_files_dict = {'source file': self.localinfo['inc_files'][ server['uuid'] ] [0],  'file format':'raw' }
                if server_files_dict['source file'][-5:] == 'qcow2':
                    server_files_dict['file format'] = 'qcow2'
                    
                self.localinfo['server_files'][ server['uuid'] ] = { server['image_id'] : server_files_dict }
        if 'inc_files' in self.localinfo:
            del self.localinfo['inc_files']
            self.localinfo_dirty = True
    
    def delete_unused_files(self):
        '''Compares self.localinfo['server_files'] content with real servers running self.server_status obtained from database
        Deletes unused entries at self.loacalinfo and the corresponding local files.
        The only reason for this mismatch is the manual deletion of instances (VM) at database
        ''' 
        if self.test:
            return
        for uuid,images in self.localinfo['server_files'].items():
            if uuid not in self.server_status:
                for localfile in images.values():
                    try:
                        print self.name, ": deleting file '%s' of unused server '%s'" %(localfile['source file'], uuid)
                        self.delete_file(localfile['source file'])
                    except paramiko.ssh_exception.SSHException, e:
                        print self.name, ": Exception deleting file '%s': %s" %(localfile['source file'], str(e))
                del self.localinfo['server_files'][uuid]
                self.localinfo_dirty = True
   
    def insert_task(self, task, *aditional):
        try:
            self.queueLock.acquire()
            task = self.taskQueue.put( (task,) + aditional, timeout=5) 
            self.queueLock.release()
            return 1, None
        except Queue.Full:
            return -1, "timeout inserting a task over host " + self.name

    def run(self):
        while True:
            self.load_localinfo()
            self.load_hostinfo()
            self.load_servers_from_db()
            self.delete_unused_files()
            while True:
                self.queueLock.acquire()
                if not self.taskQueue.empty():
                    task = self.taskQueue.get()
                else:
                    task = None
                self.queueLock.release()
    
                if task is None:
                    now=time.time()
                    if self.localinfo_dirty:
                        self.save_localinfo()
                    elif self.next_update_server_status < now:
                        self.update_servers_status()
                        self.next_update_server_status = now + 5
                    elif len(self.pending_terminate_server)>0 and self.pending_terminate_server[0][0]<now:
                        self.server_forceoff()
                    else:
                        time.sleep(1)
                    continue        
    
                if task[0] == 'instance':
                    print self.name, ": processing task instance", task[1]['action']
                    retry=0
                    while retry <2:
                        retry += 1
                        r=self.action_on_server(task[1], retry==2)
                        if r>=0: 
                            break
                elif task[0] == 'image':
                    pass
                elif task[0] == 'exit':
                    print self.name, ": processing task exit"
                    self.terminate()
                    return 0
                elif task[0] == 'reload':
                    print self.name, ": processing task reload"
                    break
                elif task[0] == 'edit-iface':
                    print self.name, ": processing task edit-iface port=%s, old_net=%s, new_net=%s" % (task[1], task[2], task[3])
                    self.edit_iface(task[1], task[2], task[3])
                    break
                else:
                    print self.name, ": unknown task", task
                
    def server_forceoff(self, wait_until_finished=False):
        while len(self.pending_terminate_server)>0:
            now = time.time()
            if self.pending_terminate_server[0][0]>now:
                if wait_until_finished:
                    time.sleep(1)
                    continue
                else:
                    return
            req={'uuid':self.pending_terminate_server[0][1],
                'action':{'terminate':'force'},
                'status': None
            }
            self.action_on_server(req)
            self.pending_terminate_server.pop(0)
    
    def terminate(self):
        try:
            self.server_forceoff(True)
            if self.localinfo_dirty:
                self.save_localinfo()
            if not self.test:
                self.ssh_conn.close()
        except Exception, e:
            text = str(e)
            print self.name, ": terminate Exception:", text
        print self.name, ": exit from host_thread" 

    def get_local_iface_name(self, generic_name):
        if self.hostinfo != None and "iface_names" in self.hostinfo and generic_name in self.hostinfo["iface_names"]:
            return self.hostinfo["iface_names"][generic_name]
        return generic_name
        
    def create_xml_server(self, server, dev_list, server_metadata={}):
        """Function that implements the generation of the VM XML definition.
        Additional devices are in dev_list list
        The main disk is upon dev_list[0]"""
        
    #get if operating system is Windows        
        windows_os = False
        os_type = server_metadata.get('os_type', None)
        if os_type == None and 'metadata' in dev_list[0]:
            os_type = dev_list[0]['metadata'].get('os_type', None)
        if os_type != None and os_type.lower() == "windows":
            windows_os = True
    #get type of hard disk bus  
        bus_ide = True if windows_os else False   
        bus = server_metadata.get('bus', None)
        if bus == None and 'metadata' in dev_list[0]:
            bus = dev_list[0]['metadata'].get('bus', None)
        if bus != None:
            bus_ide = True if bus=='ide' else False
            
        self.xml_level = 0

        text = "<domain type='kvm'>"
    #name
        name = server.get('name','') + "_" + server['uuid']
        name = name[:58]  #qemu impose a length  limit of 59 chars or not start. Using 58
        text += self.inc_tab() + "<name>" + name+ "</name>"
    #uuid
        text += self.tab() + "<uuid>" + server['uuid'] + "</uuid>" 
        
        numa={}
        if 'extended' in server and server['extended']!=None and 'numas' in server['extended']:
            numa = server['extended']['numas'][0]
    #memory
        use_huge = False
        memory = int(numa.get('memory',0))*1024*1024 #in KiB
        if memory==0:
            memory = int(server['ram'])*1024;
        else:
            if not self.develop_mode:
                use_huge = True
        if memory==0:
            return -1, 'No memory assigned to instance'
        memory = str(memory)
        text += self.tab() + "<memory unit='KiB'>" +memory+"</memory>" 
        text += self.tab() + "<currentMemory unit='KiB'>" +memory+ "</currentMemory>"
        if use_huge:
            text += self.tab()+'<memoryBacking>'+ \
                self.inc_tab() + '<hugepages/>'+ \
                self.dec_tab()+ '</memoryBacking>'

    #cpu
        use_cpu_pinning=False
        vcpus = int(server.get("vcpus",0))
        cpu_pinning = []
        if 'cores-source' in numa:
            use_cpu_pinning=True
            for index in range(0, len(numa['cores-source'])):
                cpu_pinning.append( [ numa['cores-id'][index], numa['cores-source'][index] ] )
                vcpus += 1
        if 'threads-source' in numa:
            use_cpu_pinning=True
            for index in range(0, len(numa['threads-source'])):
                cpu_pinning.append( [ numa['threads-id'][index], numa['threads-source'][index] ] )
                vcpus += 1
        if 'paired-threads-source' in numa:
            use_cpu_pinning=True
            for index in range(0, len(numa['paired-threads-source'])):
                cpu_pinning.append( [numa['paired-threads-id'][index][0], numa['paired-threads-source'][index][0] ] )
                cpu_pinning.append( [numa['paired-threads-id'][index][1], numa['paired-threads-source'][index][1] ] )
                vcpus += 2
        
        if use_cpu_pinning and not self.develop_mode:
            text += self.tab()+"<vcpu placement='static'>" +str(len(cpu_pinning)) +"</vcpu>" + \
                self.tab()+'<cputune>'
            self.xml_level += 1
            for i in range(0, len(cpu_pinning)):
                text += self.tab() + "<vcpupin vcpu='" +str(cpu_pinning[i][0])+ "' cpuset='" +str(cpu_pinning[i][1]) +"'/>"
            text += self.dec_tab()+'</cputune>'+ \
                self.tab() + '<numatune>' +\
                self.inc_tab() + "<memory mode='strict' nodeset='" +str(numa['source'])+ "'/>" +\
                self.dec_tab() + '</numatune>'
        else:
            if vcpus==0:
                return -1, "Instance without number of cpus"
            text += self.tab()+"<vcpu>" + str(vcpus)  + "</vcpu>"

    #boot
        boot_cdrom = False
        for dev in dev_list:
            if dev['type']=='cdrom' :
                boot_cdrom = True
                break
        text += self.tab()+ '<os>' + \
            self.inc_tab() + "<type arch='x86_64' machine='pc'>hvm</type>"
        if boot_cdrom:
            text +=  self.tab() + "<boot dev='cdrom'/>" 
        text +=  self.tab() + "<boot dev='hd'/>" + \
            self.dec_tab()+'</os>'
    #features
        text += self.tab()+'<features>'+\
            self.inc_tab()+'<acpi/>' +\
            self.tab()+'<apic/>' +\
            self.tab()+'<pae/>'+ \
            self.dec_tab() +'</features>'
        if windows_os:
            text += self.tab() + "<cpu mode='host-model'> <topology sockets='1' cores='%d' threads='1' /> </cpu>"% vcpus
        else:
            text += self.tab() + "<cpu mode='host-model'></cpu>"
        text += self.tab() + "<clock offset='utc'/>" +\
            self.tab() + "<on_poweroff>preserve</on_poweroff>" + \
            self.tab() + "<on_reboot>restart</on_reboot>" + \
            self.tab() + "<on_crash>restart</on_crash>"
        text += self.tab() + "<devices>" + \
            self.inc_tab() + "<emulator>/usr/libexec/qemu-kvm</emulator>" + \
            self.tab() + "<serial type='pty'>" +\
            self.inc_tab() + "<target port='0'/>" + \
            self.dec_tab() + "</serial>" +\
            self.tab() + "<console type='pty'>" + \
            self.inc_tab()+ "<target type='serial' port='0'/>" + \
            self.dec_tab()+'</console>'
        if windows_os:
            text += self.tab() + "<controller type='usb' index='0'/>" + \
                self.tab() + "<controller type='ide' index='0'/>" + \
                self.tab() + "<input type='mouse' bus='ps2'/>" + \
                self.tab() + "<sound model='ich6'/>" + \
                self.tab() + "<video>" + \
                self.inc_tab() + "<model type='cirrus' vram='9216' heads='1'/>" + \
                self.dec_tab() + "</video>" + \
                self.tab() + "<memballoon model='virtio'/>" + \
                self.tab() + "<input type='tablet' bus='usb'/>" #TODO revisar

#>             self.tab()+'<alias name=\'hostdev0\'/>\n' +\
#>             self.dec_tab()+'</hostdev>\n' +\
#>             self.tab()+'<input type=\'tablet\' bus=\'usb\'/>\n'
        if windows_os:
            text += self.tab() + "<graphics type='vnc' port='-1' autoport='yes'/>"
        else:
            #If image contains 'GRAPH' include graphics
            #if 'GRAPH' in image:
            text += self.tab() + "<graphics type='vnc' port='-1' autoport='yes' listen='127.0.0.1'>" +\
                self.inc_tab() + "<listen type='address' address='127.0.0.1'/>" +\
                self.dec_tab() + "</graphics>"

        vd_index = 'a'
        for dev in dev_list:
            bus_ide_dev = bus_ide
            if dev['type']=='cdrom' or dev['type']=='disk':
                if dev['type']=='cdrom':
                    bus_ide_dev = True
                text += self.tab() + "<disk type='file' device='"+dev['type']+"'>"
                if 'file format' in dev:
                    text += self.inc_tab() + "<driver name='qemu' type='"  +dev['file format']+ "' cache='none'/>"
                if 'source file' in dev:
                    text += self.tab() + "<source file='" +dev['source file']+ "'/>"
                #elif v['type'] == 'block':
                #    text += self.tab() + "<source dev='" + v['source'] + "'/>"
                #else:
                #    return -1, 'Unknown disk type ' + v['type']
                vpci = dev.get('vpci',None)
                if vpci == None:
                    vpci = dev['metadata'].get('vpci',None)
                text += self.pci2xml(vpci)
               
                if bus_ide_dev:
                    text += self.tab() + "<target dev='hd" +vd_index+ "' bus='ide'/>"   #TODO allows several type of disks
                else:
                    text += self.tab() + "<target dev='vd" +vd_index+ "' bus='virtio'/>" 
                text += self.dec_tab() + '</disk>'
                vd_index = chr(ord(vd_index)+1)
            elif dev['type']=='xml':
                dev_text = dev['xml']
                if 'vpci' in dev:
                    dev_text = dev_text.replace('__vpci__', dev['vpci'])
                if 'source file' in dev:
                    dev_text = dev_text.replace('__file__', dev['source file'])
                if 'file format' in dev:
                    dev_text = dev_text.replace('__format__', dev['source file'])
                if '__dev__' in dev_text:
                    dev_text = dev_text.replace('__dev__', vd_index)
                    vd_index = chr(ord(vd_index)+1)
                text += dev_text
            else:
                return -1, 'Unknown device type ' + dev['type']

        net_nb=0
        bridge_interfaces = server.get('networks', [])
        for v in bridge_interfaces:
            #Get the brifge name
            self.db_lock.acquire()
            result, content = self.db.get_table(FROM='nets', SELECT=('bind',),WHERE={'uuid':v['net_id']} )
            self.db_lock.release()
            if result <= 0:
                print "create_xml_server ERROR getting nets",result, content
                return -1, content
            #ALF: Allow by the moment the 'default' bridge net because is confortable for provide internet to VM
            #I know it is not secure    
            #for v in sorted(desc['network interfaces'].itervalues()):
            model = v.get("model", None)
            if content[0]['bind']=='default':
                text += self.tab() + "<interface type='network'>" + \
                    self.inc_tab() + "<source network='" +content[0]['bind']+ "'/>"
            elif content[0]['bind'][0:7]=='macvtap':
                text += self.tab()+"<interface type='direct'>" + \
                    self.inc_tab() + "<source dev='" + self.get_local_iface_name(content[0]['bind'][8:]) + "' mode='bridge'/>" + \
                    self.tab() + "<target dev='macvtap0'/>"
                if windows_os:
                    text += self.tab() + "<alias name='net" + str(net_nb) + "'/>"
                elif model==None:
                    model = "virtio"
            elif content[0]['bind'][0:6]=='bridge':
                text += self.tab() + "<interface type='bridge'>" +  \
                    self.inc_tab()+"<source bridge='" +self.get_local_iface_name(content[0]['bind'][7:])+ "'/>"
                if windows_os:
                    text += self.tab() + "<target dev='vnet" + str(net_nb)+ "'/>" +\
                        self.tab() + "<alias name='net" + str(net_nb)+ "'/>"
                elif model==None:
                    model = "virtio"
            else:
                return -1, 'Unknown Bridge net bind ' + content[0]['bind']
            if model!=None:
                text += self.tab() + "<model type='" +model+ "'/>"
            if v.get('mac_address', None) != None:
                text+= self.tab() +"<mac address='" +v['mac_address']+ "'/>"
            text += self.pci2xml(v.get('vpci',None))
            text += self.dec_tab()+'</interface>'
            
            net_nb += 1

        interfaces = numa.get('interfaces', [])

        net_nb=0
        for v in interfaces:
            if self.develop_mode: #map these interfaces to bridges
                text += self.tab() + "<interface type='bridge'>" +  \
                    self.inc_tab()+"<source bridge='" +self.develop_bridge_iface+ "'/>"
                if windows_os:
                    text += self.tab() + "<target dev='vnet" + str(net_nb)+ "'/>" +\
                        self.tab() + "<alias name='net" + str(net_nb)+ "'/>"
                else:
                    text += self.tab() + "<model type='e1000'/>" #e1000 is more probable to be supported than 'virtio'
                if v.get('mac_address', None) != None:
                    text+= self.tab() +"<mac address='" +v['mac_address']+ "'/>"
                text += self.pci2xml(v.get('vpci',None))
                text += self.dec_tab()+'</interface>'
                continue
                
            if v['dedicated'] == 'yes':  #passthrought
                text += self.tab() + "<hostdev mode='subsystem' type='pci' managed='yes'>" + \
                    self.inc_tab() + "<source>"
                self.inc_tab()
                text += self.pci2xml(v['source'])
                text += self.dec_tab()+'</source>'
                text += self.pci2xml(v.get('vpci',None))
                if windows_os:
                    text += self.tab() + "<alias name='hostdev" + str(net_nb) + "'/>"
                text += self.dec_tab()+'</hostdev>'
                net_nb += 1
            else:        #sriov_interfaces
                #skip not connected interfaces
                if v.get("net_id") == None:
                    continue
                text += self.tab() + "<interface type='hostdev' managed='yes'>" + \
                    self.inc_tab()
                if v.get('mac_address', None) != None:
                    text+= "<mac address='" +v['mac_address']+ "'/>"
                    text+= self.tab()+'<source>'
                self.inc_tab()
                text += self.pci2xml(v['source'])
                text += self.dec_tab()+'</source>'
                if v.get('vlan',None) != None:
                    text += self.tab() + "<vlan>   <tag id='" + str(v['vlan']) + "'/>   </vlan>"
                text += self.pci2xml(v.get('vpci',None))
                if windows_os:
                    text += self.tab() + "<alias name='hostdev" + str(net_nb) + "'/>"
                text += self.dec_tab()+'</interface>'

            
        text += self.dec_tab()+'</devices>'+\
        self.dec_tab()+'</domain>'
        return 0, text
    
    def pci2xml(self, pci):
        '''from a pci format text XXXX:XX:XX.X generates the xml content of <address>
        alows an empty pci text'''
        if pci is None:
            return ""
        first_part = pci.split(':')
        second_part = first_part[2].split('.')
        return self.tab() + "<address type='pci' domain='0x" + first_part[0] + \
                    "' bus='0x" + first_part[1] + "' slot='0x" + second_part[0] + \
                    "' function='0x" + second_part[1] + "'/>" 
    
    def tab(self):
        """Return indentation according to xml_level"""
        return "\n" + ('  '*self.xml_level)
    
    def inc_tab(self):
        """Increment and return indentation according to xml_level"""
        self.xml_level += 1
        return self.tab()
    
    def dec_tab(self):
        """Decrement and return indentation according to xml_level"""
        self.xml_level -= 1
        return self.tab()
    
    def get_file_info(self, path):
        command = 'ls -l --time-style=+%Y-%m-%dT%H:%M:%S ' + path
        print self.name, ': command:', command
        (_, stdout, _) = self.ssh_conn.exec_command(command)
        content = stdout.read()
        if len(content) == 0:
            return None # file does not exist
        else:
            return content.split(" ") #(permission, 1, owner, group, size, date, file)

    def qemu_get_info(self, path):
        command = 'qemu-img info ' + path
        print self.name, ': command:', command
        (_, stdout, stderr) = self.ssh_conn.exec_command(command)
        content = stdout.read()
        if len(content) == 0:
            error = stderr.read()
            print self.name, ": get_qemu_info error ", error
            raise paramiko.ssh_exception.SSHException("Error getting qemu_info: " + error)
        else:
            try: 
                return yaml.load(content)
            except yaml.YAMLError, exc:
                text = ""
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    text = " at position: (%s:%s)" % (mark.line+1, mark.column+1)
                print self.name, ": get_qemu_info yaml format Exception", text
                raise paramiko.ssh_exception.SSHException("Error getting qemu_info yaml format" + text)

    def qemu_change_backing(self, inc_file, new_backing_file):
        command = 'qemu-img rebase -u -b ' + new_backing_file + ' ' + inc_file 
        print self.name, ': command:', command
        (_, _, stderr) = self.ssh_conn.exec_command(command)
        content = stderr.read()
        if len(content) == 0:
            return 0
        else:
            print self.name, ": qemu_change_backing error: ", content
            return -1
    
    def get_notused_filename(self, proposed_name, suffix=''):
        extension = proposed_name.rfind(".")
        if extension < 0:
            extension = len(proposed_name)
        if suffix != None:
            target_name = proposed_name[:extension] + suffix + proposed_name[extension:]
        info = self.get_file_info(target_name)
        if info is None:
            return target_name
        
        index=0
        while info is not None:
            target_name = proposed_name[:extension] + suffix +  "-" + str(index) + proposed_name[extension:]
            index+=1
            info = self.get_file_info(target_name) 
        return target_name
    
    def delete_file(self, file_name):
        command = 'rm -f '+file_name
        print self.name, ': command:', command
        (_, _, stderr) = self.ssh_conn.exec_command(command)
        error_msg = stderr.read()
        if len(error_msg) > 0:
            raise paramiko.ssh_exception.SSHException("Error deleting file: " + error_msg)

    def copy_file(self, source, destination, perserve_time=True):
        command = 'cp --no-preserve=mode '
        if perserve_time: command += '--preserve=timestamps '
        command +=  source + ' '  + destination
        print self.name, ': command:', command
        (_, _, stderr) = self.ssh_conn.exec_command(command)
        error_msg = stderr.read()
        if len(error_msg) > 0:
            raise paramiko.ssh_exception.SSHException("Error copying image to local host: " + error_msg)

    def copy_remote_file(self, remote_file, use_incremental):
        remote_file_info = self.get_file_info( remote_file )
        #Connect SSH
        local_file = None
        if use_incremental and remote_file in self.localinfo['files']:
            local_file = self.localinfo['files'][remote_file]
            local_file_info =  self.get_file_info(local_file)
            #print "ALF to delete local_file_info:", local_file_info, "local_file:", local_file
            if local_file_info == None:
                local_file = None
            elif local_file_info[4]!=remote_file_info[4] or local_file_info[5]!=remote_file_info[5]:
                #local copy of file not valid because date or size are different. DELETE local file
                self.delete_file(local_file)
                del self.localinfo['files'][remote_file]
                local_file = None

        if local_file == None:
            img_name= remote_file.split('/') [-1]
            img_local = self.image_path + '/' + img_name
            local_file = self.get_notused_filename(img_local)
            self.copy_file(remote_file, local_file, use_incremental)

            if use_incremental:
                self.localinfo['files'][remote_file] = local_file
        
        qemu_info = self.qemu_get_info(local_file)
        if 'backing file' in qemu_info:
            new_backing_file = self.copy_remote_file(qemu_info['backing file'], True) [0]
            self.qemu_change_backing(local_file, new_backing_file)
        return local_file, qemu_info
            
    def launch_server(self, conn, server, rebuild=False, domain=None):
        if self.test:
            return 0, 'Success'

        server_id = server['uuid']
        paused = server.get('paused','no')
        try:
            if domain!=None and rebuild==False:
                domain.resume()
                #self.server_status[server_id] = 'ACTIVE'
                return 0, 'Success'

            self.db_lock.acquire()
            result, server_data = self.db.get_instance(server_id)
            self.db_lock.release()
            if result <= 0:
                print self.name, ": launch_server ERROR getting server from DB",result, server_data
                return result, server_data
    
        #0: get image metadata
            server_metadata = server.get('metadata', {})
            use_incremental = True
             
            if "use_incremental" in server_metadata and server_metadata["use_incremental"] == "no":
                use_incremental = False

            server_host_files = self.localinfo['server_files'].get( server['uuid'], {})
            if rebuild:
                #delete previous incremental files
                for file_ in server_host_files.values():
                    self.delete_file(file_['source file'] )
                server_host_files={}
    
        #1: obtain aditional devices (disks)
            #Put as first device the main disk
            devices = [  {"type":"disk", "image_id":server['image_id'], "vpci":server_metadata.get('vpci', None) } ] 
            if 'extended' in server_data and server_data['extended']!=None and "devices" in server_data['extended']:
                devices += server_data['extended']['devices']

            for dev in devices:
                if dev['image_id'] == None:
                    continue
                
                self.db_lock.acquire()
                result, content = self.db.get_table(FROM='images', SELECT=('path','metadata'),WHERE={'uuid':dev['image_id']} )
                self.db_lock.release()
                if result <= 0:
                    error_text = "ERROR", result, content, "when getting image", dev['image_id']
                    print self.name, ": launch_server", error_text 
                    return -1, error_text
                if content[0]['metadata'] is not None:
                    dev['metadata'] = json.loads(content[0]['metadata'])
                else:
                    dev['metadata'] = {}
                
                if dev['image_id'] in server_host_files:
                    dev['source file'] = server_host_files[ dev['image_id'] ] ['source file'] #local path
                    dev['file format'] = server_host_files[ dev['image_id'] ] ['file format'] # raw or qcow2
                    continue
                
            #2: copy image to host
                remote_file = content[0]['path']
                use_incremental_image = use_incremental
                if use_incremental_image and "use_incremental" in dev['metadata'] and dev['metadata']["use_incremental"] == "no":
                    use_incremental_image = False
                local_file, qemu_info = self.copy_remote_file(remote_file, use_incremental_image)
                
                #create incremental image
                if use_incremental_image:
                    local_file_inc = self.get_notused_filename(local_file, '.inc')
                    command = 'qemu-img create -f qcow2 '+local_file_inc+ ' -o backing_file='+ local_file
                    print 'command:', command
                    (_, _, stderr) = self.ssh_conn.exec_command(command)
                    error_msg = stderr.read()
                    if len(error_msg) > 0:
                        raise paramiko.ssh_exception.SSHException("Error creating incremental file: " + error_msg)
                    local_file = local_file_inc
                    qemu_info = {'file format':'qcow2'}
                
                server_host_files[ dev['image_id'] ] = {'source file': local_file, 'file format': qemu_info['file format']}

                dev['source file'] = local_file 
                dev['file format'] = qemu_info['file format']

            self.localinfo['server_files'][ server['uuid'] ] = server_host_files
            self.localinfo_dirty = True

        #3 Create XML
            result, xml = self.create_xml_server(server_data, devices, server_metadata)  #local_file
            if result <0:
                print self.name, ": create xml server error:", xml
                return -2, xml
            print self.name, ": create xml:", xml
            atribute = libvirt.VIR_DOMAIN_START_PAUSED if paused == "yes" else 0
        #4 Start the domain
            if not rebuild: #ensures that any pending destroying server is done
                self.server_forceoff(True)
            #print self.name, ": launching instance" #, xml
            conn.createXML(xml, atribute)
            #self.server_status[server_id] = 'PAUSED' if paused == "yes" else 'ACTIVE'

            return 0, 'Success'

        except paramiko.ssh_exception.SSHException, e:
            text = e.args[0]
            print self.name, ": launch_server(%s) ssh Exception: %s" %(server_id, text)
            if "SSH session not active" in text:
                self.ssh_connect()
        except libvirt.libvirtError, e:
            text = e.get_error_message()
            print self.name, ": launch_server(%s) libvirt Exception:"  %(server_id, text)
        except Exception, e:
            text = str(e)
            print self.name, ": launch_server(%s) Exception:"  %(server_id, text)
        return -1, text
    
    def update_servers_status(self):
                            # # virDomainState
                            # VIR_DOMAIN_NOSTATE = 0
                            # VIR_DOMAIN_RUNNING = 1
                            # VIR_DOMAIN_BLOCKED = 2
                            # VIR_DOMAIN_PAUSED = 3
                            # VIR_DOMAIN_SHUTDOWN = 4
                            # VIR_DOMAIN_SHUTOFF = 5
                            # VIR_DOMAIN_CRASHED = 6
                            # VIR_DOMAIN_PMSUSPENDED = 7   #TODO suspended
    
        if self.test or len(self.server_status)==0:
            return            
        
        try:
            conn = libvirt.open("qemu+ssh://"+self.user+"@"+self.host+"/system")
            domains=  conn.listAllDomains() 
            domain_dict={}
            for domain in domains:
                uuid = domain.UUIDString() ;
                libvirt_status = domain.state()
                #print libvirt_status
                if libvirt_status[0] == libvirt.VIR_DOMAIN_RUNNING or libvirt_status[0] == libvirt.VIR_DOMAIN_SHUTDOWN:
                    new_status = "ACTIVE"
                elif libvirt_status[0] == libvirt.VIR_DOMAIN_PAUSED:
                    new_status = "PAUSED"
                elif libvirt_status[0] == libvirt.VIR_DOMAIN_SHUTOFF:
                    new_status = "INACTIVE"
                elif libvirt_status[0] == libvirt.VIR_DOMAIN_CRASHED:
                    new_status = "ERROR"
                else:
                    new_status = None
                domain_dict[uuid] = new_status
            conn.close
        except libvirt.libvirtError, e:
            print self.name, ": get_state() Exception '", e.get_error_message()
            return

        for server_id, current_status in self.server_status.iteritems():
            new_status = None
            if server_id in domain_dict:
                new_status = domain_dict[server_id]
            else:
                new_status = "INACTIVE"
                            
            if new_status == None or new_status == current_status:
                continue
            if new_status == 'INACTIVE' and current_status == 'ERROR':
                continue #keep ERROR status, because obviously this machine is not running
            #change status
            print self.name, ": server ", server_id, "status change from ", current_status, "to", new_status
            STATUS={'progress':100, 'status':new_status}
            if new_status == 'ERROR':
                STATUS['last_error'] = 'machine has crashed'
            self.db_lock.acquire()
            r,_ = self.db.update_rows('instances', STATUS, {'uuid':server_id}, log=False)
            self.db_lock.release()
            if r>=0:
                self.server_status[server_id] = new_status
                        
    def action_on_server(self, req, last_retry=True):
        '''Perform an action on a req
        Attributes:
            req: dictionary that contain:
                server properties: 'uuid','name','tenant_id','status'
                action: 'action'
                host properties: 'user', 'ip_name'
        return (error, text)  
             0: No error. VM is updated to new state,  
            -1: Invalid action, as trying to pause a PAUSED VM
            -2: Error accessing host
            -3: VM nor present
            -4: Error at DB access
            -5: Error while trying to perform action. VM is updated to ERROR
        '''
        server_id = req['uuid']
            
        conn = None
        new_status = None
        old_status = req['status']
        last_error = None
        
        if self.test:
            if 'terminate' in req['action']:    new_status = 'deleted'
            elif 'shutoff' in req['action'] and req['status']!='ERROR':    new_status = 'INACTIVE'
            elif 'shutdown' in req['action'] and req['status']!='ERROR':    new_status = 'INACTIVE'
            elif 'forceOff' in req['action'] and req['status']!='ERROR':    new_status = 'INACTIVE'
            elif 'start' in req['action']  and req['status']!='ERROR':      new_status = 'ACTIVE'
            elif 'resume' in req['action'] and req['status']!='ERROR' and req['status']!='INACTIVE' :     new_status = 'ACTIVE'
            elif 'pause' in req['action']  and req['status']!='ERROR':      new_status = 'PAUSED'
            elif 'reboot' in req['action'] and req['status']!='ERROR':     new_status = 'ACTIVE'
            elif 'rebuild' in req['action']:     new_status = 'ACTIVE'
            elif 'createImage' in req['action']:     pass
        else:
            try:
                conn = libvirt.open("qemu+ssh://"+self.user+"@"+self.host+"/system")
                try:
                    dom = conn.lookupByUUIDString(server_id)
                except libvirt.libvirtError, e:
                    text = e.get_error_message()
                    if 'LookupByUUIDString' in text or 'Domain not found' in text or 'No existe un dominio coincidente' in text:
                        dom = None
                    else:
                        print self.name, ": action_on_server(",server_id,") libvirt exception:", text 
                        raise e
                
                if 'forceOff' in req['action']:
                    if dom == None:
                        print self.name, ": action_on_server(",server_id,") domain not running" 
                    else:
                        try:
                            print self.name, ": sending DESTROY to server", server_id 
                            dom.destroy()
                        except Exception, e:
                            if "domain is not running" not in e.get_error_message():
                                print self.name, ": action_on_server(",server_id,") Exception while sending force off:", e.get_error_message()
                                last_error =  'action_on_server Exception while destroy: ' + e.get_error_message()
                                new_status = 'ERROR'
                
                elif 'terminate' in req['action']:
                    if dom == None:
                        print self.name, ": action_on_server(",server_id,") domain not running" 
                        new_status = 'deleted'
                    else:
                        try:
                            if req['action']['terminate'] == 'force':
                                print self.name, ": sending DESTROY to server", server_id 
                                dom.destroy()
                                new_status = 'deleted'
                            else:
                                print self.name, ": sending SHUTDOWN to server", server_id 
                                dom.shutdown()
                                self.pending_terminate_server.append( (time.time()+10,server_id) )
                        except Exception, e:
                            print self.name, ": action_on_server(",server_id,") Exception while destroy:", e.get_error_message() 
                            last_error =  'action_on_server Exception while destroy: ' + e.get_error_message()
                            new_status = 'ERROR'
                            if "domain is not running" in e.get_error_message():
                                try:
                                    dom.undefine()
                                    new_status = 'deleted'
                                except Exception:
                                    print self.name, ": action_on_server(",server_id,") Exception while undefine:", e.get_error_message() 
                                    last_error =  'action_on_server Exception2 while undefine:', e.get_error_message()
                            #Exception: 'virDomainDetachDevice() failed'
                    if new_status=='deleted':
                        if server_id in self.server_status:
                            del self.server_status[server_id]
                        if req['uuid'] in self.localinfo['server_files']:
                            for file_ in self.localinfo['server_files'][ req['uuid'] ].values():
                                try:
                                    self.delete_file(file_['source file'])
                                except Exception:
                                    pass
                            del self.localinfo['server_files'][ req['uuid'] ]
                            self.localinfo_dirty = True

                elif 'shutoff' in req['action'] or 'shutdown' in req['action']:
                    try:
                        if dom == None:
                            print self.name, ": action_on_server(",server_id,") domain not running"
                        else: 
                            dom.shutdown()
#                        new_status = 'INACTIVE'
                        #TODO: check status for changing at database
                    except Exception, e:
                        new_status = 'ERROR'
                        print self.name, ": action_on_server(",server_id,") Exception while shutdown:", e.get_error_message() 
                        last_error =  'action_on_server Exception while shutdown: ' + e.get_error_message()
    
                elif 'rebuild' in req['action']:
                    if dom != None:
                        dom.destroy()
                    r = self.launch_server(conn, req, True, None)
                    if r[0] <0:
                        new_status = 'ERROR'
                        last_error = r[1]
                    else:
                        new_status = 'ACTIVE'
                elif 'start' in req['action']:
                    #La instancia está sólo en la base de datos pero no en la libvirt. es necesario crearla
                    rebuild = True if req['action']['start']=='rebuild'  else False
                    r = self.launch_server(conn, req, rebuild, dom)
                    if r[0] <0:
                        new_status = 'ERROR'
                        last_error = r[1]
                    else:
                        new_status = 'ACTIVE'
                
                elif 'resume' in req['action']:
                    try:
                        if dom == None:
                            pass
                        else:
                            dom.resume()
#                            new_status = 'ACTIVE'
                    except Exception, e:
                        print self.name, ": action_on_server(",server_id,") Exception while resume:", e.get_error_message() 
                    
                elif 'pause' in req['action']:
                    try: 
                        if dom == None:
                            pass
                        else:
                            dom.suspend()
#                            new_status = 'PAUSED'
                    except Exception, e:
                        print self.name, ": action_on_server(",server_id,") Exception while pause:", e.get_error_message() 
    
                elif 'reboot' in req['action']:
                    try: 
                        if dom == None:
                            pass
                        else:
                            dom.reboot()
                        print self.name, ": action_on_server(",server_id,") reboot:" 
                        #new_status = 'ACTIVE'
                    except Exception, e:
                        print self.name, ": action_on_server(",server_id,") Exception while reboot:", e.get_error_message() 
                elif 'createImage' in req['action']:
                    self.create_image(dom, req)
                        
        
                conn.close()    
            except libvirt.libvirtError, e:
                if conn is not None: conn.close
                text = e.get_error_message()
                new_status = "ERROR"
                last_error = text
                print self.name, ": action_on_server(",server_id,") Exception '", text
                if 'LookupByUUIDString' in text or 'Domain not found' in text or 'No existe un dominio coincidente' in text:
                    print self.name, ": action_on_server(",server_id,") Exception removed from host"
        #end of if self.test
        if new_status ==  None:
            return 1

        print self.name, ": action_on_server(",server_id,") new status", new_status, last_error
        UPDATE = {'progress':100, 'status':new_status}
        
        if new_status=='ERROR':
            if not last_retry:  #if there will be another retry do not update database 
                return -1 
            elif 'terminate' in req['action']:
                #PUT a log in the database
                print self.name, ": PANIC deleting server", server_id, last_error
                self.db_lock.acquire()
                self.db.new_row('logs', 
                            {'uuid':server_id, 'tenant_id':req['tenant_id'], 'related':'instances','level':'panic',
                             'description':'PANIC deleting server from host '+self.name+': '+last_error}
                        )
                self.db_lock.release()
                if server_id in self.server_status:
                    del self.server_status[server_id]
                return -1
            else:
                UPDATE['last_error'] = last_error
        if new_status != 'deleted' and (new_status != old_status or new_status == 'ERROR') :
            self.db_lock.acquire()
            self.db.update_rows('instances', UPDATE, {'uuid':server_id}, log=True)
            self.server_status[server_id] = new_status
            self.db_lock.release()
        if new_status == 'ERROR':
            return -1
        return 1 
        
    def create_image(self,dom, req):
        for retry in (0,1):
            try:
                server_id = req['uuid']
                createImage=req['action']['createImage']
                file_orig = self.localinfo['server_files'][server_id] [ createImage['source']['image_id'] ] ['source file']
                if 'path' in req['action']['createImage']:
                    file_dst = req['action']['createImage']['path']
                else:
                    img_name= createImage['source']['path']
                    index=img_name.rfind('/')
                    file_dst = self.get_notused_filename(img_name[:index+1] + createImage['name'] + '.qcow2')
                      
                self.copy_file(file_orig, file_dst)
                qemu_info = self.qemu_get_info(file_orig)
                if 'backing file' in qemu_info:
                    for k,v in self.localinfo['files'].items():
                        if v==qemu_info['backing file']:
                            self.qemu_change_backing(file_dst, k)
                            break
                image_status='ACTIVE'
            except paramiko.ssh_exception.SSHException, e:
                image_status='ERROR'
                error_text = e.args[0]
                print self.name, "': create_image(",server_id,") ssh Exception:", error_text
                if "SSH session not active" in error_text and retry==0:
                    self.ssh_connect()
            except Exception, e:
                image_status='ERROR'
                error_text = str(e)
                print self.name, "': create_image(",server_id,") Exception:", error_text
        
                #TODO insert a last_error at database
        self.db_lock.acquire()
        self.db.update_rows('images', {'status':image_status, 'progress': 100, 'path':file_dst}, 
                {'uuid':req['new_image']['uuid']}, log=True)
        self.db_lock.release()
  
    def edit_iface(self, port_id, old_net, new_net):
        #This action imply remove and insert interface to put proper parameters
        if self.test:
            pass
        else:
        #get iface details
            self.db_lock.acquire()
            r,c = self.db.get_table(FROM='ports as p join resources_port as rp on p.uuid=rp.port_id',
                                    WHERE={'port_id': port_id})
            self.db_lock.release()
            if r<0:
                print self.name, ": edit_iface(",port_id,") DDBB error:", c
                return
            elif r==0:
                print self.name, ": edit_iface(",port_id,") por not found"
                return
            port=c[0]
            if port["model"]!="VF":
                print self.name, ": edit_iface(",port_id,") ERROR model must be VF"
                return
            #create xml detach file
            xml=[]
            self.xml_level = 2
            xml.append("<interface type='hostdev' managed='yes'>")
            xml.append("  <mac address='" +port['mac']+ "'/>")
            xml.append("  <source>"+ self.pci2xml(port['pci'])+"\n  </source>")
            xml.apped('</interface>')                

            
            try:
                conn=None
                conn = libvirt.open("qemu+ssh://"+self.user+"@"+self.host+"/system")
                dom = conn.lookupByUUIDString(port["p.instance_id"])
                if old_net:
                    text="\n".join(xml)
                    print self.name, ": edit_iface detaching SRIOV interface", text
                    dom.detachDeviceFlags(text, flags=libvirt.VIR_DOMAIN_AFFECT_LIVE)
                if new_net:
                    xml[-1] ="  <vlan>   <tag id='" + str(port['p.vlan']) + "'/>   </vlan>"
                    self.xml_level = 1
                    xml.append(self.pci2xml(port.get('vpci',None)) )
                    xml.apped('</interface>')                
                    text="\n".join(xml)
                    print self.name, ": edit_iface attaching SRIOV interface", text
                    dom.attachDeviceFlags(text, flags=libvirt.VIR_DOMAIN_AFFECT_LIVE)
                    
            except libvirt.libvirtError, e:
                text = e.get_error_message()
                print self.name, ": edit_iface(",port["p.instance_id"],") libvirt exception:", text 
                
            finally:
                if conn is not None: conn.close
                            
                              
def create_server(server, db, db_lock, only_of_ports):
    #print "server"
    #print "server"
    #print server
    #print "server"
    #print "server"
    #try:
#            host_id = server.get('host_id', None)
    extended = server.get('extended', None)
    
#             print '----------------------'
#             print json.dumps(extended, indent=4)
    
    requirements={}
    requirements['numa']={'memory':0, 'proc_req_type': 'threads', 'proc_req_nb':0, 'port_list':[], 'sriov_list':[]}
    requirements['ram'] = server['flavor'].get('ram', 0)
    if requirements['ram']== None:
        requirements['ram'] = 0
    requirements['vcpus'] = server['flavor'].get('vcpus', 0)
    if requirements['vcpus']== None:
        requirements['vcpus'] = 0
    #If extended is not defined get requirements from flavor
    if extended is None:
        #If extended is defined in flavor convert to dictionary and use it
        if 'extended' in server['flavor'] and  server['flavor']['extended'] != None:
            json_acceptable_string = server['flavor']['extended'].replace("'", "\"")
            extended = json.loads(json_acceptable_string)
        else:
            extended = None
    #print json.dumps(extended, indent=4)
    
    #For simplicity only one numa VM are supported in the initial implementation
    if extended != None:
        numas = extended.get('numas', [])
        if len(numas)>1:
            return (-2, "Multi-NUMA VMs are not supported yet")
        #elif len(numas)<1:
        #    return (-1, "At least one numa must be specified")
    
        #a for loop is used in order to be ready to multi-NUMA VMs
        request = []
        for numa in numas:
            numa_req = {}
            numa_req['memory'] = numa.get('memory', 0)
            if 'cores' in numa: 
                numa_req['proc_req_nb'] = numa['cores']                     #number of cores or threads to be reserved
                numa_req['proc_req_type'] = 'cores'                         #indicates whether cores or threads must be reserved
                numa_req['proc_req_list'] = numa.get('cores-id', None)      #list of ids to be assigned to the cores or threads
            elif 'paired-threads' in numa:
                numa_req['proc_req_nb'] = numa['paired-threads']
                numa_req['proc_req_type'] = 'paired-threads'
                numa_req['proc_req_list'] = numa.get('paired-threads-id', None)
            elif 'threads' in numa:
                numa_req['proc_req_nb'] = numa['threads']
                numa_req['proc_req_type'] = 'threads'
                numa_req['proc_req_list'] = numa.get('threads-id', None)
            else:
                numa_req['proc_req_nb'] = 0 # by default
                numa_req['proc_req_type'] = 'threads'

            
            
            #Generate a list of sriov and another for physical interfaces 
            interfaces = numa.get('interfaces', [])
            sriov_list = []
            port_list = []
            for iface in interfaces:
                iface['bandwidth'] = int(iface['bandwidth'])
                if iface['dedicated'][:3]=='yes':
                    port_list.append(iface)
                else:
                    sriov_list.append(iface)
                    
            #Save lists ordered from more restrictive to less bw requirements
            numa_req['sriov_list'] = sorted(sriov_list, key=lambda k: k['bandwidth'], reverse=True)
            numa_req['port_list'] = sorted(port_list, key=lambda k: k['bandwidth'], reverse=True)
            
            
            request.append(numa_req)
                
    #                 print "----------\n"+json.dumps(request[0], indent=4)
    #                 print '----------\n\n'
            
        #Search in db for an appropriate numa for each requested numa
        #at the moment multi-NUMA VMs are not supported
        if len(request)>0:
            requirements['numa'].update(request[0])
    if requirements['numa']['memory']>0:
        requirements['ram']=0  #By the moment I make incompatible ask for both Huge and non huge pages memory
    elif requirements['ram']==0:
        return (-1, "Memory information not set neither at extended field not at ram")
    if requirements['numa']['proc_req_nb']>0:
        requirements['vcpus']=0 #By the moment I make incompatible ask for both Isolated and non isolated cpus
    elif requirements['vcpus']==0:
        return (-1, "Processor information not set neither at extended field not at vcpus")    


    db_lock.acquire()
    result, content = db.get_numas(requirements, server.get('host_id', None), only_of_ports)
    db_lock.release()
    
    if result == -1:
        return (-1, content)
    
    numa_id = content['numa_id']
    host_id = content['host_id']

    #obtain threads_id and calculate pinning
    cpu_pinning = []
    reserved_threads=[]
    if requirements['numa']['proc_req_nb']>0:
        db_lock.acquire()
        result, content = db.get_table(FROM='resources_core', 
                                       SELECT=('id','core_id','thread_id'),
                                       WHERE={'numa_id':numa_id,'instance_id': None, 'status':'ok'} )
        db_lock.release()
        if result <= 0:
            print content
            return -1, content
    
        #convert rows to a dictionary indexed by core_id
        cores_dict = {}
        for row in content:
            if not row['core_id'] in cores_dict:
                cores_dict[row['core_id']] = []
            cores_dict[row['core_id']].append([row['thread_id'],row['id']]) 
           
        #In case full cores are requested 
        paired = 'N'
        if requirements['numa']['proc_req_type'] == 'cores':
            #Get/create the list of the vcpu_ids
            vcpu_id_list = requirements['numa']['proc_req_list']
            if vcpu_id_list == None:
                vcpu_id_list = range(0,int(requirements['numa']['proc_req_nb']))
            
            for threads in cores_dict.itervalues():
                #we need full cores
                if len(threads) != 2:
                    continue
                
                #set pinning for the first thread
                cpu_pinning.append( [ vcpu_id_list.pop(0), threads[0][0], threads[0][1] ] )
                
                #reserve so it is not used the second thread
                reserved_threads.append(threads[1][1])
                
                if len(vcpu_id_list) == 0:
                    break
                
        #In case paired threads are requested
        elif requirements['numa']['proc_req_type'] == 'paired-threads':
            paired = 'Y'
            #Get/create the list of the vcpu_ids
            if requirements['numa']['proc_req_list'] != None:
                vcpu_id_list = []
                for pair in requirements['numa']['proc_req_list']:
                    if len(pair)!=2:
                        return -1, "Field paired-threads-id not properly specified"
                        return
                    vcpu_id_list.append(pair[0])
                    vcpu_id_list.append(pair[1])
            else:
                vcpu_id_list = range(0,2*int(requirements['numa']['proc_req_nb']))
                
            for threads in cores_dict.itervalues():
                #we need full cores
                if len(threads) != 2:
                    continue
                #set pinning for the first thread
                cpu_pinning.append([vcpu_id_list.pop(0), threads[0][0], threads[0][1]])
                
                #set pinning for the second thread
                cpu_pinning.append([vcpu_id_list.pop(0), threads[1][0], threads[1][1]])
                
                if len(vcpu_id_list) == 0:
                    break    
        
        #In case normal threads are requested
        elif requirements['numa']['proc_req_type'] == 'threads':
            #Get/create the list of the vcpu_ids
            vcpu_id_list = requirements['numa']['proc_req_list']
            if vcpu_id_list == None:
                vcpu_id_list = range(0,int(requirements['numa']['proc_req_nb']))
                                
            for threads_index in sorted(cores_dict, key=lambda k: len(cores_dict[k])):
                threads = cores_dict[threads_index]
                #set pinning for the first thread
                cpu_pinning.append([vcpu_id_list.pop(0), threads[0][0], threads[0][1]])
                
                #if exists, set pinning for the second thread
                if len(threads) == 2 and len(vcpu_id_list) != 0:
                    cpu_pinning.append([vcpu_id_list.pop(0), threads[1][0], threads[1][1]])
                
                if len(vcpu_id_list) == 0:
                    break    
    
        #Get the source pci addresses for the selected numa
        used_sriov_ports = []
        for port in requirements['numa']['sriov_list']:
            db_lock.acquire()
            result, content = db.get_table(FROM='resources_port', SELECT=('id', 'pci', 'mac'),WHERE={'numa_id':numa_id,'root_id': port['port_id'], 'port_id': None, 'Mbps_used': 0} )
            db_lock.release()
            if result <= 0:
                print content
                return -1, content
            for row in content:
                if row['id'] in used_sriov_ports or row['id']==port['port_id']:
                    continue
                port['pci'] = row['pci']
                if 'mac_address' not in port: 
                    port['mac_address'] = row['mac']
                del port['mac']
                port['port_id']=row['id']
                port['Mbps_used'] = port['bandwidth']
                used_sriov_ports.append(row['id'])
                break
        
        for port in requirements['numa']['port_list']:
            port['Mbps_used'] = None
            if port['dedicated'] != "yes:sriov":
                port['mac_address'] = port['mac']
                del port['mac']
                continue
            db_lock.acquire()
            result, content = db.get_table(FROM='resources_port', SELECT=('id', 'pci', 'mac', 'Mbps'),WHERE={'numa_id':numa_id,'root_id': port['port_id'], 'port_id': None, 'Mbps_used': 0} )
            db_lock.release()
            if result <= 0:
                print content
                return -1, content
            port['Mbps_used'] = content[0]['Mbps']
            for row in content:
                if row['id'] in used_sriov_ports or row['id']==port['port_id']:
                    continue
                port['pci'] = row['pci']
                if 'mac_address' not in port: 
                    port['mac_address'] = row['mac']  # mac cannot be set to passthrough ports 
                del port['mac']
                port['port_id']=row['id']
                used_sriov_ports.append(row['id'])
                break
    
    #             print '2. Physical ports assignation:'+json.dumps(requirements['port_list'], indent=4)
    #             print '2. SR-IOV assignation:'+json.dumps(requirements['sriov_list'], indent=4)
        
    server['host_id'] = host_id
        

    #Generate dictionary for saving in db the instance resources
    resources = {}
    resources['bridged-ifaces'] = []
    
    numa_dict = {}
    numa_dict['interfaces'] = []
    
    numa_dict['interfaces'] += requirements['numa']['port_list']
    numa_dict['interfaces'] += requirements['numa']['sriov_list']
  
    #Check bridge information
    unified_dataplane_iface=[]
    unified_dataplane_iface += requirements['numa']['port_list']
    unified_dataplane_iface += requirements['numa']['sriov_list']
    
    for control_iface in server.get('networks', []):
        control_iface['net_id']=control_iface.pop('uuid')
        #Get the brifge name
        db_lock.acquire()
        result, content = db.get_table(FROM='nets', SELECT=('name','type', 'vlan'),WHERE={'uuid':control_iface['net_id']} )
        db_lock.release()
        if result < 0: 
            pass
        elif result==0:
            return -1, "Error at field netwoks: Not found any network wit uuid %s" % control_iface['net_id']
        else:
            network=content[0]
            if control_iface.get("type", 'virtual') == 'virtual':
                if network['type']!='bridge_data' and network['type']!='bridge_man':
                    return -1, "Error at field netwoks: network uuid %s for control interface is not of type bridge_man or bridge_data" % control_iface['net_id']
                resources['bridged-ifaces'].append(control_iface)
            else:
                if network['type']!='data' and network['type']!='ptp':
                    return -1, "Error at field netwoks: network uuid %s for dataplane interface is not of type data or ptp" % control_iface['net_id']
                #dataplane interface, look for it in the numa tree and asign this network
                for dataplane_iface in numa_dict['interfaces']:
                    if dataplane_iface['name'] == control_iface.get("name"):
                        if (dataplane_iface['dedicated'] == "yes" and control_iface["type"] != "PF") or \
                            (dataplane_iface['dedicated'] == "no" and control_iface["type"] != "VF") or \
                            (dataplane_iface['dedicated'] == "yes:sriov" and control_iface["type"] != "VF not shared") :
                                return -1, "Error at field netwoks: mismatch at interface '%s' from flavor 'dedicated=%s' and networks 'type=%s'" % \
                                    (control_iface.get("name"), dataplane_iface['dedicated'], control_iface["type"])
                        dataplane_iface['uuid'] = control_iface['net_id']
                        if dataplane_iface['dedicated'] == "no":
                            dataplane_iface['vlan'] = network['vlan']
                        break
                if dataplane_iface['uuid'] == None:
                    return -1, "Error at field netwoks: interface name %s from network not found at flavor" % control_iface.get("name")
        
    resources['host_id'] = host_id
    resources['image_id'] = server['image_id']
    resources['flavor_id'] = server['flavor_id']
    resources['tenant_id'] = server['tenant_id']
    resources['ram'] = requirements['ram']
    resources['vcpus'] = requirements['vcpus']
    resources['status'] = 'CREATING'
    
    if 'description' in server: resources['description'] = server['description']
    if 'name' in server: resources['name'] = server['name']
    
    resources['extended'] = {}                          #optional
    resources['extended']['numas'] = []
    numa_dict['numa_id'] = numa_id
    numa_dict['memory'] = requirements['numa']['memory']
    numa_dict['cores'] = []

    for core in cpu_pinning:
        numa_dict['cores'].append({'id': core[2], 'vthread': core[0], 'paired': paired})
    for core in reserved_threads:
        numa_dict['cores'].append({'id': core})
    resources['extended']['numas'].append(numa_dict)
    if extended!=None and 'devices' in extended:   #TODO allow extra devices without numa
        resources['extended']['devices'] = extended['devices']
    

    print '===================================={'
    print json.dumps(resources, indent=4)
    print '====================================}'
    
    return 0, resources

    

# -*- coding: utf-8 -*-
import code

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
Implement the logic for obtaining compute nodes information 
Resource Availability Descriptor 
'''
__author__="Pablo Montes"

#TODO: remove warnings, remove unused things 

from definitionsClass import definitionsClass
from auxiliary_functions import get_ssh_connection
import libvirt
from xml.etree import ElementTree
import paramiko 
import re
import yaml


def getCredentials(creds, data):
    """Used as a backup for libvirt.openAuth in order to provide password that came with data,
    not used by the moment
    """
    print "RADclass:getCredentials", creds, data
    for cred in creds:
        print cred[1] + ": ",
        if cred[0] == libvirt.VIR_CRED_AUTHNAME:
            cred[4] = data
        elif cred[0] == libvirt.VIR_CRED_PASSPHRASE:
            cred[4] = data
        else:
            return -1
    return 0

class RADclass():
    def __init__(self):
        self.name = None
        self.machine = None
        self.user = None
        self.password = None
        self.nodes = dict()                 #Dictionary of nodes. Keys are the node id, values are Node() elements
        self.nr_processors = None           #Integer. Number of processors in the system 
        self.processor_family = None        #If all nodes have the same value equal them, otherwise keep as None
        self.processor_manufacturer = None  #If all nodes have the same value equal them, otherwise keep as None
        self.processor_version = None       #If all nodes have the same value equal them, otherwise keep as None
        self.processor_features = None      #If all nodes have the same value equal them, otherwise keep as None
        self.memory_type = None             #If all nodes have the same value equal them, otherwise keep as None
        self.memory_freq = None             #If all nodes have the same value equal them, otherwise keep as None
        self.memory_nr_channels = None      #If all nodes have the same value equal them, otherwise keep as None
        self.memory_size = None             #Integer. Sum of the memory in all nodes
        self.memory_hugepage_sz = None
        self.hypervisor = Hypervisor()      #Hypervisor information
        self.os = OpSys()                   #Operating system information
        self.ports_list = list()            #List containing all network ports in the node. This is used to avoid having defined multiple times the same port in the system
    
    
    def obtain_RAD(self, user, password, machine):
        """This function obtains the RAD information from the remote server.
        It uses both a ssh and a libvirt connection. 
        It is desirable in future versions get rid of the ssh connection, but currently 
        libvirt does not provide all the needed information. 
        Returns (True, Warning) in case of success and (False, <error>) in case of error"""
        warning_text=""
        try:
            #Get virsh and ssh connection
            (return_status, code) = get_ssh_connection(machine, user, password)
            if not return_status:
                print 'RADclass.obtain_RAD() error:', code
                return (return_status, code)
            ssh_conn = code
            
            self.connection_IP = machine
            #print "libvirt open pre"
            virsh_conn=libvirt.open("qemu+ssh://"+user+'@'+machine+"/system")
            #virsh_conn=libvirt.openAuth("qemu+ssh://"+user+'@'+machine+"/system", 
            #        [[libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE, libvirt.VIR_CRED_USERNAME], getCredentials, password],
            #        0)
            #print "libvirt open after"
            
    #         #Set connection infomation
    #         (return_status, code) = self.set_connection_info(machine, user, password)
    #         if not return_status:
    #             return (return_status, 'Error in '+machine+': '+code)
            
            #Set server name
            machine_name = get_hostname(virsh_conn)
            (return_status, code) = self.set_name(machine_name)
            if not return_status:
                return (return_status, 'Error at self.set_name in '+machine+': '+code)
            warning_text += code
            
            #Get the server processors information
            processors = dict()
            (return_status, code) = get_processor_information(ssh_conn, virsh_conn, processors)
            if not return_status:
                return (return_status, 'Error at get_processor_information in '+machine+': '+code)
            warning_text += code
            
            #Get the server memory information
            memory_nodes = dict()
            (return_status, code) = get_memory_information(ssh_conn, virsh_conn, memory_nodes)
            if not return_status:
                return (return_status, 'Error at get_memory_information in '+machine+': '+code)
            warning_text += code
            
            #Get nics information
            nic_topology = dict()
    #         (return_status, code) = get_nic_information_old(ssh_conn, nic_topology)
            (return_status, code) = get_nic_information(ssh_conn, virsh_conn, nic_topology)
            if not return_status:
                return (return_status, 'Error at get_nic_informationin '+machine+': '+code)
            warning_text += code
            
            #Pack each processor, memory node  and nics in a node element
            #and add the node to the RAD element
            for socket_id, processor in processors.iteritems():
                node = Node()
                if not socket_id in nic_topology:
                    nic_topology[socket_id] = list()
                    
                (return_status, code) = node.set(processor, memory_nodes[socket_id], nic_topology[socket_id])
    #             else:
    #                 (return_status, code) = node.set(processor, memory_nodes[socket_id])
                if not return_status:
                    return (return_status, 'Error at node.set in '+machine+': '+code)
                warning_text += code
                (return_status, code) = self.insert_node(node)
                if not return_status:
                    return (return_status, 'Error at self.insert_node in '+machine+': '+code)
                if code not in warning_text:
                    warning_text += code
            
            #Fill os data
            os = OpSys()
            (return_status, code) = get_os_information(ssh_conn, os)
            if not return_status:
                return (return_status, 'Error at get_os_information in '+machine+': '+code)
            warning_text += code
            (return_status, code) = self.set_os(os)
            if not return_status:
                return (return_status, 'Error at self.set_os in '+machine+': '+code)
            warning_text += code
            
            #Fill hypervisor data
            hypervisor = Hypervisor()
            (return_status, code) = get_hypervisor_information(virsh_conn, hypervisor)
            if not return_status:
                return (return_status, 'Error at get_hypervisor_information in '+machine+': '+code)
            warning_text += code
            (return_status, code) = self.set_hypervisor(hypervisor)
            if not return_status:
                return (return_status, 'Error at self.set_hypervisor in '+machine+': '+code)
            warning_text += code
            ssh_conn.close()
                
            return (True, warning_text)
        except libvirt.libvirtError, e:
            text = e.get_error_message()
            print 'RADclass.obtain_RAD() exception:', text
            return (False, text)
        except paramiko.ssh_exception.SSHException, e:
            text = e.args[0]
            print  "obtain_RAD ssh Exception:", text
            return False, text

    def set_name(self,name):
        """Sets the machine name. 
        Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        if not isinstance(name,str):
            return (False, 'The variable \'name\' must be text')
        self.name = name
        return (True, "")
    
    def set_connection_info(self, machine, user, password):
        """Sets the connection information. 
        Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        if not isinstance(machine,str):
            return (False, 'The variable \'machine\' must be text')
        if not isinstance(user,str):
            return (False, 'The variable \'user\' must be text')
#         if not isinstance(password,str):
#             return (False, 'The variable \'password\' must be text')
        (self.machine, self.user, self.password) = (machine, user, password)
        return (True, "")
        
    def insert_node(self,node):
        """Inserts a new node and updates class variables. 
        Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        if not isinstance(node,Node):
            return (False, 'The variable \'node\' must be a Node element')
        
        if node.id_ in self.nodes:
            return (False, 'The node is already present in the nodes list.')
        
        #Check if network ports have not been inserted previously as part of another node
        for port_key in node.ports_list:
            if port_key in self.ports_list:
                return (False, 'Network port '+port_key+' defined multiple times in the system')
            self.ports_list.append(port_key)
        
        #Insert the new node
        self.nodes[node.id_] = node
        
        #update variables
        self.update_variables()
        
        return (True, "")
    
    def update_variables(self):
        """Updates class variables. 
        Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        warning_text=""
        #The number of processors and nodes is the same
        self.nr_processors = len(self.nodes)
        
        #If all processors are the same get the values. Otherwise keep them as none
        prev_processor_family = prev_processor_manufacturer = prev_processor_version = prev_processor_features = None
        different_processor_family = different_processor_manufacturer = different_processor_version = different_processor_features = False
        for node in self.nodes.itervalues():
            (self.processor_family, self.processor_manufacturer, self.processor_version, self.processor_features) = node.get_processor_info()
            if prev_processor_family != None and self.processor_family != prev_processor_family:
                different_processor_family = True
            if prev_processor_manufacturer != None and self.processor_manufacturer != prev_processor_manufacturer:
                different_processor_manufacturer = True
            if prev_processor_version != None and self.processor_version != prev_processor_version:
                different_processor_version = True
            if prev_processor_features != None and self.processor_features != prev_processor_features:
                different_processor_features = True
            (prev_processor_family, prev_processor_manufacturer, prev_processor_version, prev_processor_features) = (self.processor_family, self.processor_manufacturer, self.processor_version, self.processor_features)

        if different_processor_family:
            self.processor_family = None
        if different_processor_features:
            self.processor_features = None
        if different_processor_manufacturer:
            self.processor_manufacturer = None
        if different_processor_version:
            self.processor_version = None
            
        #If all memory nodes are the same get the values. Otherwise keep them as none
        #Sum the total memory
        self.memory_size = 0
        different_memory_freq = different_memory_nr_channels = different_memory_type = different_memory_hugepage_sz = False
        prev_memory_freq = prev_memory_nr_channels = prev_memory_type = prev_memory_hugepage_sz = None
        for node in self.nodes.itervalues():
            (self.memory_freq, self.memory_nr_channels, self.memory_type, memory_size, self.memory_hugepage_sz) = node.get_memory_info()
            self.memory_size += memory_size 
            if prev_memory_freq != None and self.memory_freq != prev_memory_freq:
                different_memory_freq = True
            if prev_memory_nr_channels != None and self.memory_nr_channels != prev_memory_nr_channels:
                different_memory_nr_channels = True
            if prev_memory_type != None and self.memory_type != prev_memory_type:
                different_memory_type = True
            if prev_memory_hugepage_sz != None and self.memory_hugepage_sz != prev_memory_hugepage_sz:
                different_memory_hugepage_sz = True
            (prev_memory_freq, prev_memory_nr_channels, prev_memory_type, prev_memory_hugepage_sz) = (self.memory_freq, self.memory_nr_channels, self.memory_type, self.memory_hugepage_sz)
            
        if different_memory_freq:
            self.memory_freq = None
        if different_memory_nr_channels:
            self.memory_nr_channels = None
        if different_memory_type:
            self.memory_type = None
        if different_memory_hugepage_sz:
            warning_text += 'Detected different hugepages size in different sockets\n'
            
        return (True, warning_text)
        
    def set_hypervisor(self,hypervisor):
        """Sets the hypervisor. 
        Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        if not isinstance(hypervisor,Hypervisor):
            return (False, 'The variable \'hypervisor\' must be of class Hypervisor')
        
        self.hypervisor.assign(hypervisor) 
        return (True, "")
    
    def set_os(self,os):
        """Sets the operating system. 
        Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        if not isinstance(os,OpSys):
            return (False, 'The variable \'os\' must be of class OpSys')
        
        self.os.assign(os)
        return (True, "")
    
    def to_text(self):
        text= 'name: '+self.name+'\n'
        text+= 'processor:\n'
        text+= '    nr_processors: '+str(self.nr_processors)+'\n' 
        text+= '    family: '+self.processor_family+'\n'
        text+= '    manufacturer: '+self.processor_manufacturer+'\n'
        text+= '    version: '+self.processor_version+'\n'
        text+= '    features: '+str(self.processor_features)+'\n'
        text+= 'memory:\n'
        text+= '    type: '+self.memory_type+'\n'
        text+= '    freq: '+str(self.memory_freq)+'\n'
        text+= '    nr_channels: '+str(self.memory_nr_channels)+'\n'
        text+= '    size: '+str(self.memory_size)+'\n'
        text+= 'hypervisor:\n'
        text+= self.hypervisor.to_text()
        text+= 'os:\n'
        text+= self.os.to_text()
        text+= 'resource topology:\n'
        text+= '    nr_nodes: '+ str(len(self.nodes))+'\n'
        text+= '    nodes:\n'
        for node_k, node_v in self.nodes.iteritems():
            text+= '        node'+str(node_k)+':\n'
            text+= node_v.to_text()
        return text
    
    def to_yaml(self):
        return yaml.load(self.to_text())
    
class Node():
    def __init__(self):
        self.id_ = None                      #Integer. Node id. Unique in the system
        self.processor = ProcessorNode()    #Information about the processor in the node
        self.memory = MemoryNode()          #Information about the memory in the node
        self.nic_list = list()              #List of Nic() containing information about the nics associated to the node
        self.ports_list = list()            #List containing all network ports in the node. This is used to avoid having defined multiple times the same port in the system
        
    def get_processor_info(self):
        """Gets the processor information. Returns (processor_family, processor_manufacturer, processor_version, processor_features)"""
        return self.processor.get_info()
        
    def get_memory_info(self):
        """Gets the memory information. Returns (memory_freq, memory_nr_channels, memory_type, memory_size)"""
        return self.memory.get_info()
    
#     def set(self, *args):
#         """Sets the node information. Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
#         if len(args)==2:
#             processor = args[0]
#             memory = args[1]
#             nics = False
#         elif len(args)==3:
#             processor = args[0]
#             memory = args[1]
#             nic_list = args[2]
#             nics = True
#         else:
#             return (False, 'Wrong number of elements calling Node().set()')

    def set(self, processor, memory, nic_list):
        (status, return_code) = self.processor.assign(processor)
        if not status:
            return (status, return_code)
        
        self.id_ = processor.id_
        
        (status, return_code) = self.memory.assign(memory)
        if not status:
            return (status, return_code)
        
#         if nics:
        for nic in nic_list:
            if not isinstance(nic,Nic):
                return (False, 'The nics must be of type Nic')
            self.nic_list.append(nic)
            for port_key in nic.ports.iterkeys():
                if port_key in self.ports_list:
                    return (False, 'Network port '+port_key+'defined multiple times in the same node')
                self.ports_list.append(port_key)
            
        return (True,"")
   
    def assign(self, node):
        """Sets the node information. 
        Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        warning_text=""
        processor = node.processor
        memory = node.memory
        nic_list = node.nic_list
        (status, return_code) = self.processor.assign(processor)
        if not status:
            return (status, return_code)
        
        self.id_ = processor.id_
        
        (status, return_code) = self.memory.assign(memory)
        if not status:
            return (status, return_code)
        warning_text += code
        
        for nic in nic_list:
            if not isinstance(nic,Nic):
                return (False, 'The nics must be of type Nic')
            self.nic_list.append(nic)
            for port_key in nic.ports.iterkeys():
                if port_key in self.ports_list:
                    return (False, 'Network port '+port_key+'defined multiple times in the same node')
                self.ports_list.append(port_key)
            
        return (True,warning_text)
   
    def to_text(self):
        text= '            id: '+str(self.id_)+'\n'
        text+= '            cpu:\n'
        text += self.processor.to_text()
        text+= '            memory:\n'
        text += self.memory.to_text()
        if len(self.nic_list) > 0:
            text+= '            nics:\n'
            nic_index = 0
            for nic in self.nic_list:
                text+= '                nic '+str(nic_index)+':\n'
                text += nic.to_text()
                nic_index += 1
        return text
    
class ProcessorNode():
    #Definition of the possible values of processor variables
    possible_features = definitionsClass.processor_possible_features
    possible_manufacturers = definitionsClass.processor_possible_manufacturers
    possible_families = definitionsClass.processor_possible_families
    possible_versions = definitionsClass.processor_possible_versions
    
    def __init__(self):
        self.id_ = None              #Integer. Numeric identifier of the socket
        self.family = None          #Text. Family name of the processor
        self.manufacturer = None    #Text. Manufacturer of the processor
        self.version = None         #Text. Model version of the processor
        self.features = list()      #list. List of features offered by the processor
        self.cores = list()         #list. List of cores in the processor. In case of hyperthreading the coupled cores are expressed as [a,b]
        self.eligible_cores = list()#list. List of cores that can be used
        #self.decicated_cores
        #self.shared_cores -> this should also contain information to know if cores are being used
        
    def assign(self, processor):
        """Sets the processor information. 
        Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        if not isinstance(processor,ProcessorNode):
            return (False, 'The variable \'processor\' must be of class ProcessorNode')
        
        self.id_ = processor.id_
        self.family = processor.family
        self.manufacturer = processor.manufacturer
        self.version = processor.version
        self.features = processor.features
        self.cores = processor.cores
        self.eligible_cores = processor.eligible_cores
        
        return (True, "")
    
    def set(self, id_, family, manufacturer, version, features, cores):
        """Sets the processor information. 
        Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        warning_text = ""

        if not isinstance(id_,int):
            return (False, 'The processor id_ must be of type int')  
        if not isinstance(family,str):
            return (False, 'The processor family must be of type str')
        if not isinstance(manufacturer,str):
            return (False, 'The processor manufacturer must be of type str')
        if not isinstance(version,str):
            return (False, 'The processor version must be of type str')        
        if not isinstance(features,list):
            return (False, 'The processor features must be of type list')
        if not isinstance(cores,list):
            return (False, 'The processor cores must be of type list')
 
        (self.id_, self.family, self.manufacturer, self.version) = (id_, family, manufacturer, version)
 
        if not manufacturer in self.possible_manufacturers:
            warning_text += "processor manufacturer '%s' not among: %s\n" %(manufacturer, str(self.possible_manufacturers))     
        if not family in self.possible_families:
            warning_text += "family '%s' not among: %s\n" % (family, str(self.possible_families))
#        if not version in self.possible_versions:
#            warning_text += 'The version %s is not one of these: %s\n' % (version, str(self.possible_versions))
        
        for feature in features:
            if not feature in self.possible_features:
                warning_text += "processor feature '%s' not among: %s\n" % (feature, str(self.possible_versions))
            self.features.append(feature)
        
        #If hyperthreading is active cores must be coupled in the form of [[a,b],[c,d],...]
        if 'ht' in self.features:
            for iterator in sorted(cores):
                if not isinstance(iterator,list) or len(iterator) != 2 or not isinstance(iterator[0],int) or not isinstance(iterator[1],int):
                    return (False, 'The cores list for an hyperthreaded processor must be coupled in the form of [[a,b],[c,d],...] where a,b,c,d are of type int')
                self.cores.append(iterator)
        #If hyperthreading is not active the cores are a single list in the form of [a,b,c,d,...]
        else:
            for iterator in sorted(cores):
                if not isinstance(iterator,int):
                    return (False, 'The cores list for a non hyperthreaded processor must be in the form of [a,b,c,d,...] where a,b,c,d are of type int')
                self.cores.append(iterator)
        
        self.set_eligible_cores()
        
        return (True,warning_text)
           
    def set_eligible_cores(self):
        """Set the default eligible cores, this is all cores non used by the host operating system"""
        not_first = False
        for iterator in self.cores:
            if not_first:
                self.eligible_cores.append(iterator)
            else:
                not_first = True                
        return
    
    def get_info(self):
        """Returns processor parameters (self.family, self.manufacturer, self.version, self.features)"""
        return (self.family, self.manufacturer, self.version, self.features)
    
    def to_text(self):
        text= '                id: '+str(self.id_)+'\n'
        text+= '                family: '+self.family+'\n'
        text+= '                manufacturer: '+self.manufacturer+'\n'
        text+= '                version: '+self.version+'\n'
        text+= '                features: '+str(self.features)+'\n'
        text+= '                cores: '+str(self.cores)+'\n'
        text+= '                eligible_cores: '+str(self.eligible_cores)+'\n'
        return text
    
class MemoryNode():
    def __init__(self):
        self.modules = list()               #List of MemoryModule(). List of all modules installed in the node
        self.nr_channels = None             #Integer. Number of modules installed in the node
        self.node_size = None               #Integer. Total size in KiB of memory installed in the node
        self.eligible_memory = None         #Integer. Size in KiB of eligible memory in the node     
        self.hugepage_sz = None             #Integer. Size in KiB of hugepages
        self.hugepage_nr = None             #Integer. Number of hugepages allocated in the module
        self.eligible_hugepage_nr = None    #Integer. Number of eligible hugepages in the node
        self.type_ = None                    #Text. Type of memory modules. If modules have a different value keep it as None
        self.freq = None                    #Integer. Frequency of the modules in MHz. If modules have a different value keep it as None
        self.module_size = None             #Integer. Size of the modules in KiB. If modules have a different value keep it as None
        self.form_factor = None             #Text. Form factor of the modules. If modules have a different value keep it as None
       
    def assign(self, memory_node):
        return self.set(memory_node.modules, memory_node.hugepage_sz, memory_node.hugepage_nr)
         
    def set(self, modules, hugepage_sz, hugepage_nr):
        """Set the memory node information. hugepage_sz must be expressed in KiB. 
        Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        if not isinstance(modules, list):
            return (False, 'The modules must be a list of elements of class MemoryModule')
        if not isinstance(hugepage_sz,int):
            return (False, 'The hugepage_sz variable must be an int expressing the size in KiB')
        if not isinstance(hugepage_nr,int):
            return (False, 'The hugepage_nr variable must be of type int')
        
        (self.hugepage_sz, self.hugepage_nr) = (hugepage_sz, hugepage_nr)
        self.node_size = self.nr_channels = 0
        
        different_type = different_freq = different_module_size = different_form_factor = False
        prev_type = prev_freq = prev_module_size = prev_form_factor = None
        for iterator in modules:
            if not isinstance(iterator,MemoryModule):
                return (False, 'The modules must be a list of elements of class MemoryModule')
            self.modules.append(iterator)
            (self.type_, self.freq, self.module_size, self.form_factor) = (iterator.type_, iterator.freq, iterator.size, iterator.form_factor)
            self.node_size += self.module_size
            self.nr_channels += 1
            if prev_type != None and prev_type != self.type_:
                different_type = True
            if prev_freq != None and prev_freq != self.freq:
                different_freq = True
            if prev_module_size != None and prev_module_size != self.module_size:
                different_module_size = True
            if prev_form_factor != None and prev_form_factor != self.form_factor:
                different_form_factor = True
            (prev_type, prev_freq, prev_module_size, prev_form_factor) = (self.type_, self.freq, self.module_size, self.form_factor)
        
        if different_type:
            self.type_ = None
        if different_freq:
            self.freq = None
        if different_module_size:
            self.module_size = None
        if different_form_factor:
            self.form_factor = None
        
        (return_value, error_code) = self.set_eligible_memory()
        if not return_value:
            return (return_value, error_code)
        
        return (True, "")
    
    def set_eligible_memory(self):
        """Sets the default eligible_memory and eligible_hugepage_nr. This is all memory but 2GiB and all hugepages"""
        self.eligible_memory = self.node_size - 2*1024*1024
        if self.eligible_memory < 0:
            return (False, "There is less than 2GiB of memory in the module")
        
        self.eligible_hugepage_nr = self.hugepage_nr 
        return (True,"")
    
    def get_info(self):
        """Return memory information (self.freq, self.nr_channels, self.type_, self.node_size)"""
        return (self.freq, self.nr_channels, self.type_, self.node_size, self.hugepage_sz)
        
    def to_text(self):
        text= '                node_size: '+str(self.node_size)+'\n'
        text+= '                nr_channels: '+str(self.nr_channels)+'\n'
        text+= '                eligible_memory: '+str(self.eligible_memory)+'\n'
        text+= '                hugepage_sz: '+str(self.hugepage_sz)+'\n'
        text+= '                hugepage_nr: '+str(self.hugepage_nr)+'\n'
        text+= '                eligible_hugepage_nr: '+str(self.eligible_hugepage_nr)+'\n'
        text+= '                type: '+self.type_+'\n'
        text+= '                freq: '+str(self.freq)+'\n'
        text+= '                module_size: '+str(self.module_size)+'\n'
        text+= '                form_factor: '+self.form_factor+'\n'
        text+= '                modules details:\n'
        for module in self.modules:
            text += module.to_text()
        return text
        
class MemoryModule():
    #Definition of the possible values of module variables
    possible_types = definitionsClass.memory_possible_types
    possible_form_factors = definitionsClass.memory_possible_form_factors
    
    def __init__(self):
        self.locator = None     #Text. Name of the memory module
        self.type_ = None        #Text. Type of memory module
        self.freq = None        #Integer. Frequency of the module in MHz
        self.size = None        #Integer. Size of the module in KiB
        self.form_factor = None #Text. Form factor of the module
        
    def set(self, locator, type_, freq, size, form_factor):
        """Sets the memory module information. 
        Frequency must be expressed in MHz and size in KiB.
        Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        warning_text=""
        if not isinstance(locator, str):
            return (False, "The type of the variable locator must be str")
        if not isinstance(type_, str):
            return (False, "The type of the variable type_ must be str")
        if not isinstance(form_factor, str):
            return (False, "The type of the variable form_factor must be str")
        if not isinstance(freq, int):
            return (False, "The type of the variable freq must be int")
        if not isinstance(size, int):
            return (False, "The type of the variable size must be int")
        
        if not form_factor in self.possible_form_factors:
            warning_text += "memory form_factor '%s' not among: %s\n" %(form_factor, str(self.possible_form_factors))
        if not type_ in self.possible_types:
            warning_text += "memory type '%s' not among: %s\n" %(type_, str(self.possible_types))
        
        (self.locator, self.type_, self.freq, self.size, self.form_factor) = (locator, type_, freq, size, form_factor)
        return (True, warning_text)   
    
    def to_text(self):
        text= '                    '+self.locator+':\n'
        text+= '                        type: '+self.type_+'\n'
        text+= '                        freq: '+str(self.freq)+'\n'
        text+= '                        size: '+str(self.size)+'\n'
        text+= '                        form factor: '+self.form_factor+'\n'
        return text
         
class Nic():
    def __init__(self):
        self.model = None       #Text. Model of the nic
        self.ports = dict()     #Dictionary of ports. Keys are the port name, value are Port() elements
    
    def set_model(self, model):
        """Sets the model of the nic. Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        if not isinstance(model,str):
            return (False, 'The \'model\' must be of type str')
           
        self.model = model
        return (True, "")
   
    def add_port(self, port):
        """Adds a port to the nic. Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
        if not isinstance(port,Port):
            return (False, 'The \'port\' must be of class Port')
       
#        port_id = str(port.pci_device_id[0])+':'+str(port.pci_device_id[1])+':'+str(port.pci_device_id[2])+'.'+str(port.pci_device_id[3])
#CHANGED
#        port_id = port.name
        port_id = port.pci_device_id
#CHANGED END 
        if port_id in self.ports:
            return (False, 'The \'port\' '+port.pci_device_id+' is duplicated in the nic')
#             return (False, 'The \'port\' is duplicated in the nic')
       
        self.ports[port_id] = port
        return (True, "")
   
    def to_text(self):
        text= '                    model: '+ str(self.model)+'\n'
        text+= '                    ports: '+'\n'
        for key,port in self.ports.iteritems():
            text+= '                        "'+key+'":'+'\n'
            text += port.to_text()
        return text
               
class Port():
    def __init__(self):
        self.name = None            #Text. Port name
        self.virtual = None         #Boolean. States if the port is a virtual function
        self.enabled = None         #Boolean. States if the port is enabled
        self.eligible = None        #Boolean. States if the port is eligible
        self.speed = None           #Integer. Indicates the speed in Mbps
        self.available_bw = None    #Integer. BW in Mbps that is available.
        self.mac = None             #list. Indicates the mac address of the port as a list in format ['XX','XX','XX','XX','XX','XX']
        self.pci_device_id_split = None   #list. Indicates the pci address  of the port as a list in format ['XXXX','XX','XX','X']
        self.pci_device_id = None
        self.PF_pci_device_id = None
        
#     def set(self, name, virtual, enabled, speed, mac, pci_device_id, pci_device_id_split):
#         """Sets the port information. The variable speed indicates the speed in Mbps. Returns (True,Warning) in case of success and ('False',<error description>) in case of error"""
#         if not isinstance(name,str):
#             return (False, 'The variable \'name\' must be of type str')
#         if not isinstance(virtual,bool):
#             return (False, 'The variable \'virtual\' must be of type bool')
#         if not isinstance(enabled,bool):
#             return (False, 'The variable \'enabled\' must be of type bool')
#         if not isinstance(enabled,bool):
#             return (speed, 'The variable \'speed\' must be of type int')
#         if not isinstance(mac, list) and not isinstance(mac,NoneType):
#             return (False, 'The variable \'enabled\' must be of type list indicating the mac address in format [\'XXXX\',\'XX\',\'XX\',\'X\'] or NoneType')
#         if not isinstance(pci_device_id_split, list) or len(pci_device_id_split) != 4: 
#             return (False, 'The variable \'pci_device_id_split\' must be of type list, indicating the pci address in format [\'XX\',\'XX\',\'XX\',\'XX\',\'XX\',\'XX\']')
#         
#         expected_len = [4,2,2,1]
#         index = 0
#         for iterator in pci_device_id_split:
#             if not isinstance(iterator,str) or not iterator.isdigit() or len(iterator) != expected_len[index]:
#                 return (False, 'The variable \'pci_device_id_split\' must be of type list, indicating the pci address in format [\'XX\',\'XX\',\'XX\',\'XX\',\'XX\',\'XX\']')
#             index += 1
#             
#         if not isinstance(mac,NoneType):
#             for iterator in mac:
#                 if not isinstance(iterator,str) or not iterator.isalnum() or len(iterator) != 2:
#                     return (False, 'The variable \'enabled\' must be of type list indicating the mac address in format [\'XXXX\',\'XX\',\'XX\',\'X\'] or NoneType')
#         
#         #By default only virtual ports are eligible
# #         (self.name, self.virtual, self.enabled, self.eligible, self.available_bw, self.speed, self.mac, self.pci_device_id, self.pci_device_id_split) = (name, virtual, enabled, virtual, speed, speed, mac, pci_device_id, pci_device_id_split)
#         (self.name, self.virtual, self.enabled, self.eligible, self.available_bw, self.mac, self.pci_device_id, self.pci_device_id_split) = (name, virtual, enabled, virtual, speed, mac, pci_device_id, pci_device_id_split)

    def to_text(self):
        text= '                            pci: "'+ str(self.pci_device_id)+'"\n'
        text+= '                            virtual: '+ str(self.virtual)+'\n'
        if self.virtual:
            text+= '                            PF_pci_id: "'+self.PF_pci_device_id+'"\n'
        text+= '                            eligible: '+ str(self.eligible)+'\n'
        text+= '                            enabled: '+str(self.enabled)+'\n'
        text+= '                            speed: '+ str(self.speed)+'\n'
        text+= '                            available bw: '+ str(self.available_bw)+'\n'
        text+= '                            mac: '+ str(self.mac)+'\n'
        text+= '                            source_name: '+ str(self.name)+'\n'
        return text
    
class Hypervisor():
    #Definition of the possible values of hypervisor variables
    possible_types = definitionsClass.hypervisor_possible_types
    possible_domain_types = definitionsClass.hypervisor_possible_domain_types

    def __init__(self):
        self.type_ = None            #Text. Hypervisor type_
        self.version = None         #int. Hypervisor version
        self.lib_version = None     #int. Libvirt version used to compile hypervisor
        self.domains = list()       #list. List of all the available domains
        
    def set(self, hypervisor, version, lib_version, domains):
        warning_text=""
        if not isinstance(hypervisor,str):
            return (False, 'The variable type_ must be of type str')
        if not isinstance(version,int):
            return (False, 'The variable version must be of type int')
        if not isinstance(lib_version,int):
            return (False, 'The library version must be of type int')
        if not isinstance(domains,list):
            return (False, 'Domains must be a list of the possible domains as str')
        
        if not hypervisor in self.possible_types:
            warning_text += "Hyperpivor '%s' not among: %s\n" % (hypervisor, str(self.possible_types))
        
        valid_domain_found = False
        for domain in domains:
            if not isinstance(domain,str):
                return (False, 'Domains must be a list of the possible domains as str')
            if domain in self.possible_domain_types:
                valid_domain_found = True
                self.domains.append(domain)
                
        if not valid_domain_found:
            warning_text += 'No valid domain found among: %s\n' % str(self.possible_domain_types)
            
        
        (self.version, self.lib_version, self.type_) = (version, lib_version, hypervisor)
        return (True, warning_text)
     
    def assign(self, hypervisor):
        (self.version, self.lib_version, self.type_) = (hypervisor.version, hypervisor.lib_version, hypervisor.type_)
        for domain in hypervisor.domains:
            self.domains.append(domain)
        return
           
    def to_text(self):
        text= '    type: '+self.type_+'\n'
        text+= '    version: '+str(self.version)+'\n'
        text+= '    libvirt version: '+ str(self.lib_version)+'\n'
        text+= '    domains: '+str(self.domains)+'\n'
        return text
        
class OpSys():
    #Definition of the possible values of os variables
    possible_id = definitionsClass.os_possible_id
    possible_types = definitionsClass.os_possible_types
    possible_architectures = definitionsClass.os_possible_architectures

    def __init__(self):
        self.id_ = None                   #Text. Identifier of the OS. Formed by <Distibutor ID>-<Release>-<Codename>. In linux this can be obtained using lsb_release -a
        self.type_ = None                 #Text. Type of operating system
        self.bit_architecture = None     #Integer. Architecture
        
    def set(self, id_, type_, bit_architecture):
        warning_text=""
        if not isinstance(type_,str):
            return (False, 'The variable type_ must be of type str')
        if not isinstance(id_,str):
            return (False, 'The variable id_ must be of type str')
        if not isinstance(bit_architecture,str):
            return (False, 'The variable bit_architecture must be of type str')
        
        if not type_ in self.possible_types:
            warning_text += "os type '%s' not among: %s\n" %(type_, str(self.possible_types))
        if not id_ in self.possible_id:
            warning_text += "os release '%s' not among: %s\n" %(id_, str(self.possible_id))
        if not bit_architecture in self.possible_architectures:
            warning_text += "os bit_architecture '%s' not among: %s\n" % (bit_architecture, str(self.possible_architectures))
        
        (self.id_, self.type_, self.bit_architecture) = (id_, type_, bit_architecture)
        return (True, warning_text)
    
    def assign(self,os):
        (self.id_, self.type_, self.bit_architecture) = (os.id_, os.type_, os.bit_architecture)
        return
    
    def to_text(self):
        text= '    id: '+self.id_+'\n'
        text+= '    type: '+self.type_+'\n'
        text+= '    bit_architecture: '+self.bit_architecture+'\n'
        return text
     
def get_hostname(virsh_conn):
    return virsh_conn.getHostname().rstrip('\n')

def get_hugepage_size(ssh_conn):
    command = 'sudo hugeadm --page-sizes'
#  command = 'hugeadm --page-sizes-all'
    (_, stdout, stderr) = ssh_conn.exec_command(command)
    error = stderr.read()
    if len(error)>0:
        raise paramiko.ssh_exception.SSHException(command +' : '+ error)
    mem=stdout.read()
    if mem=="":
        return 0
    return int(mem)

def get_hugepage_nr(ssh_conn,hugepage_sz, node_id):
    command = 'cat /sys/devices/system/node/node'+str(node_id)+'/hugepages/hugepages-'+str(hugepage_sz/1024)+'kB/nr_hugepages'
    (_, stdout, _) = ssh_conn.exec_command(command)
    #print command, 
    #text = stdout.read()
    #print "'"+text+"'"
    #return int(text)
    
    try:
        value=int(stdout.read())
    except: 
        value=0
    return value

def get_memory_information(ssh_conn, virsh_conn, memory_nodes):
    warning_text=""
    tree=ElementTree.fromstring(virsh_conn.getSysinfo(0))
    memory_dict = dict()
    for target in tree.findall("memory_device"):
        locator_f = size_f = freq_f = type_f = formfactor_f = False
        module_form_factor = ""
        for entry in target.findall("entry"):
            if entry.get("name") == 'size':
                size_f = True
                size_split = entry.text.split(' ')
                if size_split[1] == 'MB':
                    module_size = int(size_split[0]) * 1024 * 1024
                elif size_split[1] == 'GB':
                    module_size = int(size_split[0]) * 1024 * 1024 * 1024
                elif size_split[1] == 'KB':
                    module_size = int(size_split[0]) * 1024
                else:
                    module_size = int(size_split[0])
                
            elif entry.get("name") == 'speed':
                freq_f = True
                freq_split = entry.text.split(' ')
                if freq_split[1] == 'MHz':
                    module_freq = int(freq_split[0]) * 1024 * 1024
                elif freq_split[1] == 'GHz':
                    module_freq = int(freq_split[0]) * 1024 * 1024 * 1024
                elif freq_split[1] == 'KHz':
                    module_freq = int(freq_split[0]) * 1024
            
            elif entry.get("name") == 'type':
                type_f = True
                module_type = entry.text
                   
            elif entry.get("name") == 'form_factor':
                formfactor_f = True
                module_form_factor = entry.text  
                   
            elif entry.get("name") == 'locator' and not locator_f:
                # other case, it is obtained by bank_locator that we give priority to
                locator = entry.text
                pos = locator.find(module_form_factor)
                if module_form_factor == locator[0:len(module_form_factor) ]:
                    pos = len(module_form_factor) +1 
                else:
                    pos = 0
                if locator[pos] in "ABCDEFGH":  
                    locator_f = True
                    node_id = ord(locator[pos])-ord('A')
                    #print entry.text, node_id

            elif entry.get("name") == 'bank_locator':
                locator = entry.text
                pos = locator.find("NODE ")
                if pos >= 0 and len(locator)>pos+5:
                    if locator[pos+5] in ("01234567"): #len("NODE ") is 5
                        node_id = int(locator[pos+5])
                        locator_f = True
             
        #When all module fields have been found add a new module to the list 
        if locator_f and size_f and freq_f and type_f and formfactor_f:
            #If the memory node has not yet been created create it
            if node_id not in memory_dict:
                memory_dict[node_id] = []
                
            #Add a new module to the memory node
            module = MemoryModule()
            (return_status, code) = module.set(locator, module_type, module_freq, module_size, module_form_factor)
            if not return_status:
                return (return_status, code)
            memory_dict[node_id].append(module)
            if code not in warning_text:
                warning_text += code
    
    #Fill memory nodes
    #Hugepage size is constant for all nodes
    hugepage_sz = get_hugepage_size(ssh_conn)
    for node_id, modules in memory_dict.iteritems():
        memory_node = MemoryNode()
        memory_node.set(modules, hugepage_sz, get_hugepage_nr(ssh_conn,hugepage_sz, node_id))
        memory_nodes[node_id] = memory_node
        
    return (True, warning_text)

def get_cpu_topology_ht(ssh_conn, topology):
    command = 'cat /proc/cpuinfo'
    (_, stdout, stderr) = ssh_conn.exec_command(command)
    error = stderr.read()
    if len(error)>0:
        raise paramiko.ssh_exception.SSHException(command +' : '+ error)
    sockets = []
    cores = []
    core_map = {}
    core_details = []
    core_lines = {}
    for line in stdout.readlines():
        if len(line.strip()) != 0:
            name, value = line.split(":", 1)
            core_lines[name.strip()] = value.strip()
        else:
            core_details.append(core_lines)
            core_lines = {}
    
    for core in core_details:
        for field in ["processor", "core id", "physical id"]:
            if field not in core:
                return(False,'Error getting '+field+' value from /proc/cpuinfo')
            core[field] = int(core[field])
    
        if core["core id"] not in cores:
            cores.append(core["core id"])
        if core["physical id"] not in sockets:
            sockets.append(core["physical id"])
        key = (core["physical id"], core["core id"])
        if key not in core_map:
            core_map[key] = []
        core_map[key].append(core["processor"])
      
    for s in sockets:
        hyperthreaded_cores = list()
        for c in cores:
            hyperthreaded_cores.append(core_map[(s,c)])
        topology[s] = hyperthreaded_cores
      
    return (True, "")

def get_processor_information(ssh_conn, vish_conn, processors):
    warning_text=""
    #Processor features are the same for all processors
    #TODO (at least using virsh capabilities)nr_numa_nodes
    capabilities = list()
    tree=ElementTree.fromstring(vish_conn.getCapabilities())
    for target in tree.findall("host/cpu/feature"):
        if target.get("name") == 'pdpe1gb':
            capabilities.append('lps')
        elif target.get("name") == 'dca':
            capabilities.append('dioc')  
        elif target.get("name") == 'vmx' or target.get("name") == 'svm':
            capabilities.append('hwsv')
        elif target.get("name") == 'ht':
            capabilities.append('ht')
        
    target = tree.find("host/cpu/arch")
    if target.text == 'x86_64' or target.text == 'amd64':
        capabilities.append('64b')
      
    command = 'cat /proc/cpuinfo | grep flags'
    (_, stdout, stderr) = ssh_conn.exec_command(command)
    error = stderr.read()
    if len(error)>0:
        raise paramiko.ssh_exception.SSHException(command +' : '+ error)
    line = stdout.readline()
    if 'ept' in line or 'npt' in line:
        capabilities.append('tlbps')
    
    #Find out if IOMMU is enabled
    command = 'dmesg |grep -e Intel-IOMMU'
    (_, stdout, stderr) = ssh_conn.exec_command(command)
    error = stderr.read()
    if len(error)>0:
        raise paramiko.ssh_exception.SSHException(command +' : '+ error)
    if 'enabled' in stdout.read():
        capabilities.append('iommu')
      
    #Equivalent for AMD
    command = 'dmesg |grep -e AMD-Vi'
    (_, stdout, stderr) = ssh_conn.exec_command(command)
    error = stderr.read()
    if len(error)>0:
        raise paramiko.ssh_exception.SSHException(command +' : '+ error)
    if len(stdout.read()) > 0:
        capabilities.append('iommu')
    
    #-----------------------------------------------------------
    topology = dict()
    #In case hyperthreading is active it is necessary to determine cpu topology using /proc/cpuinfo
    if 'ht' in capabilities:
        (return_status, code) = get_cpu_topology_ht(ssh_conn, topology)
        if not return_status:
            return (return_status, code)
        warning_text += code

    #Otherwise it is possible to do it using virsh capabilities
    else:
        for target in tree.findall("host/topology/cells/cell"):
            socket_id = int(target.get("id"))
            topology[socket_id] = list()
            for cpu in target.findall("cpus/cpu"):
                topology[socket_id].append(int(cpu.get("id")))
    
    #-----------------------------------------------------------         
    #Create a dictionary with the information of all processors
    #p_fam = p_man = p_ver = None
    tree=ElementTree.fromstring(vish_conn.getSysinfo(0))
    #print vish_conn.getSysinfo(0)
    #return (False, 'forces error for debuging')
    not_populated=False
    socket_id = -1     #in case we can not determine the socket_id we assume incremental order, starting by 0
    for target in tree.findall("processor"):
        count = 0
        socket_id += 1
        #Get processor id, family, manufacturer and version
        for entry in target.findall("entry"):
            if entry.get("name") == "status":
                if entry.text[0:11] == "Unpopulated":
                    not_populated=True
            elif entry.get("name") == 'socket_destination':
                socket_text = entry.text
                if socket_text.startswith('CPU'):
                    socket_text = socket_text.strip('CPU')
                    socket_text = socket_text.strip() #removes trailing spaces
                    if socket_text.isdigit() and int(socket_text)<9 and int(socket_text)>0:
                        socket_id = int(socket_text) - 1
              
            elif entry.get("name") == 'family':
                family = entry.text
                count += 1
            elif entry.get("name") == 'manufacturer':
                manufacturer = entry.text
                count += 1
            elif entry.get("name") == 'version':
                version = entry.text.strip()
                count += 1
        if count != 3:
            return (False, 'Error. Not all expected fields could be found in processor')
        
        #Create and fill processor structure
        if not_populated:
            continue  #avoid inconsistence of some machines where more socket detected than 
        processor = ProcessorNode()
        (return_status, code) = processor.set(socket_id, family, manufacturer, version, capabilities, topology[socket_id])
        if not return_status:
            return (return_status, code)
        if code not in warning_text:
            warning_text += code

        #Add processor to the processors dictionary
        processors[socket_id] = processor
    
    return (True, warning_text)

def get_nic_information(ssh_conn, virsh_conn, nic_topology):   
    warning_text=""
    #Get list of net devices
    net_devices = virsh_conn.listDevices('net',0)
    print virsh_conn.listDevices('net',0)
    for device in net_devices:
        try:
            #Get the XML descriptor of the device:
            net_XML = ElementTree.fromstring(virsh_conn.nodeDeviceLookupByName(device).XMLDesc(0))
            #print "net_XML:" , net_XML
            #obtain the parent
            parent = net_XML.find('parent')
            if parent == None:
                print 'No parent was found in XML for device '+device
                #Error. continue?-------------------------------------------------------------
                continue
            if parent.text == 'computer':
                continue
            if not parent.text.startswith('pci_'):
                print device + ' parent is neither computer nor pci'
                #Error. continue?-------------------------------------------------------------
                continue
            interface = net_XML.find('capability/interface').text
            mac = net_XML.find('capability/address').text
            
            #Get the pci XML
            pci_XML = ElementTree.fromstring(virsh_conn.nodeDeviceLookupByName(parent.text).XMLDesc(0))
            #print pci_XML
            #Get pci
            name = pci_XML.find('name').text.split('_')
            pci = name[1]+':'+name[2]+':'+name[3]+'.'+name[4]
            
            #If slot == 0 it is a PF, otherwise it is a VF
            capability = pci_XML.find('capability')
            if capability.get('type') != 'pci':
                print device + 'Capability is not of type pci in '+parent.text
                #Error. continue?-------------------------------------------------------------
                continue
            slot = capability.find('slot').text
            bus = capability.find('bus').text
            node_id = None
            numa_ = capability.find('numa')
            if numa_ != None:
                node_id = numa_.get('node');
                if node_id != None: node_id =int(node_id)
            if slot == None or bus == None:
                print device + 'Bus and slot not detected in '+parent.text
                #Error. continue?-------------------------------------------------------------
                continue
            if slot != '0':
    #             print ElementTree.tostring(pci_XML)
                virtual = True
                capability_pf = capability.find('capability')
                if capability_pf.get('type') != 'phys_function':
                    print 'physical_function not found in VF '+parent.text
                    #Error. continue?-------------------------------------------------------------
                    continue
                PF_pci = capability_pf.find('address').attrib
                PF_pci_text = PF_pci['domain'].split('x')[1]+':'+PF_pci['bus'].split('x')[1]+':'+PF_pci['slot'].split('x')[1]+'.'+PF_pci['function'].split('x')[1]
                
            else:
                virtual = False
            
            #Obtain node for the port
            if node_id == None:
                node_id = int(bus)>>6
            #print "node_id:", node_id
            
            #Only for non virtual interfaces: Obtain speed and if link is detected (this must be done using ethtool)
            if not virtual:
                command = 'sudo ethtool '+interface+' | grep -e Speed -e "Link detected"'
                (_, stdout, stderr) = ssh_conn.exec_command(command)
                error = stderr.read()
                if len(error) >0:
                    print 'Error running '+command+'\n'+error
                    #Error. continue?-------------------------------------------------------------
                    continue
                for line in stdout.readlines():
                    line = line.strip().rstrip('\n').split(': ')
                    if line[0] == 'Speed':
                        if line[1].endswith('Mb/s'):
                            speed = int(line[1].split('M')[0])*int(1e6)
                        elif line[1].endswith('Gb/s'):
                            speed = int(line[1].split('G')[0])*int(1e9)
                        elif line[1].endswith('Kb/s'):
                            speed = int(line[1].split('K')[0])*int(1e3)
                        else:
                            #the interface is listed but won't be used
                            speed = 0
                    elif line[0] == 'Link detected':
                        if line[1] == 'yes':
                            enabled = True
                        else:
                            enabled = False
                    else:
                        print 'Unnexpected output of command '+command+':'
                        print line
                        #Error. continue?-------------------------------------------------------------
                        continue
                
            if not node_id in nic_topology:
                nic_topology[node_id] = list()
                #With this implementation we make the RAD with only one nic per node and this nic has all ports, TODO: change this by including parent information of PF
                nic_topology[node_id].append(Nic())
             
            #Load the appropriate nic    
            nic = nic_topology[node_id][0]
            
            #Create a new port and fill it
            port = Port()
            port.name = interface
            port.virtual = virtual
            port.speed = speed
            if virtual:
                port.available_bw = 0
                port.PF_pci_device_id = PF_pci_text
            else:
                port.available_bw = speed
                if speed == 0:
                    port.enabled = False
                else:
                    port.enabled = enabled

            port.eligible = virtual  #Only virtual ports are eligible
            port.mac = mac
            port.pci_device_id = pci
            port.pci_device_id_split = name[1:]
            
            #Save the port information
            nic.add_port(port)         
        except Exception,e:
            print 'Error: '+str(e)

    #set in vitual ports if they are enabled
    for nic in nic_topology.itervalues():
        for port in nic[0].ports.itervalues():
#             print port.pci_device_id
            if port.virtual:
                enabled = nic[0].ports.get(port.PF_pci_device_id)
                if enabled == None:
                    return(False, 'The PF '+port.PF_pci_device_id+' (VF '+port.pci_device_id+') is not present in ports dict')
                #Only if the PF is enabled the VF can be enabled
                if nic[0].ports[port.PF_pci_device_id].enabled:
                    port.enabled = True
                else:
                    port.enabled = False
            
    return (True, warning_text)     

def get_nic_information_old(ssh_conn, nic_topology):
    command = 'lstopo-no-graphics --of xml'
    (_, stdout, stderr) = ssh_conn.exec_command(command)
    error = stderr.read()
    if len(error)>0:
        raise paramiko.ssh_exception.SSHException(command +' : '+ error)
    tree=ElementTree.fromstring(stdout.read())
    for target in tree.findall("object/object"):
        #Find numa nodes
        if target.get("type") != "NUMANode":
            continue
        node_id = int(target.get("os_index"))
        nic_topology[node_id] = list()
        
        #find nics in numa node
        for entry in target.findall("object/object"):
            if entry.get("type") != 'Bridge':
                continue
            nic_name = entry.get("name")
            model = None
            nic = Nic()
            
            #find ports in nic
            for pcidev in entry.findall("object"):
                if pcidev.get("type") != 'PCIDev':
                    continue
                enabled = speed = mac = pci_busid = None
                port = Port()
                model = pcidev.get("name")
                virtual = False
                if 'Virtual' in model:
                    virtual = True
                pci_busid = pcidev.get("pci_busid")
                for osdev in pcidev.findall("object"):
                    name = osdev.get("name")
                    for info in osdev.findall("info"):
                        if info.get("name") != 'Address':
                            continue
                        mac = info.get("value")
                        #get the port speed and status
                        command = 'sudo ethtool '+name
                        (_, stdout, stderr) = ssh_conn.exec_command(command)
                        error = stderr.read()
                        if len(error)>0:
                            return (False, 'Error obtaining '+name+' information: '+error)
                        ethtool = stdout.read()
                        if '10000baseT/Full' in ethtool:
                            speed = 10e9
                        elif '1000baseT/Full' in ethtool:
                            speed = 1e9
                        elif '100baseT/Full' in ethtool:
                            speed = 100e6
                        elif '10baseT/Full' in ethtool:
                            speed = 10e6
                        else:
                            return (False, 'Speed not detected in '+name)

                    enabled = False
                    if 'Link detected: yes' in ethtool:
                        enabled = True
                    
                    if speed != None and mac != None and pci_busid != None:
                        mac = mac.split(':')
                        pci_busid_split = re.split(':|\.', pci_busid)
                        #Fill the port information
                        port.set(name, virtual, enabled, speed, mac, pci_busid, pci_busid_split)
                        nic.add_port(port)
              
            if len(nic.ports) > 0:  
                #Fill the nic model
                if model != None:
                    nic.set_model(model)
                else:
                    nic.set_model(nic_name)
                
                #Add it to the topology
                nic_topology[node_id].append(nic)
                
    return (True, "")

def get_os_information(ssh_conn, os):
    warning_text=""
#    command = 'lsb_release -a'
#    (stdin, stdout, stderr) = ssh_conn.exec_command(command)
#    cont = 0
#    for line in stdout.readlines():
#        line_split = re.split('\t| *', line.rstrip('\n'))
#        if line_split[0] == 'Distributor' and line_split[1] == 'ID:':
#            distributor = line_split[2]
#            cont += 1
#        elif line_split[0] == 'Release:':
#            release = line_split[1]
#            cont += 1
#        elif line_split[0] == 'Codename:':
#            codename = line_split[1]
#            cont += 1
#    if cont != 3:
#        return (False, 'It was not possible to obtain the OS id')
#    id_ = distributor+'-'+release+'-'+codename


    command = 'cat /etc/redhat-release'
    (_, stdout, _) = ssh_conn.exec_command(command)
    id_text= stdout.read()
    if len(id_text)==0:
        #try with Ubuntu
        command = 'lsb_release -d -s'
        (_, stdout, _) = ssh_conn.exec_command(command)
        id_text= stdout.read()
    if len(id_text)==0:
        raise paramiko.ssh_exception.SSHException("Can not determinte release neither with 'lsb_release' nor with 'cat /etc/redhat-release'")
    id_ = id_text.rstrip('\n')
   
    command = 'uname -o'
    (_, stdout, stderr) = ssh_conn.exec_command(command)
    error = stderr.read()
    if len(error)>0:
        raise paramiko.ssh_exception.SSHException(command +' : '+ error)
    type_ = stdout.read().rstrip('\n')
    
    command = 'uname -i'
    (_, stdout, stderr) = ssh_conn.exec_command(command)
    error = stderr.read()
    if len(error)>0:
        raise paramiko.ssh_exception.SSHException(command +' : '+ error)
    bit_architecture = stdout.read().rstrip('\n')
    
    (return_status, code) = os.set(id_, type_, bit_architecture)
    if not return_status:
        return (return_status, code)
    warning_text += code
    return (True, warning_text) 

def get_hypervisor_information(virsh_conn, hypervisor):
    type_ = virsh_conn.getType().rstrip('\n')
    version = virsh_conn.getVersion()
    lib_version = virsh_conn.getLibVersion()
    
    domains = list()
    tree=ElementTree.fromstring(virsh_conn.getCapabilities())
    for target in tree.findall("guest"):
        os_type = target.find("os_type").text
        #We only allow full virtualization
        if os_type != 'hvm':
            continue
        wordsize = int(target.find('arch/wordsize').text)
        if wordsize == 64:
            for domain in target.findall("arch/domain"):
                domains.append(domain.get("type"))
            
    (return_status, code) = hypervisor.set(type_, version, lib_version, domains)
    if not return_status:
        return (return_status, code)
    return (True, code)      
     
class RADavailableResourcesClass(RADclass):
    def __init__(self, resources):
        """Copy resources from the RADclass (server resources not taking into account resources used by VMs"""
        #New
        self.reserved = dict()          #Dictionary of reserved resources for a server. Key are VNFC names and values RADreservedResources
        self.cores_consumption = None   #Dictionary of cpu consumption. Key is the cpu and the value is
        
        self.machine = resources.machine
        self.user = resources.user
        self.password = resources.password
        self.name = resources.name
        self.nr_processors = resources.nr_processors 
        self.processor_family = resources.processor_family
        self.processor_manufacturer = resources.processor_manufacturer
        self.processor_version = resources.processor_version
        self.processor_features = resources.processor_features
        self.memory_type = resources.memory_type
        self.memory_freq = resources.memory_freq
        self.memory_nr_channels = resources.memory_nr_channels
        self.memory_size = resources.memory_size
        self.memory_hugepage_sz = resources.memory_hugepage_sz
        self.hypervisor = Hypervisor()
        self.hypervisor.assign(resources.hypervisor)
        self.os = OpSys()
        self.os.assign(resources.os)
        self.nodes = dict()
        for node_k, node_v in resources.nodes.iteritems():
            self.nodes[node_k] = Node()
            self.nodes[node_k].assign(node_v)
        return
    
    def _get_cores_consumption_warnings(self):
        """Returns list of warning strings in case warnings are generated. 
        In case no warnings are generated the return value will be an empty list"""
        warnings = list()
        #Get the cores consumption
        (return_status, code) = get_ssh_connection(self.machine, self.user, self.password)
        if not return_status:
            return (return_status, code)
        ssh_conn = code
        command = 'mpstat -P ALL 1 1 | grep Average | egrep -v CPU\|all'
        (_, stdout, stderr) = ssh_conn.exec_command(command)
        error = stderr.read()
        if len(error) > 0:
            return (False, error)
    
        self.cores_consumption = dict()
        for line in stdout.readlines():
            cpu_usage_split = re.split('\t| *', line.rstrip('\n'))
            usage = 100 *(1 - float(cpu_usage_split[10]))
            if usage > 0:
                self.cores_consumption[int(cpu_usage_split[1])] = usage 
        ssh_conn.close()   
        #Check if any core marked as available in the nodes has cpu_usage > 0
        for _, node_v in self.nodes.iteritems():
            cores = node_v.processor.eligible_cores
            for cpu in cores:
                if len(cpu) > 1:
                    for core in cpu:
                        if core in self.cores_consumption:
                            warnings.append('Warning: Core '+str(core)+' is supposed to be idle but it is consuming '+str(self.cores_consumption[core])+'%')
                else:
                    if cpu in self.cores_consumption:
                        warnings.append('Warning: Core '+str(core)+' is supposed to be idle but it is consuming '+str(self.cores_consumption[cpu])+'%')
        
        return warnings
    
    def reserved_to_text(self):
        text = str()
        for VNFC_name, VNFC_reserved in self.reserved.iteritems():
            text += '    VNFC: '+str(VNFC_name)+'\n'
            text += VNFC_reserved.to_text()
                    
        return text
    
    def obtain_usage(self):
        resp = dict()
        #Iterate through nodes to get cores, eligible cores, memory and physical ports (save ports usage for next section)
        nodes = dict()
        ports_usage = dict()
        hugepage_size = dict()
        for node_k, node_v in self.nodes.iteritems():
            node = dict()
            ports_usage[node_k] = dict()
            eligible_cores = list()
            for pair in node_v.processor.eligible_cores:
                if isinstance(pair, list):
                    for element in pair:
                        eligible_cores.append(element)
                else:
                    eligible_cores.append(pair)
            node['cpus'] = {'cores':node_v.processor.cores,'eligible_cores':eligible_cores}
            node['memory'] = {'size':str(node_v.memory.node_size/(1024*1024*1024))+'GB','eligible':str(node_v.memory.eligible_memory/(1024*1024*1024))+'GB'}
            hugepage_size[node_k] = node_v.memory.hugepage_sz
            
            ports = dict()
            for nic in node_v.nic_list:
                for port in nic.ports.itervalues():
                    if port.enabled and not port.virtual: 
                        ports[port.name] = {'speed':str(port.speed/1000000000)+'G'}
#                         print '*************** ',port.name,'speed',port.speed 
                        ports_usage[node_k][port.name] = 100 - int(100*float(port.available_bw)/float(port.speed))
            node['ports'] = ports
            nodes[node_k] = node
        resp['RAD'] = nodes
        
        #Iterate through reserved section to get used cores, used memory and port usage
        cores = dict()
        memory = dict()
        #reserved_cores = list
        for node_k in self.nodes.iterkeys():
            if not node_k in cores:
                cores[node_k] = list()
                memory[node_k] = 0
            for _, reserved in self.reserved.iteritems():
                if node_k in reserved.node_reserved_resources:
                    node_v = reserved.node_reserved_resources[node_k]
                    cores[node_k].extend(node_v.reserved_cores)
                    memory[node_k] += node_v.reserved_hugepage_nr * hugepage_size[node_k]
                            
        occupation = dict()       
        for node_k in self.nodes.iterkeys():
            ports = dict()
            for name, usage in ports_usage[node_k].iteritems():
                ports[name] = {'occupied':str(usage)+'%'}
#             print '****************cores',cores
#             print '****************memory',memory
            occupation[node_k] = {'cores':cores[node_k],'memory':str(memory[node_k]/(1024*1024*1024))+'GB','ports':ports}
        resp['occupation'] = occupation
        
        return resp            
    
class RADreservedResources():
    def __init__(self):
        self.node_reserved_resources = dict()      #dict. keys are the RAD nodes id, values are NodeReservedResources
        self.mgmt_interface_pci = None             #pci in the VNF for the management interface
        self.image = None                          #Path in remote machine of the VNFC image
    
    def update(self,reserved):
        self.image = reserved.image
        self.mgmt_interface_pci = reserved.mgmt_interface_pci
        for k,v in reserved.node_reserved_resources.iteritems():
            if k in self.node_reserved_resources.keys():
                return (False, 'Duplicated node entry '+str(k)+' in reserved resources')
            self.node_reserved_resources[k]=v
            
        return (True, "")
    
    def to_text(self):
        text = '        image: '+str(self.image)+'\n'
        for node_id, node_reserved in self.node_reserved_resources.iteritems():
            text += '        Node ID: '+str(node_id)+'\n'
            text += node_reserved.to_text()
        return text

class NodeReservedResources():
    def __init__(self):
    #     reserved_shared_cores = None      #list. List of all cores that the VNFC needs in shared mode  #TODO Not used
    #     reserved_memory = None            #Integer. Amount of KiB needed by the VNFC #TODO. Not used since hugepages are used
        self.reserved_cores = list()             #list. List of all cores that the VNFC uses
        self.reserved_hugepage_nr = 0            #Integer. Number of hugepages needed by the VNFC 
        self.reserved_ports = dict()             #dict. The key is the physical port pci and the value the VNFC port description
        self.vlan_tags = dict()
        self.cpu_pinning = None
    
    def to_text(self):
        text = '            cores: '+str(self.reserved_cores)+'\n'
        text += '            cpu_pinning: '+str(self.cpu_pinning)+'\n'
        text += '            hugepages_nr: '+str(self.reserved_hugepage_nr)+'\n'
        for port_pci, port_description in self.reserved_ports.iteritems():
            text += '            port: '+str(port_pci)+'\n'
            text += port_description.to_text()
        return text
    
#     def update(self,reserved):
#         self.reserved_cores = list(reserved.reserved_cores)
#         self.reserved_hugepage_nr = reserved.reserved_hugepage_nr
#         self.reserved_ports = dict(reserved.reserved_ports)
#         self.cpu_pinning = list(reserved.cpu_pinning)
    
    
        

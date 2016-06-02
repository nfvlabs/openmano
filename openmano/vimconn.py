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
vimconn implement an Abstract class for the vim connector plugins
 with the definition of the method to be implemented.
'''
__author__="Alfonso Tierno"
__date__ ="$16-oct-2015 11:09:29$"

import logging

#Error variables 
HTTP_Bad_Request = 400
HTTP_Unauthorized = 401 
HTTP_Not_Found = 404 
HTTP_Method_Not_Allowed = 405 
HTTP_Request_Timeout = 408
HTTP_Conflict = 409
HTTP_Not_Implemented = 501
HTTP_Service_Unavailable = 503 
HTTP_Internal_Server_Error = 500 

class vimconnException(Exception):
    '''Common and base class Exception for all vimconnector exceptions'''
    def __init__(self, message, http_code=HTTP_Bad_Request):
        Exception.__init__(self, message)
        self.http_code = http_code

class vimconnConnectionException(vimconnException):
    '''Connectivity error with the VIM'''
    def __init__(self, message, http_code=HTTP_Service_Unavailable):
        vimconnException.__init__(self, message, http_code)
    
class vimconnUnexpectedResponse(vimconnException):
    '''Get an wrong response from VIM'''
    def __init__(self, message, http_code=HTTP_Service_Unavailable):
        vimconnException.__init__(self, message, http_code)

class vimconnAuthException(vimconnException):
    '''Invalid credentials or authorization to perform this action over the VIM'''
    def __init__(self, message, http_code=HTTP_Unauthorized):
        vimconnException.__init__(self, message, http_code)

class vimconnNotFoundException(vimconnException):
    '''The item is not found at VIM'''
    def __init__(self, message, http_code=HTTP_Not_Found):
        vimconnException.__init__(self, message, http_code)

class vimconnConflictException(vimconnException):
    '''There is a conflict, e.g. more item found than one'''
    def __init__(self, message, http_code=HTTP_Conflict):
        vimconnException.__init__(self, message, http_code)

class vimconnNotImplemented(vimconnException):
    '''The method is not implemented by the connected'''
    def __init__(self, message, http_code=HTTP_Not_Implemented):
        vimconnException.__init__(self, message, http_code)

class vimconnector():
    '''Abstract base class for all the VIM connector plugins
    These plugins must implement a vimconnector class derived from this 
    and all these methods
    ''' 
    def __init__(self, uuid, name, tenant_id, tenant_name, url, url_admin=None, user=None, passwd=None, log_level="ERROR", config={}):
        self.id        = uuid
        self.name      = name
        self.url       = url
        self.url_admin = url_admin
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.user      = user
        self.passwd    = passwd
        self.config    = config
        self.logger = logging.getLogger('mano.vim')
        self.logger.setLevel( getattr(logging, log_level) )
        if not self.url_admin:  #try to use normal url 
            self.url_admin = self.url
    
    def __getitem__(self,index):
        if index=='tenant_id':
            return self.tenant_id
        if index=='tenant_name':
            return self.tenant_name
        elif index=='id':
            return self.id
        elif index=='name':
            return self.name
        elif index=='user':
            return self.user
        elif index=='passwd':
            return self.passwd
        elif index=='url':
            return self.url
        elif index=='url_admin':
            return self.url_admin
        elif index=="config":
            return self.config
        else:
            raise KeyError("Invalid key '%s'" %str(index))
        
    def __setitem__(self,index, value):
        if index=='tenant_id':
            self.tenant_id = value
        if index=='tenant_name':
            self.tenant_name = value
        elif index=='id':
            self.id = value
        elif index=='name':
            self.name = value
        elif index=='user':
            self.user = value
        elif index=='passwd':
            self.passwd = value
        elif index=='url':
            self.url = value
        elif index=='url_admin':
            self.url_admin = value
        else:
            raise KeyError("Invalid key '%s'" %str(index))
        
    def new_tenant(self,tenant_name,tenant_description):
        '''Adds a new tenant to VIM with this name and description,
        returns the tenant identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def delete_tenant(self,tenant_id,):
        '''Delete a tenant from VIM'''
        '''Returns the tenant identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_tenant_list(self, filter_dict={}):
        '''Obtain tenants of VIM
        filter_dict can contain the following keys:
            name: filter by tenant name
            id: filter by tenant uuid/id
            <other VIM specific>
        Returns the tenant list of dictionaries: 
            [{'name':'<name>, 'id':'<id>, ...}, ...]
        '''
        raise vimconnNotImplemented( "Should have implemented this" )

    def new_network(self,net_name, net_type, shared=False):
        '''Adds a tenant network to VIM
            net_type can be 'bridge','data'.'ptp'.  TODO: this need to be revised 
            shared is a boolean
        Returns the network identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_network_list(self, filter_dict={}):
        '''Obtain tenant networks of VIM
        Filter_dict can be:
            name: network name
            id: network uuid
            shared: boolean
            tenant_id: tenant
            admin_state_up: boolean
            status: 'ACTIVE'
        Returns the network list of dictionaries:
            [{<the fields at Filter_dict plus some VIM specific>}, ...]
            List can be empty
        '''
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_network(self, net_id):
        '''Obtain network details of net_id VIM network'
           Return a dict with  the fields at filter_dict (see get_network_list) plus some VIM specific>}, ...]'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def delete_network(self, net_id):
        '''Deletes a tenant network from VIM, provide the network id.
        Returns the network identifier or raise an exception'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def refresh_nets_status(self, net_list):
        '''Get the status of the networks
           Params: the list of network identifiers
           Returns a dictionary with:
                net_id:         #VIM id of this network
                    status:     #Mandatory. Text with one of:
                                #  DELETED (not found at vim)
                                #  VIM_ERROR (Cannot connect to VIM, VIM response error, ...) 
                                #  OTHER (Vim reported other status not understood)
                                #  ERROR (VIM indicates an ERROR status)
                                #  ACTIVE, INACTIVE, DOWN (admin down), 
                                #  BUILD (on building process)
                                #
                    error_msg:  #Text with VIM error message, if any. Or the VIM connection ERROR 
                    vim_info:   #Text with plain information obtained from vim (yaml.safe_dump)

        '''
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_flavor(self, flavor_id):
        '''Obtain flavor details from the  VIM
            Returns the flavor dict details {'id':<>, 'name':<>, other vim specific } #TODO to concrete
        '''
        raise vimconnNotImplemented( "Should have implemented this" )
        
    def new_flavor(self, flavor_data):
        '''Adds a tenant flavor to VIM
            flavor_data contains a dictionary with information, keys:
                name: flavor name
                ram: memory (cloud type) in MBytes
                vpcus: cpus (cloud type)
                extended: EPA parameters
                  - numas: #items requested in same NUMA
                        memory: number of 1G huge pages memory
                        paired-threads|cores|threads: number of paired hyperthreads, complete cores OR individual threads
                        interfaces: # passthrough(PT) or SRIOV interfaces attached to this numa
                          - name: interface name
                            dedicated: yes|no|yes:sriov;  for PT, SRIOV or only one SRIOV for the physical NIC
                            bandwidth: X Gbps; requested guarantee bandwidth
                            vpci: requested virtual PCI address   
                disk: disk size
                is_public:
                       
                
                    
                 #TODO to concrete
        Returns the flavor identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def delete_flavor(self, flavor_id):
        '''Deletes a tenant flavor from VIM identify by its id
        Returns the used id or raise an exception'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def new_image(self,image_dict):
        '''
        Adds a tenant image to VIM
        Returns:
            200, image-id        if the image is created
            <0, message          if there is an error
        '''
        raise vimconnNotImplemented( "Should have implemented this" )

    def delete_image(self, image_id):
        '''Deletes a tenant image from VIM'''
        '''Returns the HTTP response code and a message indicating details of the success or fail'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_image_id_from_path(self, path):
        '''Get the image id from image path in the VIM database'''
        '''Returns:
             0,"Image not found"   if there are no images with that path
             1,image-id            if there is one image with that path
             <0,message            if there was an error (Image not found, error contacting VIM, more than 1 image with that path, etc.) 
        '''
        raise vimconnNotImplemented( "Should have implemented this" )
        
    def new_vminstance(self,name,description,start,image_id,flavor_id,net_list):
        '''Adds a VM instance to VIM
        Params:
            start: indicates if VM must start or boot in pause mode. Ignored
            image_id,flavor_id: image and flavor uuid
            net_list: list of interfaces, each one is a dictionary with:
                name:
                net_id: network uuid to connect
                vpci: virtual vcpi to assign
                model: interface model, virtio, e2000, ...
                mac_address: 
                use: 'data', 'bridge',  'mgmt'
                type: 'virtual', 'PF', 'VF', 'VFnotShared'
                vim_id: filled/added by this function
                #TODO ip, security groups
        Returns >=0, the instance identifier
                <0, error_text
        '''
        raise vimconnNotImplemented( "Should have implemented this" )
        
    def get_vminstance(self,vm_id):
        '''Returns the VM instance information from VIM'''
        raise vimconnNotImplemented( "Should have implemented this" )
        
    def delete_vminstance(self, vm_id):
        '''Removes a VM instance from VIM'''
        '''Returns the instance identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def refresh_vms_status(self, vm_list):
        '''Get the status of the virtual machines and their interfaces/ports
           Params: the list of VM identifiers
           Returns a dictionary with:
                vm_id:          #VIM id of this Virtual Machine
                    status:     #Mandatory. Text with one of:
                                #  DELETED (not found at vim)
                                #  VIM_ERROR (Cannot connect to VIM, VIM response error, ...) 
                                #  OTHER (Vim reported other status not understood)
                                #  ERROR (VIM indicates an ERROR status)
                                #  ACTIVE, PAUSED, SUSPENDED, INACTIVE (not running), 
                                #  CREATING (on building process), ERROR
                                #  ACTIVE:NoMgmtIP (Active but any of its interface has an IP address
                                #
                    error_msg:  #Text with VIM error message, if any. Or the VIM connection ERROR 
                    vim_info:   #Text with plain information obtained from vim (yaml.safe_dump)
                    interfaces:
                     -  vim_info:         #Text with plain information obtained from vim (yaml.safe_dump)
                        mac_address:      #Text format XX:XX:XX:XX:XX:XX
                        vim_net_id:       #network id where this interface is connected
                        vim_interface_id: #interface/port VIM id
                        ip_address:       #null, or text with IPv4, IPv6 address
        '''
        raise vimconnNotImplemented( "Should have implemented this" )
    
    def action_vminstance(self, vm_id, action_dict):
        '''Send and action over a VM instance from VIM
        Returns the vm_id if the action was successfully sent to the VIM'''
        raise vimconnNotImplemented( "Should have implemented this" )
    
    def get_vminstance_console(self,vm_id, console_type="vnc"):
        '''
        Get a console for the virtual machine
        Params:
            vm_id: uuid of the VM
            console_type, can be:
                "novnc" (by default), "xvpvnc" for VNC types, 
                "rdp-html5" for RDP types, "spice-html5" for SPICE types
        Returns dict with the console parameters:
                protocol: ssh, ftp, http, https, ...
                server:   usually ip address 
                port:     the http, ssh, ... port 
                suffix:   extra text, e.g. the http path and query string   
        '''
        raise vimconnNotImplemented( "Should have implemented this" )
        
#NOT USED METHODS in current version        

    def host_vim2gui(self, host, server_dict):
        '''Transform host dictionary from VIM format to GUI format,
        and append to the server_dict
        '''
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_hosts_info(self):
        '''Get the information of deployed hosts
        Returns the hosts content'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_hosts(self, vim_tenant):
        '''Get the hosts and deployed instances
        Returns the hosts content'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def get_processor_rankings(self):
        '''Get the processor rankings in the VIM database'''
        raise vimconnNotImplemented( "Should have implemented this" )
    
    def new_host(self, host_data):
        '''Adds a new host to VIM'''
        '''Returns status code of the VIM response'''
        raise vimconnNotImplemented( "Should have implemented this" )
    
    def new_external_port(self, port_data):
        '''Adds a external port to VIM'''
        '''Returns the port identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )
        
    def new_external_network(self,net_name,net_type):
        '''Adds a external network to VIM (shared)'''
        '''Returns the network identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def connect_port_network(self, port_id, network_id, admin=False):
        '''Connects a external port to a network'''
        '''Returns status code of the VIM response'''
        raise vimconnNotImplemented( "Should have implemented this" )

    def new_vminstancefromJSON(self, vm_data):
        '''Adds a VM instance to VIM'''
        '''Returns the instance identifier'''
        raise vimconnNotImplemented( "Should have implemented this" )


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

#Error variables 
HTTP_Bad_Request = 400
HTTP_Unauthorized = 401 
HTTP_Not_Found = 404 
HTTP_Method_Not_Allowed = 405 
HTTP_Request_Timeout = 408
HTTP_Conflict = 409
HTTP_Service_Unavailable = 503 
HTTP_Internal_Server_Error = 500 


class vimconnector():
    '''Abstract base class for all the VIM connector plugins
    These plugins must implement a vimconnector class deribed from this 
    and all these methods
    ''' 
    def __init__(self, uuid, name, tenant, url, url_admin=None, user=None, passwd=None,debug=True,config={}):
        self.id        = uuid
        self.name      = name
        self.url       = url
        self.url_admin = url_admin
        self.tenant    = tenant
        self.user      = user
        self.passwd    = passwd
        self.config    = config
        self.debug     = debug
    
    def __getitem__(self,index):
        if index=='tenant':
            return self.tenant
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
        if index=='tenant':
            self.tenant = value
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

    def new_host(self, host_data):
        '''Adds a new host to VIM'''
        '''Returns status code of the VIM response'''
        raise NotImplementedError( "Should have implemented this" )
    
    def new_external_port(self, port_data):
        '''Adds a external port to VIM'''
        '''Returns the port identifier'''
        raise NotImplementedError( "Should have implemented this" )
        
    def new_external_network(self,net_name,net_type):
        '''Adds a external network to VIM (shared)'''
        '''Returns the network identifier'''
        raise NotImplementedError( "Should have implemented this" )

    def connect_port_network(self, port_id, network_id, admin=False):
        '''Connects a external port to a network'''
        '''Returns status code of the VIM response'''
        raise NotImplementedError( "Should have implemented this" )
        
    def new_tenant(self,tenant_name,tenant_description):
        '''Adds a new tenant to VIM'''
        '''Returns the tenant identifier'''
        raise NotImplementedError( "Should have implemented this" )

    def delete_tenant(self,tenant_id,):
        '''Delete a tenant from VIM'''
        '''Returns the tenant identifier'''
        raise NotImplementedError( "Should have implemented this" )

    def new_tenant_network(self,net_name,net_type):
        '''Adds a tenant network to VIM'''
        '''Returns the network identifier'''
        raise NotImplementedError( "Should have implemented this" )

    def get_network_list(self, filter_dict={}):
        '''Obtain tenant networks of VIM
        Filter_dict can be:
            name: network name
            id: network uuid
            shared: boolean
            tenant_id: tenant
            admin_state_up: boolean
            status: 'ACTIVE'
        Returns the network list of dictionaries
        '''
        raise NotImplementedError( "Should have implemented this" )

    def get_tenant_network(self, net_id, tenant_id=None):
        '''Obtain tenant networks of VIM'''
        '''Returns the network information from a network id'''
        raise NotImplementedError( "Should have implemented this" )

    def delete_tenant_network(self, net_id):
        '''Deletes a tenant network from VIM'''
        '''Returns the network identifier'''
        raise NotImplementedError( "Should have implemented this" )

    def refresh_tenant_network(self, net_id):
        '''Refreshes the status of the tenant network'''
        '''Returns: 0 if no error,
                    <0 if error'''
        raise NotImplementedError( "Should have implemented this" )

    def get_tenant_flavor(self, flavor_id):
        '''Obtain flavor details from the  VIM
            Returns the flavor dict details
        '''
        raise NotImplementedError( "Should have implemented this" )
        
    def new_tenant_flavor(self, flavor_data):
        '''Adds a tenant flavor to VIM'''
        '''Returns the flavor identifier'''
        raise NotImplementedError( "Should have implemented this" )

    def delete_tenant_flavor(self,flavor_id):
        '''Deletes a tenant flavor from VIM'''
        '''Returns the HTTP response code and a message indicating details of the success or fail'''
        raise NotImplementedError( "Should have implemented this" )

    def new_tenant_image(self,image_dict):
        '''
        Adds a tenant image to VIM
        Returns:
            200, image-id        if the image is created
            <0, message          if there is an error
        '''
        raise NotImplementedError( "Should have implemented this" )

    def delete_tenant_image(self, image_id):
        '''Deletes a tenant image from VIM'''
        '''Returns the HTTP response code and a message indicating details of the success or fail'''
        raise NotImplementedError( "Should have implemented this" )
        
    def new_tenant_vminstancefromJSON(self, vm_data):
        '''Adds a VM instance to VIM'''
        '''Returns the instance identifier'''
        raise NotImplementedError( "Should have implemented this" )

    def new_tenant_vminstance(self,name,description,start,image_id,flavor_id,net_list):
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
        raise NotImplementedError( "Should have implemented this" )
        
    def get_tenant_vminstance(self,vm_id):
        '''Returns the VM instance information from VIM'''
        raise NotImplementedError( "Should have implemented this" )
        
    def delete_tenant_vminstance(self, vm_id):
        '''Removes a VM instance from VIM'''
        '''Returns the instance identifier'''
        raise NotImplementedError( "Should have implemented this" )

    def refresh_tenant_vms_and_nets(self, vmDict, netDict):
        '''Refreshes the status of the dictionaries of VM instances and nets passed as arguments. It modifies the dictionaries'''
        '''Returns:
            - result: 0 if all elements could be refreshed (even if its status didn't change)
                      n>0, the number of elements that couldn't be refreshed,
                      <0 if error (foreseen)
            - error_msg: text with reference to possible errors
        '''
        raise NotImplementedError( "Should have implemented this" )
    
    def action_tenant_vminstance(self, vm_id, action_dict):
        '''Send and action over a VM instance from VIM'''
        '''Returns the status'''
        raise NotImplementedError( "Should have implemented this" )
        
    def host_vim2gui(self, host, server_dict):
        '''Transform host dictionary from VIM format to GUI format,
        and append to the server_dict
        '''
        raise NotImplementedError( "Should have implemented this" )

    def get_hosts_info(self):
        '''Get the information of deployed hosts
        Returns the hosts content'''
        raise NotImplementedError( "Should have implemented this" )

    def get_hosts(self, vim_tenant):
        '''Get the hosts and deployed instances
        Returns the hosts content'''
        raise NotImplementedError( "Should have implemented this" )

    def get_processor_rankings(self):
        '''Get the processor rankings in the VIM database'''
        raise NotImplementedError( "Should have implemented this" )
    
    def get_image_id_from_path(self, path):
        '''Get the image id from image path in the VIM database'''
        '''Returns:
             0,"Image not found"   if there are no images with that path
             1,image-id            if there is one image with that path
             <0,message            if there was an error (Image not found, error contacting VIM, more than 1 image with that path, etc.) 
        '''
        raise NotImplementedError( "Should have implemented this" )

        


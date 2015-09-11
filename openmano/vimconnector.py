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
vimconnector implements all the methods to interact with openvim using the openvim API.

For interacting with Openstack refer to osconnector.
'''
__author__="Alfonso Tierno, Gerardo Garcia"
__date__ ="$26-aug-2014 11:09:29$"

import requests
import json
from utils import auxiliary_functions as af
import openmano_schemas
from nfvo_db import HTTP_Bad_Request, HTTP_Internal_Server_Error, HTTP_Not_Found, HTTP_Unauthorized, HTTP_Conflict

#TODO: Decide if it makes sense to have the methods outside the class as static generic methods
class vimconnector():
    def __init__(self, uuid, name, tenant, url, url_admin=None, user=None, passwd=None,config={}):
        self.id        = uuid
        self.name      = name
        self.url       = url
        self.url_admin = url_admin
        self.tenant    = tenant
        self.user      = user
        self.passwd    = passwd
        self.config    = config
    
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
        print "VIMConnector: Adding a new host"
        headers_req = {'content-type': 'application/json'}
        payload_req = host_data
        try:
            vim_response = requests.post(self.url_admin+'/hosts', headers = headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_host Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
        #print vim_response.json()
        #print json.dumps(vim_response.json(), indent=4)
            res,http_content = af.format_in(vim_response, openmano_schemas.new_host_response_schema)
            #print http_content
            if res :
                r = af.remove_extra_items(http_content, openmano_schemas.new_host_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                host_id = http_content['host']['id']
                #print "Host id: ",host_id
                return vim_response.status_code,host_id
            else: return -HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new host. HTTP Response: %d. Error: %s' % (self.url_admin, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
    
    def new_external_port(self, port_data):
        '''Adds a external port to VIM'''
        '''Returns the port identifier'''
        print "VIMConnector: Adding a new external port"
        headers_req = {'content-type': 'application/json'}
        payload_req = port_data
        try:
            vim_response = requests.post(self.url_admin+'/ports', headers = headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_external_port Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
        #print vim_response.json()
        #print json.dumps(vim_response.json(), indent=4)
            res, http_content = af.format_in(vim_response, openmano_schemas.new_port_response_schema)
        #print http_content
            if res:
                r = af.remove_extra_items(http_content, openmano_schemas.new_port_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                port_id = http_content['port']['id']
                print "Port id: ",port_id
                return vim_response.status_code,port_id
            else: return -HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new external port. HTTP Response: %d. Error: %s' % (self.url_admin, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        
    def new_external_network(self,net_name,net_type):
        '''Adds a external network to VIM (shared)'''
        '''Returns the network identifier'''
        print "VIMConnector: Adding external shared network to VIM (type " + net_type + "): "+ net_name
        
        headers_req = {'content-type': 'application/json'}
        payload_req = '{"network":{"name": "' + net_name + '","shared":true,"type": "' + net_type + '"}}'
        try:
            vim_response = requests.post(self.url+'/networks', headers = headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_external_network Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = af.format_in(vim_response, openmano_schemas.new_network_response_schema)
            #print http_content
            if res:
                r = af.remove_extra_items(http_content, openmano_schemas.new_network_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                network_id = http_content['network']['id']
                print "Network id: ",network_id
                return vim_response.status_code,network_id
            else: return -HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new external network. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        
    def connect_port_network(self, port_id, network_id, admin=False):
        '''Connects a external port to a network'''
        '''Returns status code of the VIM response'''
        print "VIMConnector: Connecting external port to network"
        
        headers_req = {'content-type': 'application/json'}
        payload_req = '{"port":{"network_id":"' + network_id + '"}}'
        if admin:
            if self.url_admin==None:
                return -HTTP_Unauthorized, "datacenter cannot contain  admin URL"
            url= self.url_admin
        else:
            url= self.url
        try:
            vim_response = requests.put(url +'/ports/'+port_id, headers = headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "connect_port_network Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = af.format_in(vim_response, openmano_schemas.new_port_response_schema)
            #print http_content
            if res:
                r = af.remove_extra_items(http_content, openmano_schemas.new_port_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                port_id = http_content['port']['id']
                print "Port id: ",port_id
                return vim_response.status_code,port_id
            else: return -HTTP_Bad_Request,http_content
        else:
            print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to connect external port to network. HTTP Response: %d. Error: %s' % (self.url_admin, vim_response.status_code, jsonerror)
            print text
            return -vim_response.status_code,text
        
    def new_tenant(self,tenant_name,tenant_description):
        '''Adds a new tenant to VIM'''
        '''Returns the tenant identifier'''
        print "VIMConnector: Adding a new tenant to VIM"
        headers_req = {'content-type': 'application/json'}
        payload_dict = {"tenant": {"name":tenant_name,"description": tenant_description, "enabled": True}}
        payload_req = json.dumps(payload_dict)
        #print payload_req

        try:
            vim_response = requests.post(self.url+'/tenants', headers = headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_tenant Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        #print vim_response
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = af.format_in(vim_response, openmano_schemas.new_tenant_response_schema)
            #print http_content
            if res:
                r = af.remove_extra_items(http_content, openmano_schemas.new_tenant_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                tenant_id = http_content['tenant']['id']
                #print "Tenant id: ",tenant_id
                return vim_response.status_code,tenant_id
            else: return -HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new tenant. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def delete_tenant(self,tenant_id,):
        '''Delete a tenant from VIM'''
        '''Returns the tenant identifier'''
        print "VIMConnector: Deleting  a  tenant from VIM"
        headers_req = {'content-type': 'application/json'}
        try:
            vim_response = requests.delete(self.url+'/tenants/'+tenant_id, headers = headers_req)
        except requests.exceptions.RequestException, e:
            print "delete_tenant Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        #print vim_response
        if vim_response.status_code == 200:
            return vim_response.status_code,tenant_id
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to delete tenant. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def new_tenant_network(self,net_name,net_type):
        '''Adds a tenant network to VIM'''
        '''Returns the network identifier'''
        if net_type=="bridge":
            net_type="bridge_data"
        print "VIMConnector: Adding a new tenant network to VIM (tenant: " + self.tenant + ", type: " + net_type + "): "+ net_name

        headers_req = {'content-type': 'application/json'}
        payload_req = '{"network":{"name": "' + net_name + '", "type": "' + net_type + '","self.tenant":"' + self.tenant + '"}}'
        try:
            vim_response = requests.post(self.url+'/networks', headers = headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_tenant_network Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = af.format_in(vim_response, openmano_schemas.new_network_response_schema)
            #print http_content
            if res:
                r = af.remove_extra_items(http_content, openmano_schemas.new_network_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                network_id = http_content['network']['id']
                print "Tenant Network id: ",network_id
                return vim_response.status_code,network_id
            else: return -HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new tenant network. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

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
        print "VIMConnector.get_network_list: Getting tenant network from VIM (filter: " + str(filter_dict) + "): "
        filterquery=[]
        filterquery_text=''
        for k,v in filter_dict.iteritems():
            filterquery.append(str(k)+'='+str(v))
        if len(filterquery)>0:
            filterquery_text='?'+ '&'.join(filterquery)
        headers_req = {'content-type': 'application/json'}
        try:
            print self.url+'/networks'+filterquery_text
            vim_response = requests.get(self.url+'/networks'+filterquery_text, headers = headers_req)
        except requests.exceptions.RequestException, e:
            print "get_network_list Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            #TODO: parse input datares,http_content = af.format_in(vim_response, openmano_schemas.new_network_response_schema)
            #print http_content
            return vim_response.status_code, vim_response.json()["networks"]
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to get network list. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def get_tenant_network(self, net_id, tenant_id=None):
        '''Obtain tenant networks of VIM'''
        '''Returns the network information from a network id'''
        if self.debug:
            print "VIMconnector.get_tenant_network(): Getting tenant network %s from VIM" % net_id
        filter_dict={"id": net_id}
        if tenant_id:
            filter_dict["tenant_id"] = tenant_id
        r, net_list = self.get_network_list(filter_dict)
        if r<0:
            return r, net_list
        if len(net_list)==0:
            return -HTTP_Not_Found, "Network '%s' not found" % net_id
        elif len(net_list)>1:
            return -HTTP_Conflict, "Found more than one network with this criteria"
        return 1, net_list[0]

    def delete_tenant_network(self, net_id):
        '''Deletes a tenant network from VIM'''
        '''Returns the network identifier'''
        print "VIMConnector: Deleting a new tenant network from VIM tenant: " + self.tenant + ", id: " + net_id

        headers_req = {'content-type': 'application/json'}
        try:
            vim_response = requests.delete(self.url+'/networks/'+net_id, headers=headers_req)
        except requests.exceptions.RequestException, e:
            print "delete_tenant_network Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])

        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
                return vim_response.status_code,net_id
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to delete tenant network. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def refresh_tenant_network(self, net_id):
        '''Refreshes the status of the tenant network'''
        '''Returns: 0 if no error,
                    <0 if error'''
        return 0
    
    def new_tenant_flavor(self, flavor_data):
        '''Adds a tenant flavor to VIM'''
        '''Returns the flavor identifier'''
        print "VIMConnector: Adding a new flavor to VIM"
        #print "VIM URL:",self.url
        #print "Tenant id:",self.tenant
        #print "Flavor:",flavor_data
        headers_req = {'content-type': 'application/json'}
        payload_req = json.dumps({'flavor': flavor_data})
        try:
            vim_response = requests.post(self.url+'/'+self.tenant+'/flavors', headers = headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_tenant_flavor Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = af.format_in(vim_response, openmano_schemas.new_flavor_response_schema)
            #print http_content
            if res:
                r = af.remove_extra_items(http_content, openmano_schemas.new_flavor_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                flavor_id = http_content['flavor']['id']
                print "Flavor id: ",flavor_id
                return vim_response.status_code,flavor_id
            else: return -HTTP_Bad_Request,http_content

        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new flavor. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def delete_tenant_flavor(self,flavor_id):
        '''Deletes a tenant flavor from VIM'''
        '''Returns the HTTP response code and a message indicating details of the success or fail'''
        print "VIMConnector: Deleting a flavor from VIM"
        print "VIM URL:",self.url
        print "Tenant id:",self.tenant
        print "Flavor id:",flavor_id
        #headers_req = {'content-type': 'application/json'}
        #payload_req = flavor_data
        try:
            vim_response = requests.delete(self.url+'/'+self.tenant+'/flavors/'+flavor_id)
        except requests.exceptions.RequestException, e:
            print "delete_tenant_flavor Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        print vim_response.status_code
        if vim_response.status_code == 200:
            result = vim_response.json()["result"]
            return 200,result
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to delete flavor. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def new_tenant_image(self,image_dict):
        '''
        Adds a tenant image to VIM
        Returns:
            200, image-id        if the image is created
            <0, message          if there is an error
        '''
        print "VIMConnector: Adding a new image to VIM", image_dict['location']
        headers_req = {'content-type': 'application/json'}
        new_image_dict={'name': image_dict['name']}
        if 'description' in image_dict and image_dict['description'] != None:
            new_image_dict['description'] = image_dict['description']
        if 'metadata' in image_dict and image_dict['metadata'] != None:
            new_image_dict['metadata'] = image_dict['metadata']
        if 'location' in image_dict and image_dict['location'] != None:
            new_image_dict['path'] = image_dict['location']
        payload_req = json.dumps({"image":new_image_dict})
        url=self.url + '/' + self.tenant + '/images'
        try:
            vim_response = requests.post(url, headers = headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_tenant_image Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = af.format_in(vim_response, openmano_schemas.new_image_response_schema)
            #print http_content
            if res:
                r = af.remove_extra_items(http_content, openmano_schemas.new_image_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                image_id = http_content['image']['id']
                print "Image id: ",image_id
                return vim_response.status_code,image_id
            else: return -HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new image. HTTP Response: %d. Error: %s' % (url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def delete_tenant_image(self, image_id):
        '''Deletes a tenant image from VIM'''
        '''Returns the HTTP response code and a message indicating details of the success or fail'''
        print "VIMConnector: Deleting an image from VIM"
        #headers_req = {'content-type': 'application/json'}
        #payload_req = flavor_data
        url=self.url + '/'+ self.tenant +'/images/'+image_id
        try:
            vim_response = requests.delete(url)
        except requests.exceptions.RequestException, e:
            print "delete_tenant_image Exception url '%s': " % url, e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        print vim_response.status_code
        if vim_response.status_code == 200:
            result = vim_response.json()["result"]
            return 200,result
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to delete image. HTTP Response: %d. Error: %s' % (url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        
    def new_tenant_vminstancefromJSON(self, vm_data):
        '''Adds a VM instance to VIM'''
        '''Returns the instance identifier'''
        print "VIMConnector: Adding a new VM instance from JSON to VIM"
        headers_req = {'content-type': 'application/json'}
        payload_req = vm_data
        try:
            vim_response = requests.post(self.url+'/'+self.tenant+'/servers', headers = headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_tenant_vminstancefromJSON Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = af.format_in(vim_response, openmano_schemas.new_image_response_schema)
            #print http_content
            if res:
                r = af.remove_extra_items(http_content, openmano_schemas.new_image_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                vminstance_id = http_content['server']['id']
                print "Tenant image id: ",vminstance_id
                return vim_response.status_code,vminstance_id
            else: return -HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new vm instance. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

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
                type: 'virtual', 'PF', 'VF', 'VF not shared'
                vim_id: filled/added by this function
                #TODO ip, security groups
        Returns >=0, the instance identifier
                <0, error_text
        '''
        print "VIMConnector: Adding a new VM instance to VIM"
        headers_req = {'content-type': 'application/json'}
        
#         net_list = []
#         for k,v in net_dict.items():
#             print k,v
#             net_list.append('{"name":"' + k + '", "uuid":"' + v + '"}')
#         net_list_string = ', '.join(net_list) 
        virtio_net_list=[]
        for net in net_list:
            if not net.get("net_id"):
                continue
            net_dict={'uuid': net["net_id"]}
            if net.get("type"):        net_dict["type"] = net["type"]
            if net.get("name"):        net_dict["name"] = net["name"]
            if net.get("vpci"):        net_dict["vpci"] = net["vpci"]
            if net.get("model"):       net_dict["model"] = net["model"]
            if net.get("mac_address"): net_dict["mac_address"] = net["mac_address"]
            virtio_net_list.append(net_dict)
        payload_dict={  "name":        name,
                        "description": description,
                        "imageRef":    image_id,
                        "flavorRef":   flavor_id,
                        "networks": virtio_net_list
                    }
        if start != None:
            payload_dict["start"] = start
        payload_req = json.dumps({"server": payload_dict})
        print self.url+'/'+self.tenant+'/servers'+payload_req
        try:
            vim_response = requests.post(self.url+'/'+self.tenant+'/servers', headers = headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_tenant_vminstance Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code != 200:
            print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new vm instance. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        #ok
        print vim_response.json()
        print json.dumps(vim_response.json(), indent=4)
        res,http_content = af.format_in(vim_response, openmano_schemas.new_vminstance_response_schema)
        #print http_content
        if  not res:
            return -HTTP_Bad_Request,http_content
        #r = af.remove_extra_items(http_content, openmano_schemas.new_vminstance_response_schema)
        #if r is not None: print "Warning: remove extra items ", r
        vminstance_id = http_content['server']['id']
        print json.dumps(http_content, indent=4)
        #connect data plane interfaces to network
        for net in net_list:
            if net["type"]=="virtual":
                if not net.get("net_id"):
                    continue
                for iface in http_content['server']['networks']:
                    if "name" in net:
                        if net["name"]==iface["name"]:
                            net["vim_id"] = iface['iface_id']
                            break
                    elif "net_id" in net:
                        if net["net_id"]==iface["net_id"]:
                            net["vim_id"] = iface['iface_id']
                            break
            else: #dataplane
                for numa in http_content['server'].get('extended',{}).get('numas',() ):
                    for iface in numa.get('interfaces',() ):
                        if net['name'] == iface['name']:
                            net['vim_id'] = iface['iface_id']
                            if net.get("net_id"):
                            #connect dataplane interface
                                result, port_id = self.connect_port_network(iface['iface_id'], net["net_id"])
                                if result < 0:
                                    error_text = "Error attaching port %s to network %s: %s." % (iface['iface_id'], net["net_id"], port_id)
                                    print "new_tenant_vminstance: " + error_text
                                    self.delete_tenant_vminstance(vminstance_id)
                                    return result, error_text
                            break
        
        print "VM instance id: ",vminstance_id
        return vim_response.status_code,vminstance_id
        
    def get_tenant_vminstance(self,vm_id):
        '''Returns the VM instance information from VIM'''
        print "VIMConnector: Getting tenant VM instance information from VIM"
        headers_req = {'content-type': 'application/json'}
        
        url = self.url+'/'+self.tenant+'/servers/'+vm_id
        print url
        try:
            vim_response = requests.get(url, headers = headers_req)
        except requests.exceptions.RequestException, e:
            print "get_tenant_vminstance Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            print vim_response.json()
            print json.dumps(vim_response.json(), indent=4)
            res,http_content = af.format_in(vim_response, openmano_schemas.new_vminstance_response_schema)
            #print http_content
            if res:
                print json.dumps(http_content, indent=4)
                return vim_response.status_code,http_content
            else: return -HTTP_Bad_Request,http_content
        else:
            print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to get vm instance. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        
    def delete_tenant_vminstance(self, vm_id):
        '''Removes a VM instance from VIM'''
        '''Returns the instance identifier'''
        print "VIMConnector: Delete a VM instance from VIM " + vm_id
        headers_req = {'content-type': 'application/json'}
        
        try:
            vim_response = requests.delete(self.url+'/'+self.tenant+'/servers/'+vm_id, headers = headers_req)
        except requests.exceptions.RequestException, e:
            print "delete_tenant_vminstance Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])

        #print vim_response.status_code
        if vim_response.status_code == 200:
            print json.dumps(vim_response.json(), indent=4)
            return vim_response.status_code, vm_id
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to delete vm instance. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code, text

    def refresh_tenant_vms_and_nets(self, vmDict, netDict):
        '''Refreshes the status of the dictionaries of VM instances and nets passed as arguments. It modifies the dictionaries'''
        '''Returns:
            - result: 0 if all elements could be refreshed (even if its status didn't change)
                      n>0, the number of elements that couldn't be refreshed,
                      <0 if error (foreseen)
            - error_msg: text with reference to possible errors
        '''
        #vms_refreshed = []
        #nets_refreshed = []
        vms_unrefreshed = []
        nets_unrefreshed = []
        for vm_id in vmDict:
            print "VIMConnector refresh_tenant_vms and nets: Getting tenant VM instance information from VIM"
            headers_req = {'content-type': 'application/json'}
        
            url = self.url+'/'+self.tenant+'/servers/'+ vm_id
            print url
            try:
                vim_response = requests.get(url, headers = headers_req)
            except requests.exceptions.RequestException, e:
                print "VIMConnector refresh_tenant_elements. Exception: ", e.args
                vms_unrefreshed.append(vm_id)
                continue
            #print vim_response
            #print vim_response.status_code
            if vim_response.status_code == 200:
                #print vim_response.json()
                #print json.dumps(vim_response.json(), indent=4)
                res,http_content = af.format_in(vim_response, openmano_schemas.new_vminstance_response_schema)
                if res:
                    #print json.dumps(http_content, indent=4)
                    #OLD:
                    #status = http_content['server']['status']
                    #if vmDict[vm_id] != status:
                    #    vmDict[vm_id] = status
                    #    vms_refreshed.append(vm_id)
                    #NEW:
                    vmDict[vm_id] = http_content['server']['status']
                    #print http_content['server']['hostId']
                else:
                    vms_unrefreshed.append(vm_id)
            else:
                #print vim_response.text
                jsonerror = af.format_jsonerror(vim_response)
                print 'VIMConnector refresh_tenant_vms_and_nets. Error in VIM "%s": not possible to get VM instance. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
                vms_unrefreshed.append(vm_id)
        
        #print "VMs refreshed: %s" % str(vms_refreshed)
        for net_id in netDict:
            print "VIMConnector refresh_tenant_vms_and_nets: Getting tenant network from VIM (tenant: " + str(self.tenant) + "): "
            headers_req = {'content-type': 'application/json'}
            r,c = self.get_tenant_network(net_id)
            if r<0:
                print "VIMconnector refresh_tenant_network. Error getting net_id '%s' status: %s" % (net_id, c)
                if r==-HTTP_Not_Found:
                    netDict[net_id] = "DELETED" #TODO check exit status
                else:
                    nets_unrefreshed.append(net_id)
            else:
                netDict[net_id] = c['status']

        #print "Nets refreshed: %s" % str(nets_refreshed)
        
        error_msg=""
        if len(vms_unrefreshed)+len(nets_unrefreshed)>0:
            error_msg += "VMs unrefreshed: " + str(vms_unrefreshed) + "; nets unrefreshed: " + str(nets_unrefreshed)
            print error_msg

        #return len(vms_unrefreshed)+len(nets_unrefreshed), error_msg, vms_refreshed, nets_refreshed
        return len(vms_unrefreshed)+len(nets_unrefreshed), error_msg
    
    def action_tenant_vminstance(self, vm_id, action_dict):
        '''Send and action over a VM instance from VIM'''
        '''Returns the status'''
        print "VIMConnector: Action over VM instance from VIM " + vm_id
        headers_req = {'content-type': 'application/json'}
        
        try:
            vim_response = requests.post(self.url+'/'+self.tenant+'/servers/'+vm_id+"/action", headers = headers_req, data=json.dumps(action_dict) )
        except requests.exceptions.RequestException, e:
            print "action_tenant_vminstance Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])

        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print "vimconnector.action_tenant_vminstance():", json.dumps(vim_response.json(), indent=4)
            return vim_response.status_code, vm_id
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": action over vm instance. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return vim_response.status_code, text
        
    def host_vim2gui(self, host, server_dict):
        '''Transform host dictionary from VIM format to GUI format,
        and append to the server_dict
        '''
        if type(server_dict) is not dict: 
            print 'vimconnector.host_vim2gui() ERROR, param server_dict must be a dictionary'
            return
        RAD={}
        occupation={}
        for numa in host['host']['numas']:
            RAD_item={}
            occupation_item={}
            #memory
            RAD_item['memory']={'size': str(numa['memory'])+'GB', 'eligible': str(numa['hugepages'])+'GB'}
            occupation_item['memory']= str(numa['hugepages_consumed'])+'GB'
            #cpus
            RAD_item['cpus']={}
            RAD_item['cpus']['cores'] = []
            RAD_item['cpus']['eligible_cores'] = []
            occupation_item['cores']=[]
            for _ in range(0, len(numa['cores']) / 2):
                RAD_item['cpus']['cores'].append( [] )
            for core in numa['cores']:
                RAD_item['cpus']['cores'][core['core_id']].append(core['thread_id'])
                if not 'status' in core: RAD_item['cpus']['eligible_cores'].append(core['thread_id'])
                if 'instance_id' in core: occupation_item['cores'].append(core['thread_id'])
            #ports
            RAD_item['ports']={}
            occupation_item['ports']={}
            for iface in numa['interfaces']:
                RAD_item['ports'][ iface['pci'] ] = 'speed:'+str(iface['Mbps'])+'M'
                occupation_item['ports'][ iface['pci'] ] = { 'occupied': str(100*iface['Mbps_consumed'] / iface['Mbps']) + "%" }
                
            RAD[ numa['numa_socket'] ] = RAD_item
            occupation[ numa['numa_socket'] ] = occupation_item
        server_dict[ host['host']['name'] ] = {'RAD':RAD, 'occupation':occupation}

    def get_hosts_info(self):
        '''Get the information of deployed hosts
        Returns the hosts content'''
    #obtain hosts list
        url=self.url+'/hosts'
        try:
            vim_response = requests.get(url)
        except requests.exceptions.RequestException, e:
            print "get_hosts_info Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print "vim get", url, "response:",  vim_response.status_code, vim_response.json()
        #print vim_response.status_code
        #print json.dumps(vim_response.json(), indent=4)
        if vim_response.status_code != 200:
            #TODO: get error
            print 'vimconnector.get_hosts_info error getting host list %d %s' %(vim_response.status_code, vim_response.json())
            return -vim_response.status_code, "Error getting host list"
        
        res,hosts = af.format_in(vim_response, openmano_schemas.get_hosts_response_schema)
            
        if res==False:
            print "vimconnector.get_hosts_info error parsing GET HOSTS vim response", hosts
            return HTTP_Internal_Server_Error, hosts
    #obtain hosts details
        hosts_dict={}
        for host in hosts['hosts']:
            url=self.url+'/hosts/'+host['id']
            try:
                vim_response = requests.get(url)
            except requests.exceptions.RequestException, e:
                print "get_hosts_info Exception: ", e.args
                return -HTTP_Not_Found, str(e.args[0])
            print "vim get", url, "response:",  vim_response.status_code, vim_response.json()
            if vim_response.status_code != 200:
                print 'vimconnector.get_hosts_info error getting detailed host %d %s' %(vim_response.status_code, vim_response.json())
                continue
            res,host_detail = af.format_in(vim_response, openmano_schemas.get_host_detail_response_schema)
            if res==False:
                print "vimconnector.get_hosts_info error parsing GET HOSTS/%s vim response" % host['id'], host_detail
                continue
            #print 'host id '+host['id'], json.dumps(host_detail, indent=4)
            self.host_vim2gui(host_detail, hosts_dict)
        return 200, hosts_dict

    def get_hosts(self, vim_tenant):
        '''Get the hosts and deployed instances
        Returns the hosts content'''
    #obtain hosts list
        url=self.url+'/hosts'
        try:
            vim_response = requests.get(url)
        except requests.exceptions.RequestException, e:
            print "get_hosts Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print "vim get", url, "response:",  vim_response.status_code, vim_response.json()
        #print vim_response.status_code
        #print json.dumps(vim_response.json(), indent=4)
        if vim_response.status_code != 200:
            #TODO: get error
            print 'vimconnector.get_hosts error getting host list %d %s' %(vim_response.status_code, vim_response.json())
            return -vim_response.status_code, "Error getting host list"
        
        res,hosts = af.format_in(vim_response, openmano_schemas.get_hosts_response_schema)
            
        if res==False:
            print "vimconnector.get_host error parsing GET HOSTS vim response", hosts
            return HTTP_Internal_Server_Error, hosts
    #obtain instances from hosts
        for host in hosts['hosts']:
            url=self.url+'/' + vim_tenant + '/servers?hostId='+host['id']
            try:
                vim_response = requests.get(url)
            except requests.exceptions.RequestException, e:
                print "get_hosts Exception: ", e.args
                return -HTTP_Not_Found, str(e.args[0])
            print "vim get", url, "response:",  vim_response.status_code, vim_response.json()
            if vim_response.status_code != 200:
                print 'vimconnector.get_hosts error getting instances at host %d %s' %(vim_response.status_code, vim_response.json())
                continue
            res,servers = af.format_in(vim_response, openmano_schemas.get_server_response_schema)
            if res==False:
                print "vimconnector.get_host error parsing GET SERVERS/%s vim response" % host['id'], servers
                continue
            #print 'host id '+host['id'], json.dumps(host_detail, indent=4)
            host['instances'] = servers['servers']
        return 200, hosts['hosts']

    def get_processor_rankings(self):
        '''Get the processor rankings in the VIM database'''
        url=self.url+'/processor_ranking'
        try:
            vim_response = requests.get(url)
        except requests.exceptions.RequestException, e:
            print "get_processor_rankings Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print "vim get", url, "response:", vim_response.status_code, vim_response.json()
        #print vim_response.status_code
        #print json.dumps(vim_response.json(), indent=4)
        if vim_response.status_code != 200:
            #TODO: get error
            print 'vimconnector.get_processor_rankings error getting processor rankings %d %s' %(vim_response.status_code, vim_response.json())
            return -vim_response.status_code, "Error getting processor rankings"
        
        res,rankings = af.format_in(vim_response, openmano_schemas.get_processor_rankings_response_schema)
        return res, rankings['rankings']
    
    def get_image_id_from_path(self, path):
        '''Get the image id from image path in the VIM database'''
        '''Returns:
             0,"Image not found"   if there are no images with that path
             1,image-id            if there is one image with that path
             <0,message            if there was an error (Image not found, error contacting VIM, more than 1 image with that path, etc.) 
        '''
        url=self.url + '/' + self.tenant + '/images?path='+path
        try:
            vim_response = requests.get(url)
        except requests.exceptions.RequestException, e:
            print "get_image_id_from_path url='%s'Exception: '%s'" % (url, str(e.args))
            return -HTTP_Not_Found, str(e.args[0])
        print "vim get_image_id_from_path", url, "response:", vim_response.status_code, vim_response.json()
        #print vim_response.status_code
        #print json.dumps(vim_response.json(), indent=4)
        if vim_response.status_code != 200:
            #TODO: get error
            print 'vimconnector.get_image_id_from_path error getting image id from path. Error code: %d Description: %s' %(vim_response.status_code, vim_response.json())
            return -vim_response.status_code, "Error getting image id from path"
        
        res,image = af.format_in(vim_response, openmano_schemas.get_images_response_schema)
        if not res:
            print "vimconnector.get_image_id_from_path error"
            return -HTTP_Bad_Request, image
        if len(image['images'])==0:
            return 0,"Image not found"
        elif len(image['images'])>1:
            print "vimconnector.get_image_id_from_path error. More than one images with the path %s." %(path)
            return -HTTP_Internal_Server_Error,"More than one images with that path"
        return 1, image['images'][0]['id']
        


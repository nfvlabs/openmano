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

Other connectors will be implemented in the future for interacting with other VIM
such as Openstack.
'''
__author__="Alfonso Tierno, Gerardo Garcia"
__date__ ="$26-aug-2014 11:09:29$"

import requests
import json
from utils import auxiliary_functions as af
import openmano_schemas
from nfvo_db import HTTP_Bad_Request, HTTP_Internal_Server_Error, HTTP_Not_Found

#TODO: Decide if it makes sense to have the methods outside the class as static generic methods
class vimconnector():
    def new_host(self,vimURIadmin, host_data):
        '''Adds a new host to VIM'''
        '''Returns status code of the VIM response'''
        print "VIMConnector: Adding a new host"
        headers_req = {'content-type': 'application/json'}
        payload_req = host_data
        try:
            vim_response = requests.post(vimURIadmin+'/hosts', headers = headers_req, data=payload_req)
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
            text = 'Error in VIM "%s": not possible to add new host. HTTP Response: %d. Error: %s' % (vimURIadmin, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
    
    def new_external_port(self,vimURIadmin,port_data):
        '''Adds a external port to VIM'''
        '''Returns the port identifier'''
        print "VIMConnector: Adding a new external port"
        headers_req = {'content-type': 'application/json'}
        payload_req = port_data
        try:
            vim_response = requests.post(vimURIadmin+'/ports', headers = headers_req, data=payload_req)
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
            text = 'Error in VIM "%s": not possible to add new external port. HTTP Response: %d. Error: %s' % (vimURIadmin, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
    
    
    def new_external_network(self,vimURI,net_name,net_type):
        '''Adds a external network to VIM (shared)'''
        '''Returns the network identifier'''
        print "VIMConnector: Adding external shared network to VIM (type " + net_type + "): "+ net_name
        
        headers_req = {'content-type': 'application/json'}
        payload_req = '{"network":{"name": "' + net_name + '","shared":true,"type": "' + net_type + '"}}'
        try:
            vim_response = requests.post(vimURI+'/networks', headers = headers_req, data=payload_req)
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
            text = 'Error in VIM "%s": not possible to add new external network. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

        
    def connect_port_network(self, vimURIadmin, port_id, network_id):
        '''Connects a external port to a network'''
        '''Returns status code of the VIM response'''
        print "VIMConnector: Connecting external port to network"
        
        headers_req = {'content-type': 'application/json'}
        payload_req = '{"port":{"network_id":"' + network_id + '"}}'
        try:
            vim_response = requests.put(vimURIadmin+'/ports/'+port_id, headers = headers_req, data=payload_req)
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
            text = 'Error in VIM "%s": not possible to connect external port to network. HTTP Response: %d. Error: %s' % (vimURIadmin, vim_response.status_code, jsonerror)
            print text
            return -vim_response.status_code,text
        
    def new_tenant(self,vimURI,tenant_name,tenant_description):
        '''Adds a new tenant to VIM'''
        '''Returns the tenant identifier'''
        print "VIMConnector: Adding a new tenant to VIM"
        headers_req = {'content-type': 'application/json'}
        payload_dict = {"tenant": {"name":tenant_name,"description": tenant_description, "enabled": True}}
        payload_req = json.dumps(payload_dict)
        #print payload_req

        try:
            vim_response = requests.post(vimURI+'/tenants', headers = headers_req, data=payload_req)
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
            text = 'Error in VIM "%s": not possible to add new tenant. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def delete_tenant(self,vimURI,tenant_id,):
        '''Delete a tenant from VIM'''
        '''Returns the tenant identifier'''
        print "VIMConnector: Deleting  a  tenant from VIM"
        headers_req = {'content-type': 'application/json'}
        try:
            vim_response = requests.delete(vimURI+'/tenants/'+tenant_id, headers = headers_req)
        except requests.exceptions.RequestException, e:
            print "delete_tenant Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        #print vim_response
        if vim_response.status_code == 200:
            return vim_response.status_code,tenant_id
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to delete tenant. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text


    def new_tenant_network(self,vimURI,tenant_id,net_name,net_type):
        '''Adds a tenant network to VIM'''
        '''Returns the network identifier'''
        if net_type=="bridge":
            net_type="bridge_data"
        print "VIMConnector: Adding a new tenant network to VIM (tenant: " + tenant_id + ", type: " + net_type + "): "+ net_name

        headers_req = {'content-type': 'application/json'}
        payload_req = '{"network":{"name": "' + net_name + '", "type": "' + net_type + '","tenant_id":"' + tenant_id + '"}}'
        try:
            vim_response = requests.post(vimURI+'/networks', headers = headers_req, data=payload_req)
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
            text = 'Error in VIM "%s": not possible to add new tenant network. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def get_tenant_network(self,vimURI,tenant_id=None, filter_dict={}):
        '''Obtain tenant networks of VIM'''
        '''Returns the network list'''
        print "VIMConnector: Getting tenant network from VIM (tenant: " + str(tenant_id) + "): "
        filterquery=[]
        filterquery_text=''
        for k,v in filter_dict.iteritems():
            filterquery.append(str(k)+'='+str(v))
        if tenant_id!=None:
            filterquery.append('tenant_id='+tenant_id)
        if len(filterquery)>0:
            filterquery_text='?'+ '&'.join(filterquery)
        headers_req = {'content-type': 'application/json'}
        try:
            print vimURI+'/networks'+filterquery_text
            vim_response = requests.get(vimURI+'/networks'+filterquery_text, headers = headers_req)
        except requests.exceptions.RequestException, e:
            print "get_tenant_network Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            #TODO: parse input datares,http_content = af.format_in(vim_response, openmano_schemas.new_network_response_schema)
            #print http_content
            return vim_response.status_code, vim_response.json()
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to get tenant network. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text


    def delete_tenant_network(self,vimURI, tenant_id, net_id):
        '''Deletes a tenant network from VIM'''
        '''Returns the network identifier'''
        print "VIMConnector: Deleting a new tenant network from VIM tenant: " + tenant_id + ", id: " + net_id

        headers_req = {'content-type': 'application/json'}
        try:
            vim_response = requests.delete(vimURI+'/networks/'+net_id, headers=headers_req)
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
            text = 'Error in VIM "%s": not possible to delete tenant network. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text


    def new_tenant_flavor(self,vimURI,tenant_id,flavor_data):
        '''Adds a tenant flavor to VIM'''
        '''Returns the flavor identifier'''
        print "VIMConnector: Adding a new flavor to VIM"
        #print "VIM URL:",vimURI
        #print "Tenant id:",tenant_id
        #print "Flavor:",flavor_data
        headers_req = {'content-type': 'application/json'}
        payload_req = flavor_data
        try:
            vim_response = requests.post(vimURI+'/'+tenant_id+'/flavors', headers = headers_req, data=payload_req)
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
            text = 'Error in VIM "%s": not possible to add new flavor. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def delete_tenant_flavor(self,vimURI,tenant_id,flavor_id):
        '''Deletes a tenant flavor from VIM'''
        '''Returns the HTTP response code and a message indicating details of the success or fail'''
        print "VIMConnector: Deleting a flavor from VIM"
        print "VIM URL:",vimURI
        print "Tenant id:",tenant_id
        print "Flavor id:",flavor_id
        #headers_req = {'content-type': 'application/json'}
        #payload_req = flavor_data
        try:
            vim_response = requests.delete(vimURI+'/'+tenant_id+'/flavors/'+flavor_id)
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
            text = 'Error in VIM "%s": not possible to delete flavor. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def new_tenant_image(self,vimURI,tenant_id,image_data):
        '''
        Adds a tenant image to VIM
        Returns:
            200, image-id        if the image is created
            <0, message          if there is an error
        '''
        print "VIMConnector: Adding a new image to VIM", image_data
        headers_req = {'content-type': 'application/json'}
        payload_req = image_data
        try:
            vim_response = requests.post(vimURI+'/'+tenant_id+'/images', headers = headers_req, data=payload_req)
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
            text = 'Error in VIM "%s": not possible to add new image. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def delete_tenant_image(self,vimURI,tenant_id,image_id):
        '''Deletes a tenant image from VIM'''
        '''Returns the HTTP response code and a message indicating details of the success or fail'''
        print "VIMConnector: Deleting an image from VIM"
        print "VIM URL:",vimURI
        print "Tenant id:",tenant_id
        print "Image id:",image_id
        #headers_req = {'content-type': 'application/json'}
        #payload_req = flavor_data
        try:
            vim_response = requests.delete(vimURI+'/'+tenant_id+'/images/'+image_id)
        except requests.exceptions.RequestException, e:
            print "delete_tenant_image Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        print vim_response.status_code
        if vim_response.status_code == 200:
            result = vim_response.json()["result"]
            return 200,result
        else:
            #print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to delete image. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        
    def new_tenant_vminstancefromJSON(self,vimURI,tenant_id,vm_data):
        '''Adds a VM instance to VIM'''
        '''Returns the instance identifier'''
        print "VIMConnector: Adding a new VM instance from JSON to VIM"
        headers_req = {'content-type': 'application/json'}
        payload_req = vm_data
        try:
            vim_response = requests.post(vimURI+'/'+tenant_id+'/servers', headers = headers_req, data=payload_req)
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
            text = 'Error in VIM "%s": not possible to add new vm instance. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def new_tenant_vminstance(self,vimURI,tenant_id,name,description,start,image_id,flavor_id,net_list,iface_list=None):
        '''Adds a VM instance to VIM'''
        '''Returns the instance identifier'''
        print "VIMConnector: Adding a new VM instance to VIM"
        headers_req = {'content-type': 'application/json'}
        
#         net_list = []
#         for k,v in net_dict.items():
#             print k,v
#             net_list.append('{"name":"' + k + '", "uuid":"' + v + '"}')
#         net_list_string = ', '.join(net_list) 
            
        payload_req = '{"server":{"networks": ' + json.dumps(net_list) + ',"name":"' + name + '","description":"' + description + \
        '","imageRef":"' + image_id + '","flavorRef":"' + flavor_id + '"'
        if start != None:
            payload_req += ',"start": "' + start+ '"'
        payload_req += '}}'
        print vimURI+'/'+tenant_id+'/servers'+payload_req
        try:
            vim_response = requests.post(vimURI+'/'+tenant_id+'/servers', headers = headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_tenant_vminstance Exception: ", e.args
            return -HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            print vim_response.json()
            print json.dumps(vim_response.json(), indent=4)
            res,http_content = af.format_in(vim_response, openmano_schemas.new_vminstance_response_schema)
            #print http_content
            if res:
                #r = af.remove_extra_items(http_content, openmano_schemas.new_vminstance_response_schema)
                #if r is not None: print "Warning: remove extra items ", r
                print json.dumps(http_content, indent=4)
                #insert interface vim id at iface_list
                if iface_list is not None and len(iface_list)>0:
                    #bridges interfaces
                    try:
                        for iface in http_content['server']['networks']:
                            for i in iface_list:
                                if i['internal_name'] == iface['name']:
                                    i['vim_id'] = iface['iface_id']
                    except KeyError, e:
                        print "Attach vim_id to interface list: Error No bridge interfaces KeyError " + e.message
                        pass
                    #extended interfaces
                    try:
                        for numa in http_content['server']['extended']['numas']:
                            for iface in numa['interfaces']:
                                for i in iface_list:
                                    if i['internal_name'] == iface['name']:
                                        i['vim_id'] = iface['iface_id']
                    except KeyError, e:
                        print "Attach vim_id to interface list: Error No numa interfaces KeyError " + e.message
                        pass
                
                
                vminstance_id = http_content['server']['id']
                print "VM instance id: ",vminstance_id
                return vim_response.status_code,vminstance_id
            else: return -HTTP_Bad_Request,http_content
        else:
            print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new vm instance. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        
    def get_tenant_vminstance(self,vimURI,tenant_id,vm_id):
        '''Returns the VM instance information from VIM'''
        print "VIMConnector: Getting tenant VM instance information from VIM"
        headers_req = {'content-type': 'application/json'}
        
        url = vimURI+'/'+tenant_id+'/servers/'+vm_id
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
                #insert interface vim id at iface_list
                return vim_response.status_code,http_content
            else: return -HTTP_Bad_Request,http_content
        else:
            print vim_response.text
            jsonerror = af.format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new vm instance. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        
    def delete_tenant_vminstance(self,vimURI,tenant_id, vm_id):
        '''Removes a VM instance from VIM'''
        '''Returns the instance identifier'''
        print "VIMConnector: Delete a VM instance from VIM " + vm_id
        headers_req = {'content-type': 'application/json'}
        
        try:
            vim_response = requests.delete(vimURI+'/'+tenant_id+'/servers/'+vm_id, headers = headers_req)
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
            text = 'Error in VIM "%s": not possible to delete vm instance. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code, text

    def action_tenant_vminstance(self,vimURI,tenant_id, vm_id, action_dict):
        '''Send and action over a VM instance from VIM'''
        '''Returns the status'''
        print "VIMConnector: Action over VM instance from VIM " + vm_id
        headers_req = {'content-type': 'application/json'}
        
        try:
            vim_response = requests.post(vimURI+'/'+tenant_id+'/servers/'+vm_id+"/action", headers = headers_req, data=json.dumps(action_dict) )
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
            text = 'Error in VIM "%s": action over vm instance. HTTP Response: %d. Error: %s' % (vimURI, vim_response.status_code, jsonerror)
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

    def get_hosts_info(self,vimURI):
        '''Get the information of deployed hosts
        Returns the hosts content'''
    #obtain hosts list
        url=vimURI+'/hosts'
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
            url=vimURI+'/hosts/'+host['id']
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

    def get_hosts(self,vimURI, vim_tenant):
        '''Get the hosts and deployed instances
        Returns the hosts content'''
    #obtain hosts list
        url=vimURI+'/hosts'
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
            url=vimURI+'/' + vim_tenant + '/servers?hostId='+host['id']
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

    def get_processor_rankings(self, vimURI):
        '''Get the processor rankings in the VIM database'''
        url=vimURI+'/processor_ranking'
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
    
    def get_image_id_from_path(self, vimURI, vim_tenant, path):
        '''Get the image id from image path in the VIM database'''
        '''Returns:
             0,"Image not found"   if there are no images with that path
             1,image-id            if there is one image with that path
             <0,message            if there was an error (Image not found, error contacting VIM, more than 1 image with that path, etc.) 
        '''
        url=vimURI+'/'+vim_tenant+'/images?path='+path
        try:
            vim_response = requests.get(url)
        except requests.exceptions.RequestException, e:
            print "get_image_id_from_path Exception: ", e.args
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
        


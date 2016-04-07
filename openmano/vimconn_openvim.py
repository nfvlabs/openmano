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

import vimconn
import requests
import json
import yaml
from openmano_schemas import id_schema, name_schema, nameshort_schema, description_schema, \
                            vlan1000_schema, integer0_schema
from jsonschema import validate as js_v, exceptions as js_e

'''contain the openvim virtual machine status to openmano status'''
vmStatus2manoFormat={'ACTIVE':'ACTIVE',
                     'PAUSED':'PAUSED',
                     'SUSPENDED': 'SUSPENDED',
                     'INACTIVE':'INACTIVE',
                     'CREATING':'BUILD',
                     'ERROR':'ERROR','DELETED':'DELETED'
                     }
netStatus2manoFormat={'ACTIVE':'ACTIVE','INACTIVE':'INACTIVE','BUILD':'BUILD','ERROR':'ERROR','DELETED':'DELETED', 'DOWN':'DOWN'
                     }


host_schema = {
    "type":"object",
    "properties":{
        "id": id_schema,
        "name": name_schema,
    },
    "required": ["id"]
}
image_schema = {
    "type":"object",
    "properties":{
        "id": id_schema,
        "name": name_schema,
    },
    "required": ["id","name"]
}
server_schema = {
    "type":"object",
    "properties":{
        "id":id_schema,
        "name": name_schema,
    },
    "required": ["id","name"]
}
new_host_response_schema = {
    "title":"host response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "host": host_schema
    },
    "required": ["host"],
    "additionalProperties": False
}

get_images_response_schema = {
    "title":"openvim images response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "images":{
            "type":"array",
            "items": image_schema,
        }
    },
    "required": ["images"],
    "additionalProperties": False
}

get_hosts_response_schema = {
    "title":"openvim hosts response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "hosts":{
            "type":"array",
            "items": host_schema,
        }
    },
    "required": ["hosts"],
    "additionalProperties": False
}

get_host_detail_response_schema = new_host_response_schema # TODO: Content is not parsed yet

get_server_response_schema = {
    "title":"openvim server response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "servers":{
            "type":"array",
            "items": server_schema,
        }
    },
    "required": ["servers"],
    "additionalProperties": False
}

new_tenant_response_schema = {
    "title":"tenant response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "tenant":{
            "type":"object",
            "properties":{
                "id": id_schema,
                "name": nameshort_schema,
                "description":description_schema,
                "enabled":{"type" : "boolean"}
            },
            "required": ["id"]
        }
    },
    "required": ["tenant"],
    "additionalProperties": False
}

new_network_response_schema = {
    "title":"network response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "network":{
            "type":"object",
            "properties":{
                "id":id_schema,
                "name":name_schema,
                "type":{"type":"string", "enum":["bridge_man","bridge_data","data", "ptp"]},
                "shared":{"type":"boolean"},
                "tenant_id":id_schema,
                "admin_state_up":{"type":"boolean"},
                "vlan":vlan1000_schema
            },
            "required": ["id"]
        }
    },
    "required": ["network"],
    "additionalProperties": False
}


# get_network_response_schema = {
#     "title":"get network response information schema",
#     "$schema": "http://json-schema.org/draft-04/schema#",
#     "type":"object",
#     "properties":{
#         "network":{
#             "type":"object",
#             "properties":{
#                 "id":id_schema,
#                 "name":name_schema,
#                 "type":{"type":"string", "enum":["bridge_man","bridge_data","data", "ptp"]},
#                 "shared":{"type":"boolean"},
#                 "tenant_id":id_schema,
#                 "admin_state_up":{"type":"boolean"},
#                 "vlan":vlan1000_schema
#             },
#             "required": ["id"]
#         }
#     },
#     "required": ["network"],
#     "additionalProperties": False
# }


new_port_response_schema = {
    "title":"port response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "port":{
            "type":"object",
            "properties":{
                "id":id_schema,
            },
            "required": ["id"]
        }
    },
    "required": ["port"],
    "additionalProperties": False
}

get_flavor_response_schema = {
    "title":"openvim flavors response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "flavor":{
            "type":"object",
            "properties":{
                "id":   id_schema,
                "name": name_schema,
                "extended": {"type":"object"},
            },
            "required": ["id", "name"],
        }
    },
    "required": ["flavor"],
    "additionalProperties": False
}

new_flavor_response_schema = {
    "title":"flavor response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "flavor":{
            "type":"object",
            "properties":{
                "id":id_schema,
            },
            "required": ["id"]
        }
    },
    "required": ["flavor"],
    "additionalProperties": False
}

new_image_response_schema = {
    "title":"image response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "image":{
            "type":"object",
            "properties":{
                "id":id_schema,
            },
            "required": ["id"]
        }
    },
    "required": ["image"],
    "additionalProperties": False
}

new_vminstance_response_schema = {
    "title":"server response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "server":{
            "type":"object",
            "properties":{
                "id":id_schema,
            },
            "required": ["id"]
        }
    },
    "required": ["server"],
    "additionalProperties": False
}

get_processor_rankings_response_schema = {
    "title":"processor rankings information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "rankings":{
            "type":"array",
            "items":{
                "type":"object",
                "properties":{
                    "model": description_schema,
                    "value": integer0_schema
                },
                "additionalProperties": False,
                "required": ["model","value"]
            }
        },
        "additionalProperties": False,
        "required": ["rankings"]
    }
}

class vimconnector(vimconn.vimconnector):
    def __init__(self, uuid, name, tenant_id, tenant_name, url, url_admin=None, user=None, passwd=None,debug=True,config={}):
        vimconn.vimconnector.__init__(self, uuid, name, tenant_id, tenant_name, url, url_admin, user, passwd, debug, config)
        self.tenant = None
        self.headers_req = {'content-type': 'application/json'}
        if tenant_id:
            self.tenant = tenant_id

    def __setitem__(self,index, value):
        '''Set individuals parameters 
        Throw TypeError, KeyError
        '''
        if index=='tenant_id':
            self.tenant = value
        elif index=='tenant_name':
            self.tenant = None
        vimconn.vimconnector.__setitem__(self,index, value)    

    def _get_my_tenant(self):
        '''Obtain uuid of my tenant from name
        '''
        if self.tenant:
            return self.tenant

        vim_response = requests.get(self.url+'/tenants?name='+ self.tenant_name, headers = self.headers_req)
        if vim_response.status_code != 200:
            raise vimconn.vimconnectorException ("_get_my_tenant response " + str(vim_response.status_code))
        tenant_list = vim_response.json()["tenants"]
        if len(tenant_list) == 0:
            raise vimconn.vimconnectorException ("No tenant found for name '%s'" % str(self.tenant_name))
        elif len(tenant_list) > 1:
            raise vimconn.vimconnectorException ("More that one tenant found for name '%s'" % str(self.tenant_name))
        self.tenant = tenant_list[0]["id"]
        return self.tenant 

    def _format_jsonerror(self,http_response):
        try:
            data = http_response.json()
            return data["error"]["description"]
        except:
            return http_response.text

    def _format_in(self, http_response, schema):
        try:
            client_data = http_response.json()
            js_v(client_data, schema)
            #print "Input data: ", str(client_data)
            return True, client_data
        except js_e.ValidationError, exc:
            print "validate_in error, jsonschema exception ", exc.message, "at", exc.path
            return False, ("validate_in error, jsonschema exception ", exc.message, "at", exc.path)
    
    def _remove_extra_items(self, data, schema):
        deleted=[]
        if type(data) is tuple or type(data) is list:
            for d in data:
                a= self._remove_extra_items(d, schema['items'])
                if a is not None: deleted.append(a)
        elif type(data) is dict:
            for k in data.keys():
                if 'properties' not in schema or k not in schema['properties'].keys():
                    del data[k]
                    deleted.append(k)
                else:
                    a = self._remove_extra_items(data[k], schema['properties'][k])
                    if a is not None:  deleted.append({k:a})
        if len(deleted) == 0: return None
        elif len(deleted) == 1: return deleted[0]
        else: return deleted
    
    def new_host(self, host_data):
        '''Adds a new host to VIM'''
        '''Returns status code of the VIM response'''
        print "VIMConnector: Adding a new host"
        payload_req = host_data
        try:
            vim_response = requests.post(self.url_admin+'/hosts', headers = self.headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_host Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
        #print vim_response.json()
        #print json.dumps(vim_response.json(), indent=4)
            res,http_content = self._format_in(vim_response, new_host_response_schema)
            #print http_content
            if res :
                r = self._remove_extra_items(http_content, new_host_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                host_id = http_content['host']['id']
                #print "Host id: ",host_id
                return vim_response.status_code,host_id
            else: return -vimconn.HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = self.__format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new host. HTTP Response: %d. Error: %s' % (self.url_admin, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
    
    def new_external_port(self, port_data):
        '''Adds a external port to VIM'''
        '''Returns the port identifier'''
        print "VIMConnector: Adding a new external port"
        payload_req = port_data
        try:
            vim_response = requests.post(self.url_admin+'/ports', headers = self.headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_external_port Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
        #print vim_response.json()
        #print json.dumps(vim_response.json(), indent=4)
            res, http_content = self.__format_in(vim_response, new_port_response_schema)
        #print http_content
            if res:
                r = self._remove_extra_items(http_content, new_port_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                port_id = http_content['port']['id']
                print "Port id: ",port_id
                return vim_response.status_code,port_id
            else: return -vimconn.HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new external port. HTTP Response: %d. Error: %s' % (self.url_admin, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        
    def new_external_network(self,net_name,net_type):
        '''Adds a external network to VIM (shared)'''
        '''Returns the network identifier'''
        print "VIMConnector: Adding external shared network to VIM (type " + net_type + "): "+ net_name
        
        payload_req = '{"network":{"name": "' + net_name + '","shared":true,"type": "' + net_type + '"}}'
        try:
            vim_response = requests.post(self.url+'/networks', headers = self.headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_external_network Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = self._format_in(vim_response, new_network_response_schema)
            #print http_content
            if res:
                r = self._remove_extra_items(http_content, new_network_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                network_id = http_content['network']['id']
                print "Network id: ",network_id
                return vim_response.status_code,network_id
            else: return -vimconn.HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new external network. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        
    def connect_port_network(self, port_id, network_id, admin=False):
        '''Connects a external port to a network'''
        '''Returns status code of the VIM response'''
        print "VIMConnector: Connecting external port to network"
        
        payload_req = '{"port":{"network_id":"' + network_id + '"}}'
        if admin:
            if self.url_admin==None:
                return -vimconn.HTTP_Unauthorized, "datacenter cannot contain  admin URL"
            url= self.url_admin
        else:
            url= self.url
        try:
            vim_response = requests.put(url +'/ports/'+port_id, headers = self.headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "connect_port_network Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = self._format_in(vim_response, new_port_response_schema)
            #print http_content
            if res:
                r = self._remove_extra_items(http_content, new_port_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                port_id = http_content['port']['id']
                print "Port id: ",port_id
                return vim_response.status_code,port_id
            else: return -vimconn.HTTP_Bad_Request,http_content
        else:
            print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to connect external port to network. HTTP Response: %d. Error: %s' % (self.url_admin, vim_response.status_code, jsonerror)
            print text
            return -vim_response.status_code,text
        
    def new_tenant(self,tenant_name,tenant_description):
        '''Adds a new tenant to VIM'''
        '''Returns the tenant identifier'''
        print "VIMConnector: Adding a new tenant to VIM"
        payload_dict = {"tenant": {"name":tenant_name,"description": tenant_description, "enabled": True}}
        payload_req = json.dumps(payload_dict)
        #print payload_req

        try:
            vim_response = requests.post(self.url+'/tenants', headers = self.headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_tenant Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        #print vim_response
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = self._format_in(vim_response, new_tenant_response_schema)
            #print http_content
            if res:
                r = self._remove_extra_items(http_content, new_tenant_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                tenant_id = http_content['tenant']['id']
                #print "Tenant id: ",tenant_id
                return vim_response.status_code,tenant_id
            else: return -vimconn.HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new tenant. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def delete_tenant(self,tenant_id,):
        '''Delete a tenant from VIM'''
        '''Returns the tenant identifier'''
        print "VIMConnector: Deleting  a  tenant from VIM"
        try:
            vim_response = requests.delete(self.url+'/tenants/'+tenant_id, headers = self.headers_req)
        except requests.exceptions.RequestException, e:
            print "delete_tenant Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        #print vim_response
        if vim_response.status_code == 200:
            return vim_response.status_code,tenant_id
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to delete tenant. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def new_tenant_network(self,net_name,net_type,public=False, **vim_specific):
        '''Adds a tenant network to VIM'''
        '''Returns the network identifier'''
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        print "vim_specific", vim_specific
        if net_type=="bridge":
            net_type="bridge_data"
        print "VIMConnector: Adding a new tenant network to VIM (tenant: " + str(self.tenant) + ", type: " + net_type + "): "+ net_name

        payload_req = {"name": net_name, "type": net_type, "tenant_id": self.tenant, "shared": public}
        payload_req.update(vim_specific)
        try:
            vim_response = requests.post(self.url+'/networks', headers = self.headers_req, data=json.dumps({"network": payload_req}) )
        except requests.exceptions.RequestException, e:
            print "new_tenant_network Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = self._format_in(vim_response, new_network_response_schema)
            #print http_content
            if res:
                r = self._remove_extra_items(http_content, new_network_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                network_id = http_content['network']['id']
                print "Tenant Network id: ",network_id
                return vim_response.status_code,network_id
            else: return -vimconn.HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new tenant network. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def get_tenant_list(self, filter_dict={}):
        '''Obtain tenants of VIM
        Filter_dict can be:
            name: network name
            id: network uuid
        Returns the network list of dictionaries
        '''
        print "VIMConnector.get_tenant_list: Getting tenants from VIM (filter: " + str(filter_dict) + "): "
        filterquery=[]
        filterquery_text=''
        for k,v in filter_dict.iteritems():
            filterquery.append(str(k)+'='+str(v))
        if len(filterquery)>0:
            filterquery_text='?'+ '&'.join(filterquery)
        try:
            print self.url+'/tenants'+filterquery_text
            vim_response = requests.get(self.url+'/tenants'+filterquery_text, headers = self.headers_req)
        except requests.exceptions.RequestException, e:
            print "get_tenant_list Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            #TODO: parse input datares,http_content = self._format_in(vim_response, new_network_response_schema)
            #print http_content
            return vim_response.status_code, vim_response.json()["tenants"]
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to get tenant list. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
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
        
        filter_dict["tenant_id"] = self._get_my_tenant()
        print "VIMConnector.get_network_list: Getting tenant network from VIM (filter: " + str(filter_dict) + "): "
        filterquery=[]
        filterquery_text=''
        for k,v in filter_dict.iteritems():
            filterquery.append(str(k)+'='+str(v))
        if len(filterquery)>0:
            filterquery_text='?'+ '&'.join(filterquery)
        try:
            print self.url+'/networks'+filterquery_text
            vim_response = requests.get(self.url+'/networks'+filterquery_text, headers = self.headers_req)
        except requests.exceptions.RequestException, e:
            print "get_network_list Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            #TODO: parse input datares,http_content = self._format_in(vim_response, new_network_response_schema)
            #print http_content
            return vim_response.status_code, vim_response.json()["networks"]
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
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
            return -vimconn.HTTP_Not_Found, "Network '%s' not found" % net_id
        elif len(net_list)>1:
            return -vimconn.HTTP_Conflict, "Found more than one network with this criteria"
        return 1, net_list[0]

    def delete_tenant_network(self, net_id):
        '''Deletes a tenant network from VIM'''
        '''Returns the network identifier'''
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        print "VIMConnector: Deleting a new tenant network from VIM tenant: " + self.tenant + ", id: " + net_id

        try:
            vim_response = requests.delete(self.url+'/networks/'+net_id, headers=self.headers_req)
        except requests.exceptions.RequestException, e:
            print "delete_tenant_network Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])

        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
                return vim_response.status_code,net_id
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to delete tenant network. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def refresh_tenant_network(self, net_id):
        '''Refreshes the status of the tenant network'''
        '''Returns: 0 if no error,
                    <0 if error'''
        return 0

    def get_tenant_flavor(self, flavor_id):
        '''Obtain flavor details from the  VIM
            Returns the flavor dict details
        '''
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        print "VIMConnector: Getting flavor from VIM"
        #print "VIM URL:",self.url
        #print "Tenant id:",self.tenant
        #print "Flavor:",flavor_data
        try:
            vim_response = requests.get(self.url+'/'+self.tenant+'/flavors/'+flavor_id, headers = self.headers_req)
        except requests.exceptions.RequestException, e:
            print "get_tenant_flavor Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = self._format_in(vim_response, get_flavor_response_schema)
            #print http_content
            if res:
                r = self._remove_extra_items(http_content, get_flavor_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                flavor_id = http_content['flavor']['id']
                print "Flavor id: ",flavor_id
                return vim_response.status_code,flavor_id
            else: return -vimconn.HTTP_Bad_Request,http_content

        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to get flavor. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text    
        
    def new_tenant_flavor(self, flavor_data):
        '''Adds a tenant flavor to VIM'''
        '''Returns the flavor identifier'''
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        print "VIMConnector: Adding a new flavor to VIM"
        #print "VIM URL:",self.url
        #print "Tenant id:",self.tenant
        #print "Flavor:",flavor_data
        payload_req = json.dumps({'flavor': flavor_data})
        try:
            vim_response = requests.post(self.url+'/'+self.tenant+'/flavors', headers = self.headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_tenant_flavor Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = self._format_in(vim_response, new_flavor_response_schema)
            #print http_content
            if res:
                r = self._remove_extra_items(http_content, new_flavor_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                flavor_id = http_content['flavor']['id']
                print "Flavor id: ",flavor_id
                return vim_response.status_code,flavor_id
            else: return -vimconn.HTTP_Bad_Request,http_content

        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new flavor. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def delete_tenant_flavor(self,flavor_id):
        '''Deletes a tenant flavor from VIM'''
        '''Returns the HTTP response code and a message indicating details of the success or fail'''
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        print "VIMConnector: Deleting a flavor from VIM"
        print "VIM URL:",self.url
        print "Tenant id:",self.tenant
        print "Flavor id:",flavor_id
        #payload_req = flavor_data
        try:
            vim_response = requests.delete(self.url+'/'+self.tenant+'/flavors/'+flavor_id)
        except requests.exceptions.RequestException, e:
            print "delete_tenant_flavor Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        print vim_response.status_code
        if vim_response.status_code == 200:
            result = vim_response.json()["result"]
            return 200,result
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
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
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        print "VIMConnector: Adding a new image to VIM", image_dict['location']
        new_image_dict={'name': image_dict['name']}
        if 'description' in image_dict and image_dict['description'] != None:
            new_image_dict['description'] = image_dict['description']
        if 'metadata' in image_dict and image_dict['metadata'] != None:
            new_image_dict['metadata'] = yaml.load(image_dict['metadata'])
        if 'location' in image_dict and image_dict['location'] != None:
            new_image_dict['path'] = image_dict['location']
        payload_req = json.dumps({"image":new_image_dict})
        url=self.url + '/' + self.tenant + '/images'
        try:
            vim_response = requests.post(url, headers = self.headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_tenant_image Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = self._format_in(vim_response, new_image_response_schema)
            #print http_content
            if res:
                r = self._remove_extra_items(http_content, new_image_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                image_id = http_content['image']['id']
                print "Image id: ",image_id
                return vim_response.status_code,image_id
            else: return -vimconn.HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new image. HTTP Response: %d. Error: %s' % (url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text

    def delete_tenant_image(self, image_id):
        '''Deletes a tenant image from VIM'''
        '''Returns the HTTP response code and a message indicating details of the success or fail'''
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        print "VIMConnector: Deleting an image from VIM"
        #payload_req = flavor_data
        url=self.url + '/'+ self.tenant +'/images/'+image_id
        try:
            vim_response = requests.delete(url)
        except requests.exceptions.RequestException, e:
            print "delete_tenant_image Exception url '%s': " % url, e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        print vim_response.status_code
        if vim_response.status_code == 200:
            result = vim_response.json()["result"]
            return 200,result
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to delete image. HTTP Response: %d. Error: %s' % (url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        
    def new_tenant_vminstancefromJSON(self, vm_data):
        '''Adds a VM instance to VIM'''
        '''Returns the instance identifier'''
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        print "VIMConnector: Adding a new VM instance from JSON to VIM"
        payload_req = vm_data
        try:
            vim_response = requests.post(self.url+'/'+self.tenant+'/servers', headers = self.headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_tenant_vminstancefromJSON Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            res,http_content = self._format_in(vim_response, new_image_response_schema)
            #print http_content
            if res:
                r = self._remove_extra_items(http_content, new_image_response_schema)
                if r is not None: print "Warning: remove extra items ", r
                #print http_content
                vminstance_id = http_content['server']['id']
                print "Tenant image id: ",vminstance_id
                return vim_response.status_code,vminstance_id
            else: return -vimconn.HTTP_Bad_Request,http_content
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
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
                type: 'virtual', 'PF', 'VF', 'VFnotShared'
                vim_id: filled/added by this function
                #TODO ip, security groups
        Returns >=0, the instance identifier
                <0, error_text
        '''
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        print "VIMConnector: Adding a new VM instance to VIM"
        
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
            vim_response = requests.post(self.url+'/'+self.tenant+'/servers', headers = self.headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            print "new_tenant_vminstance Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code != 200:
            print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to add new vm instance. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        #ok
        print vim_response.json()
        print json.dumps(vim_response.json(), indent=4)
        res,http_content = self._format_in(vim_response, new_vminstance_response_schema)
        #print http_content
        if  not res:
            return -vimconn.HTTP_Bad_Request,http_content
        #r = self._remove_extra_items(http_content, new_vminstance_response_schema)
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
                            #Code bellow is not needed, current openvim connect dataplane interfaces 
                            #if net.get("net_id"):
                            ##connect dataplane interface
                            #    result, port_id = self.connect_port_network(iface['iface_id'], net["net_id"])
                            #    if result < 0:
                            #        error_text = "Error attaching port %s to network %s: %s." % (iface['iface_id'], net["net_id"], port_id)
                            #        print "new_tenant_vminstance: " + error_text
                            #        self.delete_tenant_vminstance(vminstance_id)
                            #        return result, error_text
                            break
        
        print "VM instance id: ",vminstance_id
        return vim_response.status_code,vminstance_id
        
    def get_tenant_vminstance(self,vm_id):
        '''Returns the VM instance information from VIM'''
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        print "VIMConnector: Getting tenant VM instance information from VIM"
        
        url = self.url+'/'+self.tenant+'/servers/'+vm_id
        print url
        try:
            vim_response = requests.get(url, headers = self.headers_req)
        except requests.exceptions.RequestException, e:
            print "get_tenant_vminstance Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            print vim_response.json()
            print json.dumps(vim_response.json(), indent=4)
            res,http_content = self._format_in(vim_response, new_vminstance_response_schema)
            #print http_content
            if res:
                print json.dumps(http_content, indent=4)
                return vim_response.status_code,http_content
            else: return -vimconn.HTTP_Bad_Request,http_content
        else:
            print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
            text = 'Error in VIM "%s": not possible to get vm instance. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
            #print text
            return -vim_response.status_code,text
        
    def delete_tenant_vminstance(self, vm_id):
        '''Removes a VM instance from VIM'''
        '''Returns the instance identifier'''
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        print "VIMConnector: Delete a VM instance from VIM " + vm_id
        
        try:
            vim_response = requests.delete(self.url+'/'+self.tenant+'/servers/'+vm_id, headers = self.headers_req)
        except requests.exceptions.RequestException, e:
            print "delete_tenant_vminstance Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])

        #print vim_response.status_code
        if vim_response.status_code == 200:
            print json.dumps(vim_response.json(), indent=4)
            return vim_response.status_code, vm_id
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
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
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        #vms_refreshed = []
        #nets_refreshed = []
        vms_unrefreshed = []
        nets_unrefreshed = []
        for vm_id in vmDict:
            vmDict[vm_id]={'error_msg':None, 'vim_info':None}
            print "VIMConnector refresh_tenant_vms and nets: Getting tenant VM instance information from VIM"
        
            url = self.url+'/'+self.tenant+'/servers/'+ vm_id
            print url
            try:
                vim_response = requests.get(url, headers = self.headers_req)
            except requests.exceptions.RequestException, e:
                print "VIMConnector refresh_tenant_elements. Exception: ", e.args
                vmDict[vm_id]['status'] = "VIM_ERROR"
                vmDict[vm_id]['error_msg'] = str(e)
                vms_unrefreshed.append(vm_id)
                continue
            #print vim_response
            #print vim_response.status_code
            if vim_response.status_code == 200:
                #print vim_response.json()
                #print json.dumps(vim_response.json(), indent=4)
                management_ip = False
                res,http_content = self._format_in(vim_response, new_vminstance_response_schema)
                if res:
                    try:
                        vmDict[vm_id]['status'] = vmStatus2manoFormat[ http_content['server']['status']  ]
                        if http_content['server'].get('last_error'):
                            vmDict[vm_id]['error_msg'] = http_content['server']['last_error']
                        vmDict[vm_id]["vim_info"] = yaml.safe_dump(http_content['server'])
                        vmDict[vm_id]["interfaces"]=[]
                        #get interfaces info
                        url2 = self.url+'/ports?device_id='+ vm_id
                        try:
                            vim_response2 = requests.get(url2, headers = self.headers_req)
                            if vim_response.status_code == 200:
                                client_data = vim_response2.json()
                                for port in client_data.get("ports"):
                                    print "VACAport", port
                                    interface={}
                                    interface['vim_info']  = yaml.safe_dump(port)
                                    interface["mac_address"] = port.get("mac_address")
                                    interface["vim_net_id"] = port["network_id"]
                                    interface["vim_interface_id"] = port["id"]
                                    interface["ip_address"] = port.get("ip_address")
                                    if interface["ip_address"]:
                                        management_ip = True
                                    if interface["ip_address"] == "0.0.0.0":
                                        interface["ip_address"] = None
                                    vmDict[vm_id]["interfaces"].append(interface)
                                
                        except Exception as e:
                            print "VIMConnector refresh_tenant_elements. Port get %s: %s", (type(e).__name__, (str(e) if len(e.args)==0 else str(e.args[0])))

                        if vmDict[vm_id]['status'] == "ACTIVE" and not management_ip:
                            vmDict[vm_id]['status'] = "ACTIVE:NoMgmtIP"
                        
                    except Exception as e:
                        vmDict[vm_id]['status'] = "VIM_ERROR"
                        vmDict[vm_id]['error_msg'] = str(e)
                        vms_unrefreshed.append(vm_id)
                else:
                    vmDict[vm_id]['status'] = "VIM_ERROR"
                    vmDict[vm_id]['error_msg'] = str(http_content)
                    vms_unrefreshed.append(vm_id)
            else:
                #print vim_response.text
                jsonerror = self._format_jsonerror(vim_response)
                print 'VIMConnector refresh_tenant_vms_and_nets. Error in VIM "%s": not possible to get VM instance. HTTP Response: %d. Error: %s' % (self.url, vim_response.status_code, jsonerror)
                if vim_response.status_code == 404: # HTTP_Not_Found
                    vmDict[vm_id]['status'] = "DELETED"
                else:
                    vmDict[vm_id]['status'] = "VIM_ERROR"
                    vmDict[vm_id]['error_msg'] = jsonerror
                    vms_unrefreshed.append(vm_id)
        
        #print "VMs refreshed: %s" % str(vms_refreshed)
        for net_id in netDict:
            netDict[net_id] = {'error_msg':None, 'vim_info':None}
            print "VIMConnector refresh_tenant_vms_and_nets: Getting tenant network from VIM (tenant: " + str(self.tenant) + "): "
            r,c = self.get_tenant_network(net_id)
            if r<0:
                print "VIMconnector refresh_tenant_network. Error getting net_id '%s' status: %s" % (net_id, c)
                if r==-vimconn.HTTP_Not_Found:
                    netDict[net_id]['status'] = "DELETED" #TODO check exit status
                else:
                    netDict[net_id]['status'] = "VIM_ERROR"
                    netDict[net_id]['error_msg'] = c
                    nets_unrefreshed.append(net_id)
            else:
                try: 
                    net_status = netStatus2manoFormat[ c['status'] ]
                    if net_status == "ACTIVE" and not c['admin_state_up']:
                        net_status = "DOWN"
                    netDict[net_id]['status'] = net_status
                    if c.get('last_error'):
                        netDict[net_id]['error_msg'] = c['last_error']
                    netDict[net_id]["vim_info"] = yaml.safe_dump(c)
                except Exception as e:
                    netDict[net_id]['status'] = "VIM_ERROR"
                    netDict[net_id]['error_msg'] = str(e)
                    nets_unrefreshed.append(net_id)

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
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        print "VIMConnector: Action over VM instance from VIM " + vm_id
        
        try:
            if "console" in action_dict:
                return -vimconn.HTTP_Service_Unavailable, "getting console is not available at openvim"
            
            vim_response = requests.post(self.url+'/'+self.tenant+'/servers/'+vm_id+"/action", headers = self.headers_req, data=json.dumps(action_dict) )
        except requests.exceptions.RequestException, e:
            print "action_tenant_vminstance Exception: ", e.args
            return -vimconn.HTTP_Not_Found, str(e.args[0])

        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print "vimconnector.action_tenant_vminstance():", json.dumps(vim_response.json(), indent=4)
            return vim_response.status_code, vm_id
        else:
            #print vim_response.text
            jsonerror = self._format_jsonerror(vim_response)
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
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print "vim get", url, "response:",  vim_response.status_code, vim_response.json()
        #print vim_response.status_code
        #print json.dumps(vim_response.json(), indent=4)
        if vim_response.status_code != 200:
            #TODO: get error
            print 'vimconnector.get_hosts_info error getting host list %d %s' %(vim_response.status_code, vim_response.json())
            return -vim_response.status_code, "Error getting host list"
        
        res,hosts = self._format_in(vim_response, get_hosts_response_schema)
            
        if res==False:
            print "vimconnector.get_hosts_info error parsing GET HOSTS vim response", hosts
            return vimconn.HTTP_Internal_Server_Error, hosts
    #obtain hosts details
        hosts_dict={}
        for host in hosts['hosts']:
            url=self.url+'/hosts/'+host['id']
            try:
                vim_response = requests.get(url)
            except requests.exceptions.RequestException, e:
                print "get_hosts_info Exception: ", e.args
                return -vimconn.HTTP_Not_Found, str(e.args[0])
            print "vim get", url, "response:",  vim_response.status_code, vim_response.json()
            if vim_response.status_code != 200:
                print 'vimconnector.get_hosts_info error getting detailed host %d %s' %(vim_response.status_code, vim_response.json())
                continue
            res,host_detail = self._format_in(vim_response, get_host_detail_response_schema)
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
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print "vim get", url, "response:",  vim_response.status_code, vim_response.json()
        #print vim_response.status_code
        #print json.dumps(vim_response.json(), indent=4)
        if vim_response.status_code != 200:
            #TODO: get error
            print 'vimconnector.get_hosts error getting host list %d %s' %(vim_response.status_code, vim_response.json())
            return -vim_response.status_code, "Error getting host list"
        
        res,hosts = self._format_in(vim_response, get_hosts_response_schema)
            
        if res==False:
            print "vimconnector.get_host error parsing GET HOSTS vim response", hosts
            return vimconn.HTTP_Internal_Server_Error, hosts
    #obtain instances from hosts
        for host in hosts['hosts']:
            url=self.url+'/' + vim_tenant + '/servers?hostId='+host['id']
            try:
                vim_response = requests.get(url)
            except requests.exceptions.RequestException, e:
                print "get_hosts Exception: ", e.args
                return -vimconn.HTTP_Not_Found, str(e.args[0])
            print "vim get", url, "response:",  vim_response.status_code, vim_response.json()
            if vim_response.status_code != 200:
                print 'vimconnector.get_hosts error getting instances at host %d %s' %(vim_response.status_code, vim_response.json())
                continue
            res,servers = self._format_in(vim_response, get_server_response_schema)
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
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print "vim get", url, "response:", vim_response.status_code, vim_response.json()
        #print vim_response.status_code
        #print json.dumps(vim_response.json(), indent=4)
        if vim_response.status_code != 200:
            #TODO: get error
            print 'vimconnector.get_processor_rankings error getting processor rankings %d %s' %(vim_response.status_code, vim_response.json())
            return -vim_response.status_code, "Error getting processor rankings"
        
        res,rankings = self._format_in(vim_response, get_processor_rankings_response_schema)
        return res, rankings['rankings']
    
    def get_image_id_from_path(self, path):
        '''Get the image id from image path in the VIM database'''
        '''Returns:
             0,"Image not found"   if there are no images with that path
             1,image-id            if there is one image with that path
             <0,message            if there was an error (Image not found, error contacting VIM, more than 1 image with that path, etc.) 
        '''
        try:
            self._get_my_tenant()
        except Exception as e:
            return -vimconn.HTTP_Not_Found, str(e)
        url=self.url + '/' + self.tenant + '/images?path='+path
        try:
            vim_response = requests.get(url)
        except requests.exceptions.RequestException, e:
            print "get_image_id_from_path url='%s'Exception: '%s'" % (url, str(e.args))
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print "vim get_image_id_from_path", url, "response:", vim_response.status_code, vim_response.json()
        #print vim_response.status_code
        #print json.dumps(vim_response.json(), indent=4)
        if vim_response.status_code != 200:
            #TODO: get error
            print 'vimconnector.get_image_id_from_path error getting image id from path. Error code: %d Description: %s' %(vim_response.status_code, vim_response.json())
            return -vim_response.status_code, "Error getting image id from path"
        
        res,image = self._format_in(vim_response, get_images_response_schema)
        if not res:
            print "vimconnector.get_image_id_from_path error"
            return -vimconn.HTTP_Bad_Request, image
        if len(image['images'])==0:
            return 0,"Image not found"
        elif len(image['images'])>1:
            print "vimconnector.get_image_id_from_path error. More than one images with the path %s." %(path)
            return -vimconn.HTTP_Internal_Server_Error,"More than one images with that path"
        return 1, image['images'][0]['id']
        


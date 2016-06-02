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
'''
__author__="Alfonso Tierno, Gerardo Garcia"
__date__ ="$26-aug-2014 11:09:29$"

import vimconn
import requests
import json
import yaml
import logging
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

get_image_response_schema = {
    "title":"openvim images response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "image":{
            "type":"object",
            "properties":{
                "id":   id_schema,
                "name": name_schema,
            },
            "required": ["id", "name"],
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
    def __init__(self, uuid, name, tenant_id, tenant_name, url, url_admin=None, user=None, passwd=None,log_level="DEBUG",config={}):
        vimconn.vimconnector.__init__(self, uuid, name, tenant_id, tenant_name, url, url_admin, user, passwd, log_level, config)
        self.tenant = None
        self.headers_req = {'content-type': 'application/json'}
        self.logger = logging.getLogger('mano.vim.openvim')
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

        url = self.url+'/tenants?name='+ self.tenant_name
        self.logger.info("Getting VIM tenant_id GET %s", url)
        vim_response = requests.get(url, headers = self.headers_req)
        self._check_http_request_response(vim_response)
        try:
            tenant_list = vim_response.json()["tenants"]
            if len(tenant_list) == 0:
                raise vimconn.vimconnNotFoundException("No tenant found for name '%s'" % str(self.tenant_name))
            elif len(tenant_list) > 1:
                raise vimconn.vimconnConflictException ("More that one tenant found for name '%s'" % str(self.tenant_name))
            self.tenant = tenant_list[0]["id"]
            return self.tenant
        except Exception as e:
            raise vimconn.vimconnUnexpectedResponse("Get VIM tenant {} '{}'".format(type(e).__name__, str(e)))

    def _format_jsonerror(self,http_response):
        #DEPRECATED, to delete in the future
        try:
            data = http_response.json()
            return data["error"]["description"]
        except:
            return http_response.text

    def _format_in(self, http_response, schema):
        #DEPRECATED, to delete in the future
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
        
    def _format_request_exception(self, request_exception):
        '''Transform a request exception into a vimconn exception'''
        if isinstance(request_exception, js_e.ValidationError):
            raise vimconn.vimconnUnexpectedResponse("jsonschema exception '{}' at '{}'".format(request_exception.message, request_exception.path))            
        elif isinstance(request_exception, requests.exceptions.HTTPError):
            raise vimconn.vimconnUnexpectedResponse(type(request_exception).__name__ + ": " + str(request_exception))
        else:
            raise vimconn.vimconnConnectionException(type(request_exception).__name__ + ": " + str(request_exception))

    def _check_http_request_response(self, request_response):
        '''Raise a vimconn exception if the response is not Ok'''
        if request_response.status_code >= 200 and  request_response.status_code < 300:
            return
        if request_response.status_code == vimconn.HTTP_Unauthorized:
            raise vimconn.vimconnAuthException(request_response.text)
        elif request_response.status_code == vimconn.HTTP_Not_Found:
            raise vimconn.vimconnNotFoundException(request_response.text)
        elif request_response.status_code == vimconn.HTTP_Conflict:
            raise vimconn.vimconnConflictException(request_response.text)
        else: 
            raise vimconn.vimconnUnexpectedResponse("VIM HTTP_response {}, {}".format(request_response.status_code, str(request_response.text)))

    def new_tenant(self,tenant_name,tenant_description):
        '''Adds a new tenant to VIM with this name and description, returns the tenant identifier'''
        #print "VIMConnector: Adding a new tenant to VIM"
        payload_dict = {"tenant": {"name":tenant_name,"description": tenant_description, "enabled": True}}
        payload_req = json.dumps(payload_dict)
        try:
            url = self.url_admin+'/tenants'
            self.logger.info("Adding a new tenant %s", url)
            vim_response = requests.post(url, headers = self.headers_req, data=payload_req)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            response = vim_response.json()
            js_v(response, new_tenant_response_schema)
            #r = self._remove_extra_items(response, new_tenant_response_schema)
            #if r is not None: 
            #    self.logger.warn("Warning: remove extra items %s", str(r))
            tenant_id = response['tenant']['id']
            return tenant_id
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)

    def delete_tenant(self,tenant_id):
        '''Delete a tenant from VIM. Returns the old tenant identifier'''
        try:
            url = self.url_admin+'/tenants/'+tenant_id
            self.logger.info("Delete a tenant DELETE %s", url)
            vim_response = requests.delete(url, headers = self.headers_req)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            return tenant_id
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)

    def get_tenant_list(self, filter_dict={}):
        '''Obtain tenants of VIM
        filter_dict can contain the following keys:
            name: filter by tenant name
            id: filter by tenant uuid/id
            <other VIM specific>
        Returns the tenant list of dictionaries: [{'name':'<name>, 'id':'<id>, ...}, ...]
        '''
        filterquery=[]
        filterquery_text=''
        for k,v in filter_dict.iteritems():
            filterquery.append(str(k)+'='+str(v))
        if len(filterquery)>0:
            filterquery_text='?'+ '&'.join(filterquery)
        try:
            url = self.url+'/tenants'+filterquery_text
            self.logger.info("get_tenant_list GET %s", url)
            vim_response = requests.get(url, headers = self.headers_req)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            return vim_response.json()["tenants"]
        except requests.exceptions.RequestException as e:
            self._format_request_exception(e)

    def new_network(self,net_name,net_type, shared=False, **vim_specific):
        '''Adds a tenant network to VIM'''
        '''Returns the network identifier'''
        try:
            self._get_my_tenant()
            if net_type=="bridge":
                net_type="bridge_data"
            payload_req = {"name": net_name, "type": net_type, "tenant_id": self.tenant, "shared": shared}
            payload_req.update(vim_specific)
            url = self.url+'/networks'
            self.logger.info("Adding a new network POST: %s  DATA: %s", url, str(payload_req))
            vim_response = requests.post(url, headers = self.headers_req, data=json.dumps({"network": payload_req}) )
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            response = vim_response.json()
            js_v(response, new_network_response_schema)
            #r = self._remove_extra_items(response, new_network_response_schema)
            #if r is not None: 
            #    self.logger.warn("Warning: remove extra items %s", str(r))
            network_id = response['network']['id']
            return network_id
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)
        
    def get_network_list(self, filter_dict={}):
        '''Obtain tenant networks of VIM
        Filter_dict can be:
            name: network name
            id: network uuid
            public: boolean
            tenant_id: tenant
            admin_state_up: boolean
            status: 'ACTIVE'
        Returns the network list of dictionaries
        '''
        try:
            if 'tenant_id' not in filter_dict:
                filter_dict["tenant_id"] = self._get_my_tenant()
            elif not filter_dict["tenant_id"]:
                del filter_dict["tenant_id"]
            filterquery=[]
            filterquery_text=''
            for k,v in filter_dict.iteritems():
                filterquery.append(str(k)+'='+str(v))
            if len(filterquery)>0:
                filterquery_text='?'+ '&'.join(filterquery)
            url = self.url+'/networks'+filterquery_text
            self.logger.info("Getting network list GET %s", url)
            vim_response = requests.get(url, headers = self.headers_req)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            response = vim_response.json()
            return response['networks']
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)

    def get_network(self, net_id):
        '''Obtain network details of network id'''
        try:
            url = self.url+'/networks/'+net_id
            self.logger.info("Getting network GET %s", url)
            vim_response = requests.get(url, headers = self.headers_req)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            response = vim_response.json()
            return response['network']
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)
            
    def delete_network(self, net_id):
        '''Deletes a tenant network from VIM'''
        '''Returns the network identifier'''
        try:
            self._get_my_tenant()
            url = self.url+'/networks/'+net_id
            self.logger.info("Deleting VIM network DELETE %s", url)
            vim_response = requests.delete(url, headers=self.headers_req)
            self._check_http_request_response(vim_response)
            #self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            return net_id
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)

    def get_flavor(self, flavor_id):
        '''Obtain flavor details from the  VIM'''
        try:
            self._get_my_tenant()
            url = self.url+'/'+self.tenant+'/flavors/'+flavor_id
            self.logger.info("Getting flavor GET %s", url)
            vim_response = requests.get(url, headers = self.headers_req)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            response = vim_response.json()
            js_v(response, get_flavor_response_schema)
            r = self._remove_extra_items(response, get_flavor_response_schema)
            if r is not None: 
                self.logger.warn("Warning: remove extra items %s", str(r))
            return response['flavor']
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)
        
    def new_flavor(self, flavor_data):
        '''Adds a tenant flavor to VIM'''
        '''Returns the flavor identifier'''
        try:
            self._get_my_tenant()
            payload_req = json.dumps({'flavor': flavor_data})
            url = self.url+'/'+self.tenant+'/flavors'
            self.logger.info("Adding a new VIM flavor POST %s", url)
            vim_response = requests.post(url, headers = self.headers_req, data=payload_req)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            response = vim_response.json()
            js_v(response, new_flavor_response_schema)
            r = self._remove_extra_items(response, new_flavor_response_schema)
            if r is not None: 
                self.logger.warn("Warning: remove extra items %s", str(r))
            flavor_id = response['flavor']['id']
            return flavor_id
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)

    def delete_flavor(self,flavor_id):
        '''Deletes a tenant flavor from VIM'''
        '''Returns the old flavor_id'''
        try:
            self._get_my_tenant()
            url = self.url+'/'+self.tenant+'/flavors/'+flavor_id
            self.logger.info("Deleting VIM flavor DELETE %s", url)
            vim_response = requests.delete(url, headers=self.headers_req)
            self._check_http_request_response(vim_response)
            #self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            return flavor_id
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)

    def get_image(self, image_id):
        '''Obtain image details from the  VIM'''
        try:
            self._get_my_tenant()
            url = self.url+'/'+self.tenant+'/images/'+image_id
            self.logger.info("Getting image GET %s", url)
            vim_response = requests.get(url, headers = self.headers_req)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            response = vim_response.json()
            js_v(response, get_image_response_schema)
            r = self._remove_extra_items(response, get_image_response_schema)
            if r is not None: 
                self.logger.warn("Warning: remove extra items %s", str(r))
            return response['image']
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)

    def new_image(self,image_dict):
        ''' Adds a tenant image to VIM, returns image_id'''
        try:
            self._get_my_tenant()
            new_image_dict={'name': image_dict['name']}
            if image_dict.get('description'):
                new_image_dict['description'] = image_dict['description']
            if image_dict.get('metadata'):
                new_image_dict['metadata'] = yaml.load(image_dict['metadata'])
            if image_dict.get('location'):
                new_image_dict['path'] = image_dict['location']
            payload_req = json.dumps({"image":new_image_dict})
            url=self.url + '/' + self.tenant + '/images'
            self.logger.info("Adding a new VIM image POST %s", url)
            vim_response = requests.post(url, headers = self.headers_req, data=payload_req)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            response = vim_response.json()
            js_v(response, new_image_response_schema)
            r = self._remove_extra_items(response, new_image_response_schema)
            if r is not None: 
                self.logger.warn("Warning: remove extra items %s", str(r))
            image_id = response['image']['id']
            return image_id
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)
            
    def delete_image(self, image_id):
        '''Deletes a tenant image from VIM'''
        '''Returns the deleted image_id'''
        try:
            self._get_my_tenant()
            url = self.url + '/'+ self.tenant +'/images/'+image_id
            self.logger.info("Deleting VIM image DELETE %s", url)
            vim_response = requests.delete(url, headers=self.headers_req)
            self._check_http_request_response(vim_response)
            #self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            return image_id
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)

    
    def get_image_id_from_path(self, path):
        '''Get the image id from image path in the VIM database'''
        try:
            self._get_my_tenant()
            url=self.url + '/' + self.tenant + '/images?path='+path
            self.logger.info("Getting images GET %s", url)
            vim_response = requests.get(url)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            response = vim_response.json()
            js_v(response, get_images_response_schema)
            #r = self._remove_extra_items(response, get_images_response_schema)
            #if r is not None: 
            #    self.logger.warn("Warning: remove extra items %s", str(r))
            if len(response['images'])==0:
                raise vimconn.vimconnNotFoundException("Image not found at VIM with path '%s'", path)
            elif len(response['images'])>1:
                raise vimconn.vimconnConflictException("More than one image found at VIM with path '%s'", path)
            return response['images'][0]['id']
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)

    def new_vminstancefromJSON(self, vm_data):
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
            print "new_vminstancefromJSON Exception: ", e.args
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
        Returns the instance identifier
        '''
        try:
            self._get_my_tenant()
#            net_list = []
#            for k,v in net_dict.items():
#                print k,v
#                net_list.append('{"name":"' + k + '", "uuid":"' + v + '"}')
#            net_list_string = ', '.join(net_list) 
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
            url = self.url+'/'+self.tenant+'/servers'
            self.logger.info("Adding a new vm POST %s DATA %s", url, payload_req)
            vim_response = requests.post(url, headers = self.headers_req, data=payload_req)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            response = vim_response.json()
            js_v(response, new_vminstance_response_schema)
            #r = self._remove_extra_items(response, new_vminstance_response_schema)
            #if r is not None: 
            #    self.logger.warn("Warning: remove extra items %s", str(r))
            vminstance_id = response['server']['id']

            #connect data plane interfaces to network
            for net in net_list:
                if net["type"]=="virtual":
                    if not net.get("net_id"):
                        continue
                    for iface in response['server']['networks']:
                        if "name" in net:
                            if net["name"]==iface["name"]:
                                net["vim_id"] = iface['iface_id']
                                break
                        elif "net_id" in net:
                            if net["net_id"]==iface["net_id"]:
                                net["vim_id"] = iface['iface_id']
                                break
                else: #dataplane
                    for numa in response['server'].get('extended',{}).get('numas',() ):
                        for iface in numa.get('interfaces',() ):
                            if net['name'] == iface['name']:
                                net['vim_id'] = iface['iface_id']
                                #Code bellow is not needed, current openvim connect dataplane interfaces 
                                #if net.get("net_id"):
                                ##connect dataplane interface
                                #    result, port_id = self.connect_port_network(iface['iface_id'], net["net_id"])
                                #    if result < 0:
                                #        error_text = "Error attaching port %s to network %s: %s." % (iface['iface_id'], net["net_id"], port_id)
                                #        print "new_vminstance: " + error_text
                                #        self.delete_vminstance(vminstance_id)
                                #        return result, error_text
                                break
        
            return vminstance_id
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)
        
    def get_vminstance(self, vm_id):
        '''Returns the VM instance information from VIM'''
        try:
            self._get_my_tenant()
            url = self.url+'/'+self.tenant+'/servers/'+vm_id
            self.logger.info("Getting vm GET %s", url)
            vim_response = requests.get(url, headers = self.headers_req)
            vim_response = requests.get(url, headers = self.headers_req)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            response = vim_response.json()
            js_v(response, new_vminstance_response_schema)
            #r = self._remove_extra_items(response, new_vminstance_response_schema)
            #if r is not None: 
            #    self.logger.warn("Warning: remove extra items %s", str(r))
            return response['server']
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)
        
    def delete_vminstance(self, vm_id):
        '''Removes a VM instance from VIM, returns the deleted vm_id'''
        try:
            self._get_my_tenant()
            url = self.url+'/'+self.tenant+'/servers/'+vm_id
            self.logger.info("Deleting VIM vm DELETE %s", url)
            vim_response = requests.delete(url, headers=self.headers_req)
            self._check_http_request_response(vim_response)
            #self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            return vm_id
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)

    def refresh_vms_status(self, vm_list):
        '''Refreshes the status of the virtual machines'''
        try:
            self._get_my_tenant()
        except requests.exceptions.RequestException as e:
            self._format_request_exception(e)
        vm_dict={}
        for vm_id in vm_list:
            vm={}
            #print "VIMConnector refresh_tenant_vms and nets: Getting tenant VM instance information from VIM"
            try:
                url = self.url+'/'+self.tenant+'/servers/'+ vm_id
                self.logger.info("Getting vm GET %s", url)
                vim_response = requests.get(url, headers = self.headers_req)
                self._check_http_request_response(vim_response)
                response = vim_response.json()
                js_v(response, new_vminstance_response_schema)
                if response['server']['status'] in vmStatus2manoFormat:
                    vm['status'] = vmStatus2manoFormat[ response['server']['status']  ]
                else:
                    vm['status'] = "OTHER"
                    vm['error_msg'] = "VIM status reported " + response['server']['status']
                if response['server'].get('last_error'):
                    vm['error_msg'] = response['server']['last_error']
                vm["vim_info"] = yaml.safe_dump(response['server'])
                #get interfaces info
                try:
                    management_ip = False
                    url2 = self.url+'/ports?device_id='+ vm_id
                    self.logger.info("Getting PORTS GET %s", url2)
                    vim_response2 = requests.get(url2, headers = self.headers_req)
                    self._check_http_request_response(vim_response2)
                    client_data = vim_response2.json()
                    if isinstance(client_data.get("ports"), list):
                        vm["interfaces"]=[]
                    for port in client_data.get("ports"):
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
                        vm["interfaces"].append(interface)
                        
                except Exception as e:
                    self.logger.error("refresh_vms_and_nets. Port get %s: %s", type(e).__name__, str(e))

                if vm['status'] == "ACTIVE" and not management_ip:
                    vm['status'] = "ACTIVE:NoMgmtIP"
                    
            except vimconn.vimconnNotFoundException as e:
                self.logger.error("Exception getting vm status: %s", str(e))
                vm['status'] = "DELETED"
                vm['error_msg'] = str(e)
            except (requests.exceptions.RequestException, js_e.ValidationError, vimconn.vimconnException) as e:
                self.logger.error("Exception getting vm status: %s", str(e))
                vm['status'] = "VIM_ERROR"
                vm['error_msg'] = str(e)
            vm_dict[vm_id] = vm
        return vm_dict

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
        try:
            self._get_my_tenant()
        except requests.exceptions.RequestException as e:
            self._format_request_exception(e)
        
        net_dict={}
        for net_id in net_list:
            net = {}
            #print "VIMConnector refresh_tenant_vms_and_nets: Getting tenant network from VIM (tenant: " + str(self.tenant) + "): "
            try:
                net_vim = self.get_network(net_id)
                if net_vim['status'] in netStatus2manoFormat:
                    net["status"] = netStatus2manoFormat[ net_vim['status'] ]
                else:
                    net["status"] = "OTHER"
                    net["error_msg"] = "VIM status reported " + net_vim['status']
                    
                if net["status"] == "ACTIVE" and not net_vim['admin_state_up']:
                    net["status"] = "DOWN"
                if net_vim.get('last_error'):
                    net['error_msg'] = net_vim['last_error']
                net["vim_info"] = yaml.safe_dump(net_vim)
            except vimconn.vimconnNotFoundException as e:
                self.logger.error("Exception getting net status: %s", str(e))
                net['status'] = "DELETED"
                net['error_msg'] = str(e)
            except (requests.exceptions.RequestException, js_e.ValidationError, vimconn.vimconnException) as e:
                self.logger.error("Exception getting net status: %s", str(e))
                net['status'] = "VIM_ERROR"
                net['error_msg'] = str(e)
            net_dict[net_id] = net
        return net_dict
    
    def action_vminstance(self, vm_id, action_dict):
        '''Send and action over a VM instance from VIM'''
        '''Returns the status'''
        try:
            self._get_my_tenant()
            if "console" in action_dict:
                raise vimconn.vimconnException("getting console is not available at openvim", http_code=vimconn.HTTP_Service_Unavailable)
            url = self.url+'/'+self.tenant+'/servers/'+vm_id+"/action"
            self.logger.info("Action over VM instance POST %s", url)
            vim_response = requests.post(url, headers = self.headers_req, data=json.dumps(action_dict) )
            self._check_http_request_response(vim_response)
            return vm_id
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)

#NOT USED METHODS in current version        
  
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
    
    def new_host(self, host_data):
        '''Adds a new host to VIM'''
        '''Returns status code of the VIM response'''
        payload_req = host_data
        try:
            url = self.url_admin+'/hosts'
            self.logger.info("Adding a new host POST %s", url)
            vim_response = requests.post(url, headers = self.headers_req, data=payload_req)
            self._check_http_request_response(vim_response)
            self.logger.debug(vim_response.text)
            #print json.dumps(vim_response.json(), indent=4)
            response = vim_response.json()
            js_v(response, new_host_response_schema)
            r = self._remove_extra_items(response, new_host_response_schema)
            if r is not None: 
                self.logger.warn("Warning: remove extra items %s", str(r))
            host_id = response['host']['id']
            return host_id
        except (requests.exceptions.RequestException, js_e.ValidationError) as e:
            self._format_request_exception(e)
    
    def new_external_port(self, port_data):
        '''Adds a external port to VIM'''
        '''Returns the port identifier'''
        #TODO change to logging exception code policies
        print "VIMConnector: Adding a new external port"
        payload_req = port_data
        try:
            vim_response = requests.post(self.url_admin+'/ports', headers = self.headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            self.logger.error("new_external_port Exception: ", str(e))
            return -vimconn.HTTP_Not_Found, str(e.args[0])
        print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
        #print vim_response.json()
        #print json.dumps(vim_response.json(), indent=4)
            res, http_content = self._format_in(vim_response, new_port_response_schema)
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
        #TODO change to logging exception code policies
        print "VIMConnector: Adding external shared network to VIM (type " + net_type + "): "+ net_name
        
        payload_req = '{"network":{"name": "' + net_name + '","shared":true,"type": "' + net_type + '"}}'
        try:
            vim_response = requests.post(self.url+'/networks', headers = self.headers_req, data=payload_req)
        except requests.exceptions.RequestException, e:
            self.logger.error( "new_external_network Exception: ", e.args)
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
        #TODO change to logging exception code policies
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
        


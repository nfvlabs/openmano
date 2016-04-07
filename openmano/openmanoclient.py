#!/usr/bin/env python3
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
openmano python client used to interact with openmano-server  
'''
__author__="Alfonso Tierno"
__date__ ="$09-Mar-2016 09:09:48$"
__version__="0.0.1-r467"
version_date="Mar 2016"

import requests
import json
import yaml
import logging
import sys
if  sys.version_info.major == 3:
    from urllib.parse import quote
elif sys.version_info.major == 2:
    from urllib import quote

class OpenmanoException(Exception):
    '''Common Exception for all openmano client exceptions'''

class OpenmanoBadParamsException(OpenmanoException):
    '''Bad or missing input parameters'''

class OpenmanoResponseException(OpenmanoException):
    '''Unexpected response from openmano server'''

class OpenmanoNotFoundException(OpenmanoException):
    '''Not found at server'''

# class vnf():
#     def __init__(self, message):
#         print "Error: %s" %message
#         print
#         self.print_usage()
#         #self.print_help()
#         print
#         print "Type 'openmano -h' for help"

class openmanoclient():
    headers_req = {'Accept': 'application/yaml', 'content-type': 'application/yaml'}
    
    def __init__(self, **kwargs):
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")
        self.endpoint_url = kwargs.get("endpoint_url")
        self.tenant_id = kwargs.get("tenant_id")
        self.tenant_name = kwargs.get("tenant_name")
        self.tenant = None
        self.datacenter_id = kwargs.get("datacenter_id")
        self.datacenter_name = kwargs.get("datacenter_name")
        self.datacenter = None
        self.logger = logging.getLogger('manoclient')
        if kwargs.get("debug"):
            self.logger.setLevel(logging.DEBUG)
        
    def __getitem__(self, index):
        if index=='tenant_name':
            return self.tenant_name
        elif index=='tenant_id':
            return self.tenant_id
        elif index=='datacenter_name':
            return self.datacenter_name
        elif index=='datacenter_id':
            return self.datacenter_id
        elif index=='username':
            return self.username
        elif index=='password':
            return self.password
        elif index=='endpoint_url':
            return self.endpoint_url
        else:
            raise KeyError("Invalid key '%s'" %str(index))
        
    def __setitem__(self,index, value):
        if index=='tenant_name':
            self.tenant_name = value
        elif index=='tenant_id':
            self.tenant_id = value
        elif index=='datacenter_name':
            self.datacenter_name = value
        elif index=='datacenter_id':
            self.datacenter_id = value
        elif index=='username':
            self.username = value
        elif index=='password':
            self.password = value
        elif index=='endpoint_url':
            self.endpoint_url = value
        else:
            raise KeyError("Invalid key '%s'" %str(index)) 
        self.tenant = None # force to reload tenant with different credentials
        self.datacenter = None # force to reload datacenter with different credentials
    
    def _parse(self, descriptor, descriptor_format, response=False):
        #try yaml
        if descriptor_format and descriptor_format != "json" and descriptor_format != "yaml":
            raise  OpenmanoBadParamsException("'descriptor_format' must be a 'json' or 'yaml' text")
        if descriptor_format != "json":
            try:
                return yaml.load(descriptor)
            except yaml.YAMLError as exc:
                error_pos = ""
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    error_pos = " at line:{} column:{}s".format(mark.line+1, mark.column+1)
                error_text = "yaml format error" + error_pos
        elif descriptor_format != "yaml":
            try:
                return json.loads(descriptor) 
            except Exception as e:
                if response:
                    error_text = "json format error" + str(e)

        if response:
            raise OpenmanoResponseException(error_text)
        raise  OpenmanoBadParamsException(error_text)
    
    def _parse_yaml(self, descriptor, response=False):
        try:
            return yaml.load(descriptor)
        except yaml.YAMLError as exc:
            error_pos = ""
            if hasattr(exc, 'problem_mark'):
                mark = exc.problem_mark
                error_pos = " at line:{} column:{}s".format(mark.line+1, mark.column+1)
            error_text = "yaml format error" + error_pos
            if response:
                raise OpenmanoResponseException(error_text)
            raise  OpenmanoBadParamsException(error_text)

    
    def _get_item_uuid(self, item, item_id=None, item_name=None, all_tenants=False):
        if all_tenants == None:
            tenant_text = ""
        elif all_tenants == False:
            tenant_text = "/" + self.tenant
        else:
            tenant_text = "/any"
        URLrequest = "{}{}/{}".format(self.endpoint_url, tenant_text, item)
        self.logger.debug("GET %s", URLrequest )
        mano_response = requests.get(URLrequest, headers=self.headers_req)
        self.logger.debug("openmano response: %s", mano_response.text )
        content = self._parse_yaml(mano_response.text, response=True)
        #print content
        found = 0
        if not item_id and not item_name:
            raise OpenmanoResponseException("Missing either {0}_name or {0}_id".format(item[:-1]))
        for i in content[item]:
            if item_id and i["uuid"] == item_id:
                return item_id
            elif item_name and i["name"] == item_name:
                uuid = i["uuid"]
                found += 1
            
        if found == 0:
            if item_id:
                raise OpenmanoNotFoundException("No {} found with id '{}'".format(item[:-1], item_id))
            else:
                #print(item, item_name)
                raise OpenmanoNotFoundException("No {} found with name '{}'".format(item[:-1], item_name) )
        elif found > 1:
            raise OpenmanoNotFoundException("{} {} found with name '{}'. uuid must be used".format(found, item, item_name))
        return uuid

    def _get_item(self, item, uuid=None, name=None, all_tenants=False):
        if all_tenants:
            tenant_text = "/any"
        elif all_tenants==None:
            tenant_text = ""
        else:
            tenant_text = "/"+self._get_tenant()
        if not uuid:
            #check that exist
            uuid = self._get_item_uuid(item, uuid, name, all_tenants)
        
        URLrequest = "{}{}/{}/{}".format(self.endpoint_url, tenant_text, item, uuid)
        self.logger.debug("GET %s", URLrequest )
        mano_response = requests.get(URLrequest, headers=self.headers_req)
        self.logger.debug("openmano response: %s", mano_response.text )
    
        content = self._parse_yaml(mano_response.text, response=True)
        if mano_response.status_code==200:
            return content
        else:
            raise OpenmanoResponseException(str(content))        

    def _get_tenant(self):
        if not self.tenant:
            self.tenant = self._get_item_uuid("tenants", self.tenant_id, self.tenant_name, None)
        return self.tenant
    
    def _get_datacenter(self):
        if not self.tenant:
            self._get_tenant()
        if not self.datacenter:
            self.datacenter = self._get_item_uuid("datacenters", self.datacenter_id, self.datacenter_name, False)
        return self.datacenter

    def _create_item(self, item, descriptor, all_tenants=False):
        if all_tenants:
            tenant_text = "/any"
        elif all_tenants==None:
            tenant_text = ""
        else:
            tenant_text = "/"+self._get_tenant()
        payload_req = yaml.safe_dump(descriptor)
            
        #print payload_req
            
        URLrequest = "{}{}/{}".format(self.endpoint_url, tenant_text, item)
        self.logger.debug("openmano POST %s %s", URLrequest, payload_req)
        mano_response = requests.post(URLrequest, headers = self.headers_req, data=payload_req)
        self.logger.debug("openmano response: %s", mano_response.text )
    
        content = self._parse_yaml(mano_response.text, response=True)
        if mano_response.status_code==200:
            return content
        else:
            raise OpenmanoResponseException(str(content))        

    def _del_item(self, item, uuid=None, name=None, all_tenants=False):
        if all_tenants:
            tenant_text = "/any"
        elif all_tenants==None:
            tenant_text = ""
        else:
            tenant_text = "/"+self._get_tenant()
        if not uuid:
            #check that exist
            uuid = self._get_item_uuid(item, uuid, name, all_tenants)
        
        URLrequest = "{}{}/{}/{}".format(self.endpoint_url, tenant_text, item, uuid)
        self.logger.debug("DELETE %s", URLrequest )
        mano_response = requests.delete(URLrequest, headers = self.headers_req)
        self.logger.debug("openmano response: %s", mano_response.text )
    
        content = self._parse_yaml(mano_response.text, response=True)
        if mano_response.status_code==200:
            return content
        else:
            raise OpenmanoResponseException(str(content))        
    
    def _list_item(self, item, all_tenants=False, filter_dict=None):
        if all_tenants:
            tenant_text = "/any"
        elif all_tenants==None:
            tenant_text = ""
        else:
            tenant_text = "/"+self._get_tenant()
        
        URLrequest = "{}{}/{}".format(self.endpoint_url, tenant_text, item)
        separator="?"
        if filter_dict:
            for k in filter_dict:
                URLrequest += separator + quote(str(k)) + "=" + quote(str(filter_dict[k])) 
                separator = "&"
        self.logger.debug("openmano GET %s", URLrequest)
        mano_response = requests.get(URLrequest, headers=self.headers_req)
        self.logger.debug("openmano response: %s", mano_response.text )
    
        content = self._parse_yaml(mano_response.text, response=True)
        if mano_response.status_code==200:
            return content
        else:
            raise OpenmanoResponseException(str(content))        

    def _edit_item(self, item, descriptor, uuid=None, name=None, all_tenants=False):
        if all_tenants:
            tenant_text = "/any"
        elif all_tenants==None:
            tenant_text = ""
        else:
            tenant_text = "/"+self._get_tenant()

        if not uuid:
            #check that exist
            uuid = self._get_item_uuid("tenants", uuid, name, all_tenants)
        
        payload_req = yaml.safe_dump(descriptor)
            
        #print payload_req
            
        URLrequest = "{}{}/{}/{}".format(self.endpoint_url, tenant_text, item, uuid)
        self.logger.debug("openmano PUT %s %s", URLrequest, payload_req)
        mano_response = requests.put(URLrequest, headers = self.headers_req, data=payload_req)
        self.logger.debug("openmano response: %s", mano_response.text )
    
        content = self._parse_yaml(mano_response.text, response=True)
        if mano_response.status_code==200:
            return content
        else:
            raise OpenmanoResponseException(str(content))        

    #TENANTS
    def list_tenants(self, **kwargs):
        '''Obtain a list of tenants
        Params: can be filtered by 'uuid','name','description'
        Return: Raises an exception on error
                Obtain a dictionary with format {'tenants':[{tenant1_info},{tenant2_info},...]}}
        '''
        return self._list_item("tenants", all_tenants=None, filter_dict=kwargs)

    def get_tenant(self, uuid=None, name=None):
        '''Obtain the information of a tenant
        Params: uuid or/and name. If only name is supplied, there must be only one or an exception is raised
        Return: Raises an exception on error, not found, found several
                Obtain a dictionary with format {'tenant':{tenant_info}}
        '''
        return self._get_item("tenants", uuid, name, all_tenants=None)

    def delete_tenant(self, uuid=None, name=None):
        '''Delete a tenant
        Params: uuid or/and name. If only name is supplied, there must be only one or an exception is raised
        Return: Raises an exception on error, not found, found several
                Obtain a dictionary with format {'result': text indicating deleted}
        '''
        return self._del_item("tenants", uuid, name, all_tenants=None)

    def create_tenant(self, descriptor=None, descriptor_format=None, name=None, description=None):
        '''Creates a tenant
        Params: must supply a descriptor or/and just a name
            descriptor: with format {'tenant':{new_tenant_info}}
                newtenant_info must contain 'name', and optionally 'description'
                must be a dictionary or a json/yaml text.
            name: the tenant name. Overwrite descriptor name if any
            description: tenant descriptor.. Overwrite descriptor description if any
        Return: Raises an exception on error
                Obtain a dictionary with format {'tenant':{new_tenant_info}}
        '''
        if isinstance(descriptor, str):
            descriptor = self._parse(descriptor, descriptor_format)
        elif descriptor:
            pass
        elif name:
            descriptor={"tenant": {"name": name}}
        else:
            raise OpenmanoBadParamsException("Missing descriptor")

        if 'tenant' not in descriptor or len(descriptor)!=1:
            raise OpenmanoBadParamsException("Descriptor must contain only one 'tenant' field")
        if name:
            descriptor['tenant']['name'] = name
        if description:
            descriptor['tenant']['description'] = description

        return self._create_item("tenants", descriptor, all_tenants=None)

    def edit_tenant(self, uuid=None, name=None, descriptor=None, descriptor_format=None, new_name=None, new_description=None):
        '''Edit the parameters of a tenant
        Params: must supply a descriptor or/and a new_name or new_description
            uuid or/and name. If only name is supplied, there must be only one or an exception is raised
            descriptor: with format {'tenant':{params to change info}}
                must be a dictionary or a json/yaml text.
            name: the tenant name. Overwrite descriptor name if any
            description: tenant descriptor.. Overwrite descriptor description if any
        Return: Raises an exception on error, not found or found several
                Obtain a dictionary with format {'tenant':{newtenant_info}}
        '''

        if isinstance(descriptor, str):
            descriptor = self.parse(descriptor, descriptor_format)
        elif descriptor:
            pass
        elif new_name or new_description:
            descriptor={"tenant": {}}
        else:
            raise OpenmanoBadParamsException("Missing descriptor")

        if 'tenant' not in descriptor or len(descriptor)!=1:
            raise OpenmanoBadParamsException("Descriptor must contain only one 'tenant' field")
        if new_name:
            descriptor['tenant']['name'] = new_name
        if new_description:
            descriptor['tenant']['description'] = new_description

        return self._edit_item("tenants", descriptor, uuid, name, all_tenants=None)

    #DATACENTERS

    def list_datacenters(self, all_tenants=False, **kwargs):
        '''Obtain a list of datacenters, that are the VIM information at openmano
        Params: can be filtered by 'uuid','name','vim_url','type'
        Return: Raises an exception on error
                Obtain a dictionary with format {'datacenters':[{datacenter1_info},{datacenter2_info},...]}}
        '''
        return self._list_item("datacenters", all_tenants, filter_dict=kwargs)

    def get_datacenter(self, uuid=None, name=None, all_tenants=False):
        '''Obtain the information of a datacenter
        Params: uuid or/and name. If only name is supplied, there must be only one or an exception is raised
        Return: Raises an exception on error, not found, found several
                Obtain a dictionary with format {'datacenter':{datacenter_info}}
        '''
        return self._get_item("datacenters", uuid, name, all_tenants)

    def delete_datacenter(self, uuid=None, name=None):
        '''Delete a datacenter
        Params: uuid or/and name. If only name is supplied, there must be only one or an exception is raised
        Return: Raises an exception on error, not found, found several, not free
                Obtain a dictionary with format {'result': text indicating deleted}
        '''
        return self._del_item("datacenters", uuid, name, all_tenants=True)

    def create_datacenter(self, descriptor=None, descriptor_format=None, name=None, vim_url=None, **kwargs):
#, type="openvim", public=False, description=None):
        '''Creates a datacenter
        Params: must supply a descriptor or/and just a name and vim_url
            descriptor: with format {'datacenter':{new_datacenter_info}}
                newdatacenter_info must contain 'name', 'vim_url', and optionally 'description'
                must be a dictionary or a json/yaml text.
            name: the datacenter name. Overwrite descriptor name if any
            vim_url: the datacenter URL. Overwrite descriptor vim_url if any
            vim_url_admin: the datacenter URL for administrative issues. Overwrite descriptor vim_url if any
            vim_type: the datacenter type, can be openstack or openvim. Overwrite descriptor type if any
            public: boolean, by default not public
            description: datacenter description. Overwrite descriptor description if any
            config: dictionary with extra configuration for the concrete datacenter
        Return: Raises an exception on error
                Obtain a dictionary with format {'datacenter':{new_datacenter_info}}
        '''
        if isinstance(descriptor, str):
            descriptor = self.parse(descriptor, descriptor_format)
        elif descriptor:
            pass
        elif name and vim_url:
            descriptor={"datacenter": {"name": name, "vim_url": vim_url}}
        else:
            raise OpenmanoBadParamsException("Missing descriptor, or name and vim_url")
        
        if 'datacenter' not in descriptor or len(descriptor)!=1:
            raise OpenmanoBadParamsException("Descriptor must contain only one 'datacenter' field")
        if name:
            descriptor['datacenter']['name'] = name
        if vim_url:
            descriptor['datacenter']['vim_url'] = vim_url
        for param in kwargs:
            descriptor['datacenter'][param] = kwargs[param]

        return self._create_item("datacenters", descriptor, all_tenants=None)

    def edit_datacenter(self, uuid=None, name=None, descriptor=None, descriptor_format=None, all_tenants=False, **kwargs):
        '''Edit the parameters of a datacenter
        Params: must supply a descriptor or/and a parameter to change
            uuid or/and name. If only name is supplied, there must be only one or an exception is raised
            descriptor: with format {'datacenter':{params to change info}}
                must be a dictionary or a json/yaml text.
            parameters to change can be supplyied by the descriptor or as parameters:
                new_name: the datacenter name
                vim_url: the datacenter URL
                vim_url_admin: the datacenter URL for administrative issues
                vim_type: the datacenter type, can be openstack or openvim.
                public: boolean, available to other tenants
                description: datacenter description
        Return: Raises an exception on error, not found or found several
                Obtain a dictionary with format {'datacenter':{new_datacenter_info}}
        '''

        if isinstance(descriptor, str):
            descriptor = self.parse(descriptor, descriptor_format)
        elif descriptor:
            pass
        elif kwargs:
            descriptor={"datacenter": {}}
        else:
            raise OpenmanoBadParamsException("Missing descriptor")

        if 'datacenter' not in descriptor or len(descriptor)!=1:
            raise OpenmanoBadParamsException("Descriptor must contain only one 'datacenter' field")
        for param in kwargs:
            if param=='new_name':
                descriptor['datacenter']['name'] = kwargs[param]
            else:
                descriptor['datacenter'][param] = kwargs[param]
        return self._edit_item("datacenters", descriptor, uuid, name, all_tenants=None)
    
    def attach_datacenter(self, uuid=None, name=None, descriptor=None, descriptor_format=None,  vim_user=None, vim_password=None, vim_tenant_name=None, vim_tenant_id=None):
        #check that exist
        uuid = self._get_item_uuid("datacenters", uuid, name, all_tenants=True)
        tenant_text = "/"+self._get_tenant()

        if isinstance(descriptor, str):
            descriptor = self.parse(descriptor, descriptor_format)
        elif descriptor:
            pass
        elif vim_user or vim_password or vim_tenant_name or vim_tenant_id:
            descriptor={"datacenter": {}}
        else:
            raise OpenmanoBadParamsException("Missing descriptor or params")
        
        if vim_user or vim_password or vim_tenant_name or vim_tenant_id:
            #print args.name
            try:
                if vim_user:
                    descriptor['datacenter']['vim_user'] = vim_user
                if vim_password:
                    descriptor['datacenter']['vim_password'] = vim_password
                if vim_tenant_name:
                    descriptor['datacenter']['vim_tenant_name'] = vim_tenant_name
                if vim_tenant_id:
                    descriptor['datacenter']['vim_tenant'] = vim_tenant_id
            except (KeyError, TypeError) as e:
                if str(e)=='datacenter':           error_pos= "missing field 'datacenter'"
                else:                       error_pos="wrong format"
                raise OpenmanoBadParamsException("Wrong datacenter descriptor: " + error_pos)

        payload_req = yaml.safe_dump(descriptor)
        #print payload_req
        URLrequest = "{}{}/datacenters/{}".format(self.endpoint_url, tenant_text, uuid)
        self.logger.debug("openmano POST %s %s", URLrequest, payload_req)
        mano_response = requests.post(URLrequest, headers = self.headers_req, data=payload_req)
        self.logger.debug("openmano response: %s", mano_response.text )
    
        content = self._parse_yaml(mano_response.text, response=True)
        if mano_response.status_code==200:
            return content
        else:
            raise OpenmanoResponseException(str(content))        

    def detach_datacenter(self, uuid=None, name=None):
        if not uuid:
            #check that exist
            uuid = self._get_item_uuid("datacenters", uuid, name, all_tenants=False)
        tenant_text = "/"+self._get_tenant()
        URLrequest = "{}{}/datacenters/{}".format(self.endpoint_url, tenant_text, uuid)
        self.logger.debug("openmano DELETE %s", URLrequest)
        mano_response = requests.delete(URLrequest, headers = self.headers_req)
        self.logger.debug("openmano response: %s", mano_response.text )
    
        content = self._parse_yaml(mano_response.text, response=True)
        if mano_response.status_code==200:
            return content
        else:
            raise OpenmanoResponseException(str(content))        

    #VNFS
    def list_vnfs(self, all_tenants=False, **kwargs):
        '''Obtain a list of vnfs
        Params: can be filtered by 'uuid','name','description','public', "tenant_id"
        Return: Raises an exception on error
                Obtain a dictionary with format {'vnfs':[{vnf1_info},{vnf2_info},...]}}
        '''
        return self._list_item("vnfs", all_tenants, kwargs)

    def get_vnf(self, uuid=None, name=None, all_tenants=False):
        '''Obtain the information of a vnf
        Params: uuid or/and name. If only name is supplied, there must be only one or an exception is raised
        Return: Raises an exception on error, not found, found several
                Obtain a dictionary with format {'vnf':{vnf_info}}
        '''
        return self._get_item("vnfs", uuid, name, all_tenants)

    def delete_vnf(self, uuid=None, name=None, all_tenants=False):
        '''Delete a vnf
        Params: uuid or/and name. If only name is supplied, there must be only one or an exception is raised
        Return: Raises an exception on error, not found, found several, not free
                Obtain a dictionary with format {'result': text indicating deleted}
        '''
        return self._del_item("vnfs", uuid, name, all_tenants)

    def create_vnf(self, descriptor=None, descriptor_format=None, **kwargs):
        '''Creates a vnf
        Params: must supply a descriptor
            descriptor: with format {'vnf':{new_vnf_info}}
                must be a dictionary or a json/yaml text.
                must be a dictionary or a json/yaml text.
            Other parameters can be:
                name: the vnf name. Overwrite descriptor name if any
                image_path: Can be a string or a string list. Overwrite the image_path at descriptor
                description: vnf descriptor.. Overwrite descriptor description if any
                public: boolean, available to other tenants
                class: user text for vnf classification
                tenant_id: Propietary tenant
                ...
        Return: Raises an exception on error
                Obtain a dictionary with format {'vnf':{new_vnf_info}}
        '''
        if isinstance(descriptor, str):
            descriptor = self.parse(descriptor, descriptor_format)
        elif descriptor:
            pass
        else:
            raise OpenmanoBadParamsException("Missing descriptor")
        
        if 'vnf' not in descriptor or len(descriptor)>2:
            raise OpenmanoBadParamsException("Descriptor must contain only one 'vnf' field, and an optional version")
        for param in kwargs:
            if param == 'image_path':
                #print args.name
                try:
                    if isinstance(kwargs[param], str):
                        descriptor['vnf']['VNFC'][0]['VNFC image']=kwargs[param]
                    elif isinstance(kwargs[param], tuple) or isinstance(kwargs[param], list):
                        index=0
                        for image_path_ in kwargs[param]:
                            #print "image-path", image_path_
                            descriptor['vnf']['VNFC'][index]['VNFC image']=image_path_
                            index=index+1
                    else:
                        raise OpenmanoBadParamsException("Wrong image_path type. Expected text or a text list")
                except (KeyError, TypeError) as e:
                    if str(e)=='vnf':           error_pos= "missing field 'vnf'"
                    elif str(e)=='VNFC':        error_pos= "missing field  'vnf':'VNFC'"
                    elif str(e)==str(index):    error_pos= "field  'vnf':'VNFC' must be an array"
                    elif str(e)=='VNFC image':  error_pos= "missing field 'vnf':'VNFC'['VNFC image']"
                    else:                       error_pos="wrong format"
                    raise OpenmanoBadParamsException("Wrong VNF descriptor: " + error_pos)
            else:
                descriptor['vnf'][param] = kwargs[param]
        return self._create_item("vnfs", descriptor)

#     def edit_vnf(self, uuid=None, name=None, descriptor=None, descriptor_format=None, all_tenants=False, **kwargs):
#         '''Edit the parameters of a vnf
#         Params: must supply a descriptor or/and a parameters to change
#             uuid or/and name. If only name is supplied, there must be only one or an exception is raised
#             descriptor: with format {'vnf':{params to change info}}
#             parameters to change can be supplyied by the descriptor or as parameters:
#                 new_name: the vnf name
#                 vim_url: the vnf URL
#                 vim_url_admin: the vnf URL for administrative issues
#                 vim_type: the vnf type, can be openstack or openvim.
#                 public: boolean, available to other tenants
#                 description: vnf description
#         Return: Raises an exception on error, not found or found several
#                 Obtain a dictionary with format {'vnf':{new_vnf_info}}
#         '''
# 
#        if isinstance(descriptor, str):
#            descriptor = self.parse(descriptor, descriptor_format)
#        elif descriptor:
#            pass
#         elif kwargs:
#             descriptor={"vnf": {}}
#         else:
#             raise OpenmanoBadParamsException("Missing descriptor")
# 
#         if 'vnf' not in descriptor or len(descriptor)>2:
#             raise OpenmanoBadParamsException("Descriptor must contain only one 'vnf' field")
#         for param in kwargs:
#             if param=='new_name':
#                 descriptor['vnf']['name'] = kwargs[param]
#             else:
#                 descriptor['vnf'][param] = kwargs[param]
#         return self._edit_item("vnfs", descriptor, uuid, name, all_tenants=None)

    #SCENARIOS
    def list_scenarios(self, all_tenants=False, **kwargs):
        '''Obtain a list of scenarios
        Params: can be filtered by 'uuid','name','description','public', "tenant_id"
        Return: Raises an exception on error
                Obtain a dictionary with format {'scenarios':[{scenario1_info},{scenario2_info},...]}}
        '''
        return self._list_item("scenarios", all_tenants, kwargs)

    def get_scenario(self, uuid=None, name=None, all_tenants=False):
        '''Obtain the information of a scenario
        Params: uuid or/and name. If only name is supplied, there must be only one or an exception is raised
        Return: Raises an exception on error, not found, found several
                Obtain a dictionary with format {'scenario':{scenario_info}}
        '''
        return self._get_item("scenarios", uuid, name, all_tenants)

    def delete_scenario(self, uuid=None, name=None, all_tenants=False):
        '''Delete a scenario
        Params: uuid or/and name. If only name is supplied, there must be only one or an exception is raised
        Return: Raises an exception on error, not found, found several, not free
                Obtain a dictionary with format {'result': text indicating deleted}
        '''
        return self._del_item("scenarios", uuid, name, all_tenants)

    def create_scenario(self, descriptor=None, descriptor_format=None, **kwargs):
        '''Creates a scenario
        Params: must supply a descriptor
            descriptor: with format {'scenario':{new_scenario_info}}
                must be a dictionary or a json/yaml text.
            Other parameters can be:
                name: the scenario name. Overwrite descriptor name if any
                description: scenario descriptor.. Overwrite descriptor description if any
                public: boolean, available to other tenants
                tenant_id. Propietary tenant
        Return: Raises an exception on error
                Obtain a dictionary with format {'scenario':{new_scenario_info}}
        '''
        if isinstance(descriptor, str):
            descriptor = self.parse(descriptor, descriptor_format)
        elif descriptor:
            pass
        else:
            raise OpenmanoBadParamsException("Missing descriptor")
        
        if 'scenario' not in descriptor or len(descriptor)>2:
            raise OpenmanoBadParamsException("Descriptor must contain only one 'scenario' field, and an optional version")
        for param in kwargs:
            descriptor['scenario'][param] = kwargs[param]
        return self._create_item("scenarios", descriptor)

    def edit_scenario(self, uuid=None, name=None, descriptor=None, descriptor_format=None, all_tenants=False, **kwargs):
        '''Edit the parameters of a scenario
        Params: must supply a descriptor or/and a parameters to change
            uuid or/and name. If only name is supplied, there must be only one or an exception is raised
            descriptor: with format {'scenario':{params to change info}}
                must be a dictionary or a json/yaml text.
            parameters to change can be supplyied by the descriptor or as parameters:
                new_name: the scenario name
                public: boolean, available to other tenants
                description: scenario description
                tenant_id. Propietary tenant
        Return: Raises an exception on error, not found or found several
                Obtain a dictionary with format {'scenario':{new_scenario_info}}
        '''
 
        if isinstance(descriptor, str):
            descriptor = self.parse(descriptor, descriptor_format)
        elif descriptor:
            pass
        elif kwargs:
            descriptor={"scenario": {}}
        else:
            raise OpenmanoBadParamsException("Missing descriptor")
 
        if 'scenario' not in descriptor or len(descriptor)>2:
            raise OpenmanoBadParamsException("Descriptor must contain only one 'scenario' field")
        for param in kwargs:
            if param=='new_name':
                descriptor['scenario']['name'] = kwargs[param]
            else:
                descriptor['scenario'][param] = kwargs[param]
        return self._edit_item("scenarios", descriptor, uuid, name, all_tenants=None)


    #INSTANCE-SCENARIOS
    def list_instances(self, all_tenants=False, **kwargs):
        '''Obtain a list of instances
        Params: can be filtered by 'uuid','name','description','scenario_id', "tenant_id"
        Return: Raises an exception on error
                Obtain a dictionary with format {'instances':[{instance1_info},{instance2_info},...]}}
        '''
        return self._list_item("instances", all_tenants, kwargs)

    def get_instance(self, uuid=None, name=None, all_tenants=False):
        '''Obtain the information of a instance
        Params: uuid or/and name. If only name is supplied, there must be only one or an exception is raised
        Return: Raises an exception on error, not found, found several
                Obtain a dictionary with format {'instance':{instance_info}}
        '''
        return self._get_item("instances", uuid, name, all_tenants)

    def delete_instance(self, uuid=None, name=None, all_tenants=False):
        '''Delete a instance
        Params: uuid or/and name. If only name is supplied, there must be only one or an exception is raised
        Return: Raises an exception on error, not found, found several, not free
                Obtain a dictionary with format {'result': text indicating deleted}
        '''
        return self._del_item("instances", uuid, name, all_tenants)

    def create_instance(self, descriptor=None, descriptor_format=None, name=None, **kwargs):
        '''Creates a instance
        Params: must supply a descriptor or/and a name and scenario
            descriptor: with format {'instance':{new_instance_info}}
                must be a dictionary or a json/yaml text.
            name: the instance name. Overwrite descriptor name if any
            Other parameters can be:
                description: instance descriptor.. Overwrite descriptor description if any
                datacenter_name, datacenter_id: datacenter  where to be deployed
                scenario_name, scenario_id: Scenario this instance is based on
        Return: Raises an exception on error
                Obtain a dictionary with format {'instance':{new_instance_info}}
        '''
        if isinstance(descriptor, str):
            descriptor = self.parse(descriptor, descriptor_format)
        elif descriptor:
            pass
        elif name and ("scenario_name" in kwargs or "scenario_id" in kwargs):
            descriptor = {"instance":{"name": name}}
        else:
            raise OpenmanoBadParamsException("Missing descriptor")
        
        if 'instance' not in descriptor or len(descriptor)>2:
            raise OpenmanoBadParamsException("Descriptor must contain only one 'instance' field, and an optional version")
        if name:
            descriptor['instance']["name"] = name
        if "scenario_name" in kwargs or "scenario_id" in kwargs:
            descriptor['instance']["scenario"] = self._get_item_uuid("scenarios", kwargs.get("scenario_id"), kwargs.get("scenario_name"))
        if "datacenter_name" in kwargs or "datacenter_id" in kwargs:
            descriptor['instance']["datacenter"] = self._get_item_uuid("datacenters", kwargs.get("datacenter_id"), kwargs.get("datacenter_name"))
        if "description" in kwargs:
            descriptor['instance']["description"] = kwargs.get("description")
        #for param in kwargs:
        #    descriptor['instance'][param] = kwargs[param]
        if "datacenter" not in descriptor['instance']:
            descriptor['instance']["datacenter"] = self._get_datacenter()
        return self._create_item("instances", descriptor)

    #VIM ACTIONS
    def vim_action(self, action, item, uuid=None, all_tenants=False, **kwargs):
        '''Perform an action over a vim
        Params: 
            action: can be 'list', 'get'/'show', 'delete' or 'create'
            item: can be 'tenants' or 'networks'
            uuid: uuid of the tenant/net to show or to delete. Ignore otherwise
            other parameters:
                datacenter_name, datacenter_id: datacenters to act on, if missing uses classes store datacenter 
                descriptor, descriptor_format: descriptor needed on creation, can be a dict or a yaml/json str 
                    must be a dictionary or a json/yaml text.
                name: for created tenant/net Overwrite descriptor name if any
                description: tenant descriptor. Overwrite descriptor description if any
                
        Return: Raises an exception on error
                Obtain a dictionary with format {'tenant':{new_tenant_info}}
        '''
        if item not in ("tenants", "networks"):
            raise OpenmanoBadParamsException("Unknown value for item '{}', must be 'tenants' or 'nets'".format(str(item))) 

        if all_tenants:
            tenant_text = "/any"
        else:
            tenant_text = "/"+self._get_tenant()
        
        if "datacenter_id" in kwargs or "datacenter_name" in kwargs:
            datacenter = self._get_item_uuid("datacenters", kwargs.get("datacenter_id"), kwargs.get("datacenter_name"), all_tenants=all_tenants)
        else:
            datacenter = self._get_datacenter()

        if action=="list":
            URLrequest = "{}{}/vim/{}/{}".format(self.endpoint_url, tenant_text, datacenter, item)
            self.logger.debug("GET %s", URLrequest )
            mano_response = requests.get(URLrequest, headers=self.headers_req)
            self.logger.debug("openmano response: %s", mano_response.text )
            content = self._parse_yaml(mano_response.text, response=True)            
            if mano_response.status_code==200:
                return content
            else:
                raise OpenmanoResponseException(str(content))        
        elif action=="get" or action=="show":
            URLrequest = "{}{}/vim/{}/{}/{}".format(self.endpoint_url, tenant_text, datacenter, item, uuid)
            self.logger.debug("GET %s", URLrequest )
            mano_response = requests.get(URLrequest, headers=self.headers_req)
            self.logger.debug("openmano response: %s", mano_response.text )
            content = self._parse_yaml(mano_response.text, response=True)            
            if mano_response.status_code==200:
                return content
            else:
                raise OpenmanoResponseException(str(content))        
        elif action=="delete":
            URLrequest = "{}{}/vim/{}/{}/{}".format(self.endpoint_url, tenant_text, datacenter, item, uuid)
            self.logger.debug("DELETE %s", URLrequest )
            mano_response = requests.delete(URLrequest, headers=self.headers_req)
            self.logger.debug("openmano response: %s", mano_response.text )
            content = self._parse_yaml(mano_response.text, response=True)            
            if mano_response.status_code==200:
                return content
            else:
                raise OpenmanoResponseException(str(content))        
        elif action=="create":
            if "descriptor" in kwargs:
                if isinstance(kwargs["descriptor"], str):
                    descriptor = self._parse(kwargs["descriptor"], kwargs.get("descriptor_format") )
                else:
                    descriptor = kwargs["descriptor"]
            elif "name" in kwargs:
                descriptor={item[:-1]: {"name": kwargs["name"]}}
            else:
                raise OpenmanoResponseException("Missing descriptor")
        
            if item[:-1] not in descriptor or len(descriptor)!=1:
                raise OpenmanoBadParamsException("Descriptor must contain only one 'tenant' field")
            if "name" in kwargs:
                descriptor[ item[:-1] ]['name'] = kwargs["name"]
            if "description" in kwargs:
                descriptor[ item[:-1] ]['description'] = kwargs["description"]
            payload_req = yaml.safe_dump(descriptor)
            #print payload_req
            URLrequest = "{}{}/vim/{}/{}".format(self.endpoint_url, tenant_text, datacenter, item)
            self.logger.debug("openmano POST %s %s", URLrequest, payload_req)
            mano_response = requests.post(URLrequest, headers = self.headers_req, data=payload_req)
            self.logger.debug("openmano response: %s", mano_response.text )
            content = self._parse_yaml(mano_response.text, response=True)
            if mano_response.status_code==200:
                return content
            else:
                raise OpenmanoResponseException(str(content))
        else:
            raise OpenmanoBadParamsException("Unknown value for action '{}".format(str(action))) 


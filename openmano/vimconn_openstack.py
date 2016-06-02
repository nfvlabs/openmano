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
osconnector implements all the methods to interact with openstack using the python-client.
'''
__author__="Alfonso Tierno, Gerardo Garcia"
__date__ ="$22-jun-2014 11:19:29$"

import vimconn
import json
import yaml
import logging

from novaclient import client as nClient, exceptions as nvExceptions
import keystoneclient.v2_0.client as ksClient
import keystoneclient.exceptions as ksExceptions
import glanceclient.v2.client as glClient
import glanceclient.client as gl1Client
import glanceclient.exc as gl1Exceptions
from httplib import HTTPException
from neutronclient.neutron import client as neClient
from neutronclient.common import exceptions as neExceptions
from requests.exceptions import ConnectionError

'''contain the openstack virtual machine status to openmano status'''
vmStatus2manoFormat={'ACTIVE':'ACTIVE',
                     'PAUSED':'PAUSED',
                     'SUSPENDED': 'SUSPENDED',
                     'SHUTOFF':'INACTIVE',
                     'BUILD':'BUILD',
                     'ERROR':'ERROR','DELETED':'DELETED'
                     }
netStatus2manoFormat={'ACTIVE':'ACTIVE','PAUSED':'PAUSED','INACTIVE':'INACTIVE','BUILD':'BUILD','ERROR':'ERROR','DELETED':'DELETED'
                     }

class vimconnector(vimconn.vimconnector):
    def __init__(self, uuid, name, tenant_id, tenant_name, url, url_admin=None, user=None, passwd=None, log_level="DEBUG", config={}):
        '''using common constructor parameters. In this case 
        'url' is the keystone authorization url,
        'url_admin' is not use
        '''
        vimconn.vimconnector.__init__(self, uuid, name, tenant_id, tenant_name, url, url_admin, user, passwd, log_level, config)
        
        self.k_creds={}
        self.n_creds={}
        if not url:
            raise TypeError, 'url param can not be NoneType'
        self.k_creds['auth_url'] = url
        self.n_creds['auth_url'] = url
        if tenant_name:
            self.k_creds['tenant_name'] = tenant_name
            self.n_creds['project_id']  = tenant_name
        if tenant_id:
            self.k_creds['tenant_id'] = tenant_id
            self.n_creds['tenant_id']  = tenant_id
        if user:
            self.k_creds['username'] = user
            self.n_creds['username'] = user
        if passwd:
            self.k_creds['password'] = passwd
            self.n_creds['api_key']  = passwd
        self.reload_client       = True
        self.logger = logging.getLogger('mano.vim.openstack')
    
    def __setitem__(self,index, value):
        '''Set individuals parameters 
        Throw TypeError, KeyError
        '''
        if index=='tenant_id':
            self.reload_client=True
            self.tenant_id = value
            if value:
                self.k_creds['tenant_id'] = value
                self.n_creds['tenant_id']  = value
            else:
                del self.k_creds['tenant_name']
                del self.n_creds['project_id']
        elif index=='tenant_name':
            self.reload_client=True
            self.tenant_name = value
            if value:
                self.k_creds['tenant_name'] = value
                self.n_creds['project_id']  = value
            else:
                del self.k_creds['tenant_name']
                del self.n_creds['project_id']
        elif index=='user':
            self.reload_client=True
            self.user = value
            if value:
                self.k_creds['username'] = value
                self.n_creds['username'] = value
            else:
                del self.k_creds['username']
                del self.n_creds['username']
        elif index=='passwd':
            self.reload_client=True
            self.passwd = value
            if value:
                self.k_creds['password'] = value
                self.n_creds['api_key']  = value
            else:
                del self.k_creds['password']
                del self.n_creds['api_key']
        elif index=='url':
            self.reload_client=True
            self.url = value
            if value:
                self.k_creds['auth_url'] = value
                self.n_creds['auth_url'] = value
            else:
                raise TypeError, 'url param can not be NoneType'
        else:
            vimconn.vimconnector.__setitem__(self,index, value)
     
    def _reload_connection(self):
        '''Called before any operation, it check if credentials has changed
        Throw keystoneclient.apiclient.exceptions.AuthorizationFailure
        '''
        #TODO control the timing and possible token timeout, but it seams that python client does this task for us :-) 
        if self.reload_client:
            #test valid params
            if len(self.n_creds) <4:
                raise ksExceptions.ClientException("Not enough parameters to connect to openstack")
            self.nova = nClient.Client(2, **self.n_creds)
            self.keystone = ksClient.Client(**self.k_creds)
            self.glance_endpoint = self.keystone.service_catalog.url_for(service_type='image', endpoint_type='publicURL')
            self.glance = glClient.Client(self.glance_endpoint, token=self.keystone.auth_token, **self.k_creds)  #TODO check k_creds vs n_creds
            self.ne_endpoint=self.keystone.service_catalog.url_for(service_type='network', endpoint_type='publicURL')
            self.neutron = neClient.Client('2.0', endpoint_url=self.ne_endpoint, token=self.keystone.auth_token, **self.k_creds)
            self.reload_client = False
        
    def __net_os2mano(self, net_list_dict):
        '''Transform the net openstack format to mano format
        net_list_dict can be a list of dict or a single dict'''
        if type(net_list_dict) is dict:
            net_list_=(net_list_dict,)
        elif type(net_list_dict) is list:
            net_list_=net_list_dict
        else:
            raise TypeError("param net_list_dict must be a list or a dictionary")
        for net in net_list_:
            if net.get('provider:network_type') == "vlan":
                net['type']='data'
            else:
                net['type']='bridge'
                
                
            
    def _format_exception(self, exception):
        '''Transform a keystone, nova, neutron  exception into a vimconn exception'''
        if isinstance(exception, (HTTPException, gl1Exceptions.HTTPException, gl1Exceptions.CommunicationError,
                                  ConnectionError, ksExceptions.ConnectionError, neExceptions.ConnectionFailed,
                                  neClient.exceptions.ConnectionFailed)):
            raise vimconn.vimconnConnectionException(type(exception).__name__ + ": " + str(exception))            
        elif isinstance(exception, (nvExceptions.ClientException, ksExceptions.ClientException, 
                                    neExceptions.NeutronException, nvExceptions.BadRequest)):
            raise vimconn.vimconnUnexpectedResponse(type(exception).__name__ + ": " + str(exception))
        elif isinstance(exception, (neExceptions.NetworkNotFoundClient, nvExceptions.NotFound)):
            raise vimconn.vimconnNotFoundException(type(exception).__name__ + ": " + str(exception))
        elif isinstance(exception, nvExceptions.Conflict):
            raise vimconn.vimconnConflictException(type(exception).__name__ + ": " + str(exception))
        else: # ()
            raise vimconn.vimconnConnectionException(type(exception).__name__ + ": " + str(exception))

    def get_tenant_list(self, filter_dict={}):
        '''Obtain tenants of VIM
        filter_dict can contain the following keys:
            name: filter by tenant name
            id: filter by tenant uuid/id
            <other VIM specific>
        Returns the tenant list of dictionaries: [{'name':'<name>, 'id':'<id>, ...}, ...]
        '''
        self.logger.debug("Getting tenant from VIM filter: '%s'", str(filter_dict))
        try:
            self._reload_connection()
            tenant_class_list=self.keystone.tenants.findall(**filter_dict)
            tenant_list=[]
            for tenant in tenant_class_list:
                tenant_list.append(tenant.to_dict())
            return tenant_list
        except (ksExceptions.ConnectionError, ksExceptions.ClientException)  as e:
            self._format_exception(e)

    def new_tenant(self, tenant_name, tenant_description):
        '''Adds a new tenant to openstack VIM. Returns the tenant identifier'''
        self.logger.debug("Adding a new tenant name: %s", tenant_name)
        try:
            self._reload_connection()
            tenant=self.keystone.tenants.create(tenant_name, tenant_description)
            return tenant.id
        except (ksExceptions.ConnectionError, ksExceptions.ClientException)  as e:
            self._format_exception(e)

    def delete_tenant(self, tenant_id):
        '''Delete a tenant from openstack VIM. Returns the old tenant identifier'''
        self.logger.debug("Deleting tenant %s from VIM", tenant_id)
        try:
            self._reload_connection()
            self.keystone.tenants.delete(tenant_id)
            return tenant_id
        except (ksExceptions.ConnectionError, ksExceptions.ClientException)  as e:
            self._format_exception(e)
        
    def new_network(self,net_name,net_type, shared=False, cidr=None, vlan=None):
        '''Adds a tenant network to VIM. Returns the network identifier'''
        self.logger.debug("Adding a new network to VIM name '%s', type '%s'", net_name, net_type)
        try:
            self._reload_connection()
            network_dict = {'name': net_name, 'admin_state_up': True}
            if net_type=="data" or net_type=="ptp":
                if self.config.get('dataplane_physical_net') == None:
                    raise vimconn.vimconnConflictException("You must provide a 'dataplane_physical_net' at config value before creating sriov network")
                network_dict["provider:physical_network"] = self.config['dataplane_physical_net'] #"physnet_sriov" #TODO physical
                network_dict["provider:network_type"]     = "vlan"
                if vlan!=None:
                    network_dict["provider:network_type"] = vlan
            network_dict["shared"]=shared
            new_net=self.neutron.create_network({'network':network_dict})
            #print new_net
            #create fake subnetwork
            if not cidr:
                cidr="192.168.111.0/24"
            subnet={"name":net_name+"-subnet",
                    "network_id": new_net["network"]["id"],
                    "ip_version": 4,
                    "cidr": cidr
                    }
            self.neutron.create_subnet({"subnet": subnet} )
            return new_net["network"]["id"]
        except (neExceptions.ConnectionFailed, ksExceptions.ClientException, neExceptions.NeutronException) as e:
            self._format_exception(e)

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
        self.logger.debug("Getting network from VIM filter: '%s'", str(filter_dict))
        try:
            self._reload_connection()
            net_dict=self.neutron.list_networks(**filter_dict)
            net_list=net_dict["networks"]
            self.__net_os2mano(net_list)
            return net_list
        except (neExceptions.ConnectionFailed, neClient.exceptions.ConnectionFailed, ksExceptions.ClientException, neExceptions.NeutronException) as e:
            self._format_exception(e)

    def get_network(self, net_id):
        '''Obtain details of network from VIM
        Returns the network information from a network id'''
        self.logger.debug(" Getting tenant network %s from VIM", net_id)
        filter_dict={"id": net_id}
        net_list = self.get_network_list(filter_dict)
        if len(net_list)==0:
            raise vimconn.vimconnNotFoundException("Network '{}' not found".format(net_id))
        elif len(net_list)>1:
            raise vimconn.vimconnConflictException("Found more than one network with this criteria")
        net = net_list[0]
        subnets=[]
        for subnet_id in net.get("subnets", () ):
            try:
                subnet = self.neutron.show_subnet(subnet_id)
            except Exception as e:
                self.logger.error("osconnector.get_network(): Error getting subnet %s %s" % (net_id, str(e)))
                subnet = {"id": subnet_id, "fault": str(e)}
            subnets.append(subnet)
        net["subnets"] = subnets
        return net

    def delete_network(self, net_id):
        '''Deletes a tenant network from VIM. Returns the old network identifier'''
        self.logger.debug("Deleting network '%s' from VIM", net_id)
        try:
            self._reload_connection()
            #delete VM ports attached to this networks before the network
            ports = self.neutron.list_ports(network_id=net_id)
            for p in ports['ports']:
                try:
                    self.neutron.delete_port(p["id"])
                except Exception as e:
                    self.logger.error("Error deleting port %s: %s", p["id"], str(e))
            self.neutron.delete_network(net_id)
            return net_id
        except (neExceptions.ConnectionFailed, neExceptions.NetworkNotFoundClient, neExceptions.NeutronException,
                neClient.exceptions.ConnectionFailed, ksExceptions.ClientException, neExceptions.NeutronException) as e:
            self._format_exception(e)

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
        net_dict={}
        for net_id in net_list:
            net = {}
            try:
                net_vim = self.get_network(net_id)
                if net_vim['status'] in netStatus2manoFormat:
                    net["status"] = netStatus2manoFormat[ net_vim['status'] ]
                else:
                    net["status"] = "OTHER"
                    net["error_msg"] = "VIM status reported " + net_vim['status']
                    
                if net['status'] == "ACIVE" and not net_vim['admin_state_up']:
                    net['status'] = 'DOWN'
                net['vim_info']  = yaml.safe_dump(net_vim)
                if net_vim.get('fault'):  #TODO
                    net['error_msg'] = str(net_vim['fault'])
            except vimconn.vimconnNotFoundException as e:
                self.logger.error("Exception getting net status: %s", str(e))
                net['status'] = "DELETED"
                net['error_msg'] = str(e)
            except vimconn.vimconnException as e:
                self.logger.error("Exception getting net status: %s", str(e))
                net['status'] = "VIM_ERROR"
                net['error_msg'] = str(e)
            net_dict[net_id] = net
        return net_dict

    def get_flavor(self, flavor_id):
        '''Obtain flavor details from the  VIM. Returns the flavor dict details'''
        self.logger.debug("Getting flavor '%s'", flavor_id)
        try:
            self._reload_connection()
            flavor = self.nova.flavors.find(id=flavor_id)
            #TODO parse input and translate to VIM format (openmano_schemas.new_vminstance_response_schema)
            return flavor.to_dict()
        except (nvExceptions.NotFound, nvExceptions.ClientException, ksExceptions.ClientException) as e:
            self._format_exception(e)

    def new_flavor(self, flavor_data, change_name_if_used=True):
        '''Adds a tenant flavor to openstack VIM
        if change_name_if_used is True, it will change name in case of conflict, because it is not supported name repetition
        Returns the flavor identifier
        '''
        self.logger.debug("Adding flavor '%s'", str(flavor_data))
        retry=0
        max_retries=3
        name_suffix = 0
        name=flavor_data['name']
        while retry<max_retries:
            retry+=1
            try:
                self._reload_connection()
                if change_name_if_used:
                    #get used names
                    fl_names=[]
                    fl=self.nova.flavors.list()
                    for f in fl:
                        fl_names.append(f.name)
                    while name in fl_names:
                        name_suffix += 1
                        name = flavor_data['name']+"-" + str(name_suffix)
                        
                ram = flavor_data.get('ram',64)
                vcpus = flavor_data.get('vcpus',1)
                numa_properties=None

                extended = flavor_data.get("extended")
                if extended:
                    numas=extended.get("numas")
                    if numas:
                        numa_nodes = len(numas)
                        if numa_nodes > 1:
                            return -1, "Can not add flavor with more than one numa"
                        numa_properties = {"hw:numa_nodes":str(numa_nodes)}
                        numa_properties["hw:mem_page_size"] = "large"
                        numa_properties["hw:cpu_policy"] = "dedicated"
                        numa_properties["hw:numa_mempolicy"] = "strict"
                        for numa in numas:
                            #overwrite ram and vcpus
                            ram = numa['memory']*1024
                            if 'paired-threads' in numa:
                                vcpus = numa['paired-threads']*2
                                numa_properties["hw:cpu_threads_policy"] = "prefer"
                            elif 'cores' in numa:
                                vcpus = numa['cores']
                                #numa_properties["hw:cpu_threads_policy"] = "prefer"
                            elif 'threads' in numa:
                                vcpus = numa['threads']
                                numa_properties["hw:cpu_policy"] = "isolated"
                            for interface in numa.get("interfaces",() ):
                                if interface["dedicated"]=="yes":
                                    raise vimconn.HTTP_Service_Unavailable("Passthrough interfaces are not supported for the openstack connector")
                                #TODO, add the key 'pci_passthrough:alias"="<label at config>:<number ifaces>"' when a way to connect it is available
                                
                #create flavor                 
                new_flavor=self.nova.flavors.create(name, 
                                ram, 
                                vcpus, 
                                flavor_data.get('disk',1),
                                is_public=flavor_data.get('is_public', True)
                            ) 
                #add metadata
                if numa_properties:
                    new_flavor.set_keys(numa_properties)
                return new_flavor.id
            except nvExceptions.Conflict as e:
                if change_name_if_used and retry < max_retries:
                    continue
                self._format_exception(e)
            #except nvExceptions.BadRequest as e:
            except (ksExceptions.ClientException, nvExceptions.ClientException, ConnectionError) as e:
                self._format_exception(e)

    def delete_flavor(self,flavor_id):
        '''Deletes a tenant flavor from openstack VIM. Returns the old flavor_id
        '''
        try:
            self._reload_connection()
            self.nova.flavors.delete(flavor_id)
            return flavor_id
        #except nvExceptions.BadRequest as e:
        except (nvExceptions.NotFound, ksExceptions.ClientException, nvExceptions.ClientException) as e:
            self._format_exception(e)

    def new_image(self,image_dict):
        '''
        Adds a tenant image to VIM. imge_dict is a dictionary with:
            name: name
            disk_format: qcow2, vhd, vmdk, raw (by default), ...
            location: path or URI
            public: "yes" or "no"
            metadata: metadata of the image
        Returns the image_id
        '''
        #using version 1 of glance client
        glancev1 = gl1Client.Client('1',self.glance_endpoint, token=self.keystone.auth_token, **self.k_creds)  #TODO check k_creds vs n_creds
        retry=0
        max_retries=3
        while retry<max_retries:
            retry+=1
            try:
                self._reload_connection()
                #determine format  http://docs.openstack.org/developer/glance/formats.html
                if "disk_format" in image_dict:
                    disk_format=image_dict["disk_format"]
                else: #autodiscover base on extention
                    if image_dict['location'][-6:]==".qcow2":
                        disk_format="qcow2"
                    elif image_dict['location'][-4:]==".vhd":
                        disk_format="vhd"
                    elif image_dict['location'][-5:]==".vmdk":
                        disk_format="vmdk"
                    elif image_dict['location'][-4:]==".vdi":
                        disk_format="vdi"
                    elif image_dict['location'][-4:]==".iso":
                        disk_format="iso"
                    elif image_dict['location'][-4:]==".aki":
                        disk_format="aki"
                    elif image_dict['location'][-4:]==".ari":
                        disk_format="ari"
                    elif image_dict['location'][-4:]==".ami":
                        disk_format="ami"
                    else:
                        disk_format="raw"
                self.logger.debug("new_image: '%s' loading from '%s'", image_dict['name'], image_dict['location'])
                if image_dict['location'][0:4]=="http":
                    new_image = glancev1.images.create(name=image_dict['name'], is_public=image_dict.get('public',"yes")=="yes",
                            container_format="bare", location=image_dict['location'], disk_format=disk_format)
                else: #local path
                    with open(image_dict['location']) as fimage:
                        new_image = glancev1.images.create(name=image_dict['name'], is_public=image_dict.get('public',"yes")=="yes",
                            container_format="bare", data=fimage, disk_format=disk_format)
                #insert metadata. We cannot use 'new_image.properties.setdefault' 
                #because nova and glance are "INDEPENDENT" and we are using nova for reading metadata
                new_image_nova=self.nova.images.find(id=new_image.id)
                new_image_nova.metadata.setdefault('location',image_dict['location'])
                metadata_to_load = image_dict.get('metadata')
                if metadata_to_load:
                    for k,v in yaml.load(metadata_to_load).iteritems():
                        new_image_nova.metadata.setdefault(k,v)
                return new_image.id
            except (nvExceptions.Conflict, ksExceptions.ClientException, nvExceptions.ClientException) as e:
                self._format_exception(e)
            except (HTTPException, gl1Exceptions.HTTPException, gl1Exceptions.CommunicationError) as e:
                if retry==max_retries:
                    continue
                self._format_exception(e)
            except IOError as e:  #can not open the file
                raise vimconn.vimconnConnectionException(type(e).__name__ + ": " + str(e)+ " for " + image_dict['location'],
                                                         http_code=vimconn.HTTP_Bad_Request)
     
    def delete_image(self, image_id):
        '''Deletes a tenant image from openstack VIM. Returns the old id
        '''
        try:
            self._reload_connection()
            self.nova.images.delete(image_id)
            return image_id
        except (nvExceptions.NotFound, ksExceptions.ClientException, nvExceptions.ClientException, gl1Exceptions.CommunicationError) as e: #TODO remove
            self._format_exception(e)

    def get_image_id_from_path(self, path):
        '''Get the image id from image path in the VIM database. Returns the image_id 
        '''
        try:
            self._reload_connection()
            images = self.nova.images.list()
            for image in images:
                if image.metadata.get("location")==path:
                    return image.id
            raise vimconn.vimconnNotFoundException("image with location '{}' not found".format( path))
        except (ksExceptions.ClientException, nvExceptions.ClientException, gl1Exceptions.CommunicationError) as e: 
            self._format_exception(e)
        
    def new_vminstance(self,name,description,start,image_id,flavor_id,net_list):
        '''Adds a VM instance to VIM
        Params:
            start: indicates if VM must start or boot in pause mode. Ignored
            image_id,flavor_id: iamge and flavor uuid
            net_list: list of interfaces, each one is a dictionary with:
                name:
                net_id: network uuid to connect
                vpci: virtual vcpi to assign, ignored because openstack lack #TODO
                model: interface model, ignored #TODO
                mac_address: used for  SR-IOV ifaces #TODO for other types
                use: 'data', 'bridge',  'mgmt'
                type: 'virtual', 'PF', 'VF', 'VFnotShared'
                vim_id: filled/added by this function
                #TODO ip, security groups
        Returns the instance identifier
        '''
        self.logger.debug("Creating VM image '%s' flavor '%s' nics='%s'",image_id, flavor_id,str(net_list))
        try:
            metadata=[]
            net_list_vim=[]
            self._reload_connection()
            metadata_vpci={} #For a specific neutron plugin 
            for net in net_list:
                if not net.get("net_id"): #skip non connected iface
                    continue
                if net["type"]=="virtual":
                    net_list_vim.append({'net-id': net["net_id"]})
                    if "vpci" in net:
                        metadata_vpci[ net["net_id"] ] = [[ net["vpci"], "" ]]
                elif net["type"]=="PF":
                    self.logger.warn("new_vminstance: Warning, can not connect a passthrough interface ")
                    #TODO insert this when openstack consider passthrough ports as openstack neutron ports
                else: #VF
                    if "vpci" in net:
                        if "VF" not in metadata_vpci:
                            metadata_vpci["VF"]=[]
                        metadata_vpci["VF"].append([ net["vpci"], "" ])
                    port_dict={
                         "network_id": net["net_id"],
                         "name": net.get("name"),
                         "binding:vnic_type": "direct", 
                         "admin_state_up": True
                    }
                    if not port_dict["name"]:
                        port_dict["name"] = name
                    if net.get("mac_address"):
                        port_dict["mac_address"]=net["mac_address"]
                    #TODO: manage having SRIOV without vlan tag
                    #if net["type"] == "VFnotShared"
                    #    port_dict["vlan"]=0
                    new_port = self.neutron.create_port({"port": port_dict })
                    net["mac_adress"] = new_port["port"]["mac_address"]
                    net["vim_id"] = new_port["port"]["id"]
                    net["ip"] = new_port["port"].get("fixed_ips",[{}])[0].get("ip_address")
                    net_list_vim.append({"port-id": new_port["port"]["id"]})
            if metadata_vpci:
                metadata = {"pci_assignement": json.dumps(metadata_vpci)}
            
            self.logger.debug("name '%s' image_id '%s'flavor_id '%s' net_list_vim '%s' description '%s' metadata %s",
                              name, image_id, flavor_id, str(net_list_vim), description, str(metadata))
            
            security_groups   = self.config.get('security_groups')
            if type(security_groups) is str:
                security_groups = ( security_groups, )
            server = self.nova.servers.create(name, image_id, flavor_id, nics=net_list_vim, meta=metadata,
                                              security_groups   = security_groups,
                                              availability_zone = self.config.get('availability_zone'),
                                              key_name          = self.config.get('keypair'),
                                        ) #, description=description)
            
            
            #print "DONE :-)", server
            
#             #TODO   server.add_floating_ip("10.95.87.209")
#             #To look for a free floating_ip
#             free_floating_ip = None
#             for floating_ip in self.neutron.list_floatingips().get("floatingips", () ):
#                 if not floating_ip["port_id"]:
#                     free_floating_ip = floating_ip["floating_ip_address"]
#                     break
#             if free_floating_ip:
#                 server.add_floating_ip(free_floating_ip)
                
            
            return server.id
#        except nvExceptions.NotFound as e:
#            error_value=-vimconn.HTTP_Not_Found
#            error_text= "vm instance %s not found" % vm_id
        except (ksExceptions.ClientException, nvExceptions.ClientException, ConnectionError,
                neClient.exceptions.ConnectionFailed) as e:
            self._format_exception(e)
        except TypeError as e:
            raise vimconn.vimconnException(type(e).__name__ + ": "+  str(e), http_code=vimconn.HTTP_Bad_Request)

    def get_vminstance(self,vm_id):
        '''Returns the VM instance information from VIM'''
        #self.logger.debug("Getting VM from VIM")
        try:
            self._reload_connection()
            server = self.nova.servers.find(id=vm_id)
            #TODO parse input and translate to VIM format (openmano_schemas.new_vminstance_response_schema)
            return server.to_dict()
        except (ksExceptions.ClientException, nvExceptions.ClientException, nvExceptions.NotFound) as e:
            self._format_exception(e)

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
        self.logger.debug("Getting VM CONSOLE from VIM")
        try:
            self._reload_connection()
            server = self.nova.servers.find(id=vm_id)
            if console_type == None or console_type == "novnc":
                console_dict = server.get_vnc_console("novnc")
            elif console_type == "xvpvnc":
                console_dict = server.get_vnc_console(console_type)
            elif console_type == "rdp-html5":
                console_dict = server.get_rdp_console(console_type)
            elif console_type == "spice-html5":
                console_dict = server.get_spice_console(console_type)
            else:
                raise vimconn.vimconnException("console type '{}' not allowed".format(console_type), http_code=vimconn.HTTP_Bad_Request)
            
            console_dict1 = console_dict.get("console")
            if console_dict1:
                console_url = console_dict1.get("url")
                if console_url:
                    #parse console_url
                    protocol_index = console_url.find("//")
                    suffix_index = console_url[protocol_index+2:].find("/") + protocol_index+2
                    port_index = console_url[protocol_index+2:suffix_index].find(":") + protocol_index+2
                    if protocol_index < 0 or port_index<0 or suffix_index<0:
                        return -vimconn.HTTP_Internal_Server_Error, "Unexpected response from VIM"
                    console_dict={"protocol": console_url[0:protocol_index],
                                  "server":   console_url[protocol_index+2:port_index], 
                                  "port":     console_url[port_index:suffix_index], 
                                  "suffix":   console_url[suffix_index+1:] 
                                  }
                    protocol_index += 2
                    return console_dict
            raise vimconn.vimconnUnexpectedResponse("Unexpected response from VIM")
            
        except (nvExceptions.NotFound, ksExceptions.ClientException, nvExceptions.ClientException, nvExceptions.BadRequest) as e:
            self._format_exception(e)

    def delete_vminstance(self, vm_id):
        '''Removes a VM instance from VIM. Returns the old identifier
        '''
        #print "osconnector: Getting VM from VIM"
        try:
            self._reload_connection()
            #delete VM ports attached to this networks before the virtual machine
            ports = self.neutron.list_ports(device_id=vm_id)
            for p in ports['ports']:
                try:
                    self.neutron.delete_port(p["id"])
                except Exception as e:
                    self.logger.error("Error deleting port: " + type(e).__name__ + ": "+  str(e))
            self.nova.servers.delete(vm_id)
            return vm_id
        except (nvExceptions.NotFound, ksExceptions.ClientException, nvExceptions.ClientException) as e:
            self._format_exception(e)
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception

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
        vm_dict={}
        self.logger.debug("refresh_vms status: Getting tenant VM instance information from VIM")
        for vm_id in vm_list:
            vm={}
            try:
                vm_vim = self.get_vminstance(vm_id)
                if vm_vim['status'] in vmStatus2manoFormat:
                    vm['status']    =  vmStatus2manoFormat[ vm_vim['status'] ]
                else:
                    vm['status']    = "OTHER"
                    vm['error_msg'] = "VIM status reported " + vm_vim['status']
                vm['vim_info']  = yaml.safe_dump(vm_vim)
                vm["interfaces"] = []
                if vm_vim.get('fault'):
                    vm['error_msg'] = str(vm_vim['fault'])
                #get interfaces
                try:
                    self._reload_connection()
                    port_dict=self.neutron.list_ports(device_id=vm_id)
                    for port in port_dict["ports"]:
                        interface={}
                        interface['vim_info']  = yaml.safe_dump(port)
                        interface["mac_address"] = port.get("mac_address")
                        interface["vim_net_id"] = port["network_id"]
                        interface["vim_interface_id"] = port["id"]
                        ips=[]
                        #look for floating ip address
                        floating_ip_dict = self.neutron.list_floatingips(port_id=port["id"])
                        if floating_ip_dict.get("floatingips"):
                            ips.append(floating_ip_dict["floatingips"][0].get("floating_ip_address") )

                        for subnet in port["fixed_ips"]:
                            ips.append(subnet["ip_address"])
                        interface["ip_address"] = ";".join(ips)
                        vm["interfaces"].append(interface)
                except Exception as e:
                    self.logger.error("Error getting vm interface information " + type(e).__name__ + ": "+  str(e))
            except vimconn.vimconnNotFoundException as e:
                self.logger.error("Exception getting vm status: %s", str(e))
                vm['status'] = "DELETED"
                vm['error_msg'] = str(e)
            except vimconn.vimconnException as e:
                self.logger.error("Exception getting vm status: %s", str(e))
                vm['status'] = "VIM_ERROR"
                vm['error_msg'] = str(e)
            vm_dict[vm_id] = vm
        return vm_dict
    
    def action_vminstance(self, vm_id, action_dict):
        '''Send and action over a VM instance from VIM
        Returns the vm_id if the action was successfully sent to the VIM'''
        self.logger.debug("Action over VM '%s': %s", vm_id, str(action_dict))
        try:
            self._reload_connection()
            server = self.nova.servers.find(id=vm_id)
            if "start" in action_dict:
                if action_dict["start"]=="rebuild":  
                    server.rebuild()
                else:
                    if server.status=="PAUSED":
                        server.unpause()
                    elif server.status=="SUSPENDED":
                        server.resume()
                    elif server.status=="SHUTOFF":
                        server.start()
            elif "pause" in action_dict:
                server.pause()
            elif "resume" in action_dict:
                server.resume()
            elif "shutoff" in action_dict or "shutdown" in action_dict:
                server.stop()
            elif "forceOff" in action_dict:
                server.stop() #TODO
            elif "terminate" in action_dict:
                server.delete()
            elif "createImage" in action_dict:
                server.create_image()
                #"path":path_schema,
                #"description":description_schema,
                #"name":name_schema,
                #"metadata":metadata_schema,
                #"imageRef": id_schema,
                #"disk": {"oneOf":[{"type": "null"}, {"type":"string"}] },
            elif "rebuild" in action_dict:
                server.rebuild(server.image['id'])
            elif "reboot" in action_dict:
                server.reboot() #reboot_type='SOFT'
            elif "console" in action_dict:
                console_type = action_dict["console"]
                if console_type == None or console_type == "novnc":
                    console_dict = server.get_vnc_console("novnc")
                elif console_type == "xvpvnc":
                    console_dict = server.get_vnc_console(console_type)
                elif console_type == "rdp-html5":
                    console_dict = server.get_rdp_console(console_type)
                elif console_type == "spice-html5":
                    console_dict = server.get_spice_console(console_type)
                else:
                    raise vimconn.vimconnException("console type '{}' not allowed".format(console_type), 
                                                   http_code=vimconn.HTTP_Bad_Request)
                try:
                    console_url = console_dict["console"]["url"]
                    #parse console_url
                    protocol_index = console_url.find("//")
                    suffix_index = console_url[protocol_index+2:].find("/") + protocol_index+2
                    port_index = console_url[protocol_index+2:suffix_index].find(":") + protocol_index+2
                    if protocol_index < 0 or port_index<0 or suffix_index<0:
                        raise vimconn.vimconnException("Unexpected response from VIM " + str(console_dict))
                    console_dict2={"protocol": console_url[0:protocol_index],
                                  "server":   console_url[protocol_index+2 : port_index], 
                                  "port":     int(console_url[port_index+1 : suffix_index]), 
                                  "suffix":   console_url[suffix_index+1:] 
                                  }
                    return console_dict2               
                except Exception as e:
                    raise vimconn.vimconnException("Unexpected response from VIM " + str(console_dict))
            
            return vm_id
        except (ksExceptions.ClientException, nvExceptions.ClientException, nvExceptions.NotFound) as e:
            self._format_exception(e)
        #TODO insert exception vimconn.HTTP_Unauthorized

#NOT USED FUNCTIONS
    
    def new_external_port(self, port_data):
        #TODO openstack if needed
        '''Adds a external port to VIM'''
        '''Returns the port identifier'''
        return -vimconn.HTTP_Internal_Server_Error, "osconnector.new_external_port() not implemented" 
        
    def connect_port_network(self, port_id, network_id, admin=False):
        #TODO openstack if needed
        '''Connects a external port to a network'''
        '''Returns status code of the VIM response'''
        return -vimconn.HTTP_Internal_Server_Error, "osconnector.connect_port_network() not implemented" 
    
    def new_user(self, user_name, user_passwd, tenant_id=None):
        '''Adds a new user to openstack VIM'''
        '''Returns the user identifier'''
        self.logger.debug("osconnector: Adding a new user to VIM")
        try:
            self._reload_connection()
            user=self.keystone.users.create(user_name, user_passwd, tenant_id=tenant_id)
            #self.keystone.tenants.add_user(self.k_creds["username"], #role)
            return user.id
        except ksExceptions.ConnectionError as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except ksExceptions.ClientException as e: #TODO remove
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            self.logger.debug("new_user " + error_text)
        return error_value, error_text        

    def delete_user(self, user_id):
        '''Delete a user from openstack VIM'''
        '''Returns the user identifier'''
        if self.debug:
            print "osconnector: Deleting  a  user from VIM"
        try:
            self._reload_connection()
            self.keystone.users.delete(user_id)
            return 1, user_id
        except ksExceptions.ConnectionError as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except ksExceptions.NotFound as e:
            error_value=-vimconn.HTTP_Not_Found
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        except ksExceptions.ClientException as e: #TODO remove
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "delete_tenant " + error_text
        return error_value, error_text
 
    def get_hosts_info(self):
        '''Get the information of deployed hosts
        Returns the hosts content'''
        if self.debug:
            print "osconnector: Getting Host info from VIM"
        try:
            h_list=[]
            self._reload_connection()
            hypervisors = self.nova.hypervisors.list()
            for hype in hypervisors:
                h_list.append( hype.to_dict() )
            return 1, {"hosts":h_list}
        except nvExceptions.NotFound as e:
            error_value=-vimconn.HTTP_Not_Found
            error_text= (str(e) if len(e.args)==0 else str(e.args[0]))
        except (ksExceptions.ClientException, nvExceptions.ClientException) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "get_hosts_info " + error_text
        return error_value, error_text        

    def get_hosts(self, vim_tenant):
        '''Get the hosts and deployed instances
        Returns the hosts content'''
        r, hype_dict = self.get_hosts_info()
        if r<0:
            return r, hype_dict
        hypervisors = hype_dict["hosts"]
        try:
            servers = self.nova.servers.list()
            for hype in hypervisors:
                for server in servers:
                    if server.to_dict()['OS-EXT-SRV-ATTR:hypervisor_hostname']==hype['hypervisor_hostname']:
                        if 'vm' in hype:
                            hype['vm'].append(server.id)
                        else:
                            hype['vm'] = [server.id]
            return 1, hype_dict
        except nvExceptions.NotFound as e:
            error_value=-vimconn.HTTP_Not_Found
            error_text= (str(e) if len(e.args)==0 else str(e.args[0]))
        except (ksExceptions.ClientException, nvExceptions.ClientException) as e:
            error_value=-vimconn.HTTP_Bad_Request
            error_text= type(e).__name__ + ": "+  (str(e) if len(e.args)==0 else str(e.args[0]))
        #TODO insert exception vimconn.HTTP_Unauthorized
        #if reaching here is because an exception
        if self.debug:
            print "get_hosts " + error_text
        return error_value, error_text        
  


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
NFVO engine, implementing all the methods for the creation, deletion and management of vnfs, scenarios and instances
'''
__author__="Alfonso Tierno, Gerardo Garcia"
__date__ ="$16-sep-2014 22:05:01$"

import vimconnector
import osconnector
import json
import yaml
import os
from utils import auxiliary_functions as af
from nfvo_db import HTTP_Unauthorized, HTTP_Bad_Request, HTTP_Internal_Server_Error, HTTP_Not_Found,\
    HTTP_Conflict

global global_config

def get_flavorlist(mydb, vnf_id, nfvo_tenant=None):
    '''Obtain flavorList
    return result, content:
        <0, error_text upon error
        nb_records, flavor_list on success
    '''
    WHERE_dict={}
    WHERE_dict['vnf_id'] = vnf_id
    if nfvo_tenant is not None:
        WHERE_dict['nfvo_tenant_id'] = nfvo_tenant
    
    #result, content = mydb.get_table(FROM='vms join vnfs on vms.vnf_id = vnfs.uuid',SELECT=('uuid'),WHERE=WHERE_dict )
    #result, content = mydb.get_table(FROM='vms',SELECT=('vim_flavor_id',),WHERE=WHERE_dict )
    result, content = mydb.get_table(FROM='vms join flavors on vms.flavor_id=flavors.uuid',SELECT=('flavor_id',),WHERE=WHERE_dict )
    if result < 0:
        print "nfvo.get_flavorlist error %d %s" % (result, content)
        return -result, content
    print "get_flavor_list result:", result
    print "get_flavor_list content:", content
    flavorList=[]
    for flavor in content:
        flavorList.append(flavor['flavor_id'])
    return result, flavorList

def get_imagelist(mydb, vnf_id, nfvo_tenant=None):
    '''Obtain imageList
    return result, content:
        <0, error_text upon error
        nb_records, flavor_list on success
    '''
    WHERE_dict={}
    WHERE_dict['vnf_id'] = vnf_id
    if nfvo_tenant is not None:
        WHERE_dict['nfvo_tenant_id'] = nfvo_tenant
    
    #result, content = mydb.get_table(FROM='vms join vnfs on vms-vnf_id = vnfs.uuid',SELECT=('uuid'),WHERE=WHERE_dict )
    result, content = mydb.get_table(FROM='vms join images on vms.image_id=images.uuid',SELECT=('image_id',),WHERE=WHERE_dict )
    if result < 0:
        print "nfvo.get_imagelist error %d %s" % (result, content)
        return -result, content
    print "get_image_list result:", result
    print "get_image_list content:", content
    imageList=[]
    for image in content:
        imageList.append(image['image_id'])
    return result, imageList

def get_vim(mydb, nfvo_tenant=None, datacenter_id=None, datacenter_name=None, vim_tenant=None):
    '''Obtain a dictionary of VIM (datacenter) classes with some of the input parameters
    return result, content:
        <0, error_text upon error
        NUMBER, dictionary with datacenter_id: vim_class with these keys: 
            'nfvo_tenant_id','datacenter_id','vim_tenant_id','vim_url','vim_url_admin','datacenter_name','type','user','passwd'
    '''
    WHERE_dict={}
    if nfvo_tenant     is not None:  WHERE_dict['nfvo_tenant_id'] = nfvo_tenant
    if datacenter_id   is not None:  WHERE_dict['d.uuid']  = datacenter_id
    if datacenter_name is not None:  WHERE_dict['d.name']  = datacenter_name
    if vim_tenant      is not None:  WHERE_dict['vt.vim_tenant_id']  = vim_tenant
    if nfvo_tenant or vim_tenant:
        from_= 'tenants_datacenters as td join datacenters as d on td.datacenter_id=d.uuid join vim_tenants as vt on td.vim_tenant_id=vt.uuid'
        select_ = ('type','config','d.uuid as datacenter_id', 'vim_url', 'vim_url_admin', 'd.name as datacenter_name',
                   'vt.uuid as vim_tenants_uuid','vt.vim_tenant_name as vim_tenant_name','vt.vim_tenant_id as vim_tenant_id',
                   'user','passwd')
    else:
        from_ = 'datacenters as d'
        select_ = ('type','config','d.uuid as datacenter_id', 'vim_url', 'vim_url_admin', 'd.name as datacenter_name')
    result, content = mydb.get_table(FROM=from_, SELECT=select_, WHERE=WHERE_dict )
    if result < 0:
        print "nfvo.get_vim error %d %s" % (result, content)
        return result, content
    elif result==0:
        print "nfvo.get_vim not found a valid VIM with the input params " + str(WHERE_dict)
        return -HTTP_Not_Found, "datacenter not found for " +  json.dumps(WHERE_dict)
    #print content
    vim_dict={}
    for vim in content:
        extra={'vim_tenants_uuid': vim.get('vim_tenants_uuid')}
        if vim["config"] != None:
            extra.update(json.loads(vim["config"]))
        if vim["type"]=="openvim":
            vim_dict[ vim['datacenter_id'] ] = vimconnector.vimconnector(
                            uuid=vim['datacenter_id'], name=vim['datacenter_name'],
                            tenant=vim.get('vim_tenant_id'), 
                            url=vim['vim_url'], url_admin=vim['vim_url_admin'], 
                            user=vim.get('user'), passwd=vim.get('passwd'),
                            config=extra
                    )
        elif vim["type"]=="openstack":
            vim_dict[ vim['datacenter_id'] ] = osconnector.osconnector(
                            uuid=vim['datacenter_id'], name=vim['datacenter_name'],
                            tenant=vim.get('vim_tenant_name'), 
                            url=vim['vim_url'], url_admin=vim['vim_url_admin'], 
                            user=vim.get('user'),passwd=vim.get('passwd'),
                            config=extra
                    )
        else:
            return -HTTP_Internal_Server_Error, "Unknown vim type %s" % vim["type"]
    return len(vim_dict), vim_dict

def rollback(mydb,  vims, rollback_list):
    undeleted_items=[]
    #delete things by reverse order 
    for i in range(len(rollback_list)-1, -1, -1):
        item = rollback_list[i]
        if item["where"]=="vim":
            if item["vim_id"] not in vims:
                continue
            vim=vims[ item["vim_id"] ]
            if item["what"]=="image":
                result, message = vim.delete_tenant_image(item["uuid"])
                if result < 0:
                    print "Error in rollback. Not possible to delete VIM image '%s'. Message: %s" % (item["uuid"],message)
                    undeleted_items.append("image %s from VIM %s" % (item["uuid"],vim["name"]))
                else:
                    result, message = mydb.delete_row_by_dict(FROM="datacenters_images", WEHRE={"datacenter_id": vim["datacenter_id"], "vim_id":item["uuid"]})
                    if result < 0:
                        print "Error in rollback. Not possible to delete image '%s' from DB.dacenters_images. Message: %s" % (item["uuid"],message)
            elif item["what"]=="flavor":
                result, message = vim.delete_tenant_flavor(item["uuid"])
                if result < 0:
                    print "Error in rollback. Not possible to delete VIM flavor '%s'. Message: %s" % (item["uuid"],message)
                    undeleted_items.append("flavor %s from VIM %s" % (item["uuid"],vim["name"]))
                else:
                    result, message = mydb.delete_row_by_dict(FROM="datacenters_flavos", WEHRE={"datacenter_id": vim["datacenter_id"], "vim_id":item["uuid"]})
                    if result < 0:
                        print "Error in rollback. Not possible to delete flavor '%s' from DB.dacenters_flavors. Message: %s" % (item["uuid"],message)
            elif item["what"]=="network":
                result, message = vim.delete_tenant_network(item["uuid"])
                if result < 0:
                    print "Error in rollback. Not possible to delete VIM network  '%s'. Message: %s" % (item["uuid"],message)
                    undeleted_items.append("network %s from VIM %s" % (item["uuid"],vim["name"]))
            elif item["what"]=="vm":
                result, message = vim.delete_tenant_vminstance(item["uuid"])
                if result < 0:
                    print "Error in rollback. Not possible to delete VIM VM  '%s'. Message: %s" % (item["uuid"],message)
                    undeleted_items.append("VM %s from VIM %s" % (item["uuid"],vim["name"]))
        else: # where==mano
            if item["what"]=="image":
                result, message = mydb.delete_row_by_dict(FROM="images", WEHRE={"uuid": item["uuid"]})
                if result < 0:
                    print "Error in rollback. Not possible to delete image '%s' from DB.images. Message: %s" % (item["uuid"],message)
                    undeleted_items.append("image %s" % (item["uuid"]))
            elif item["what"]=="flavor":
                result, message = mydb.delete_row_by_dict(FROM="flavors", WEHRE={"uuid": item["uuid"]})
                if result < 0:
                    print "Error in rollback. Not possible to delete flavor '%s' from DB.flavors. Message: %s" % (item["uuid"],message)
                    undeleted_items.append("flavor %s" % (item["uuid"]))
    if len(undeleted_items)==0: 
        return True," Rollback successful."
    else:
        return False," Rollback fails to delete: " + str(undeleted_items)
  
def check_vnf_descriptor(vnf_descriptor):
    global global_config
    #TODO:
    #We should check if the info in external_connections matches with the one in the vnfcs
    #We should check if the info in internal_connections matches with the one in the vnfcs
    #We should check that internal-connections of type "ptp" have only 2 elements
    #We should check if the name exists in the NFVO database (vnfs table)
    #We should check if the path where we should store the YAML file already exists. In that case, we should return error. 
    vnf_filename=global_config['vnf_repository'] + "/" +vnf_descriptor['vnf']['name'] + ".vnfd"
    if os.path.exists(vnf_filename):
        print "WARNING: The VNF descriptor already exists in the VNF repository"
    return 200, None

def create_or_use_image(mydb, vims, image_dict, rollback_list, only_create_at_vim=False):
    #look if image exist
    if only_create_at_vim:
        image_mano_id = image_dict['uuid']
    else:
        res,content = mydb.get_table(FROM="images", WHERE={'location':image_dict['location'], 'metadata':image_dict['metadata']})
        if res>=1:
            image_mano_id = content[0]['uuid']
        elif res<0:
            return res, content
        else:
            #create image
            temp_image_dict={'name':image_dict['name'],         'description':image_dict.get('description',None),
                            'location':image_dict['location'],  'metadata':image_dict.get('metadata',None)
                            }
            res,content = mydb.new_row('images', temp_image_dict, tenant_id=None, add_uuid=True)
            if res>0:
                image_mano_id= content
                rollback_list.append({"where":"mano", "what":"image","uuid":image_mano_id})
            else:
                return res if res<0 else -1, content
    #create image at every vim
    for vim_id,vim in vims.items():
        image_created="false"
        #look at database
        res_db,image_db = mydb.get_table(FROM="datacenters_images", WHERE={'datacenter_id':vim_id, 'image_id':image_mano_id})
        if res_db<0:
            return res_db, image_db
        #look at VIM if this image exist
        res_vim, image_vim_id = vim.get_image_id_from_path(image_dict['location'])
        if res_vim < 0:
            print "Error contacting VIM to know if the image %s existed previously." %image_vim_id
            continue
        elif res_vim==0:
            #Create the image in VIM
            result, image_vim_id = vim.new_tenant_image(image_dict)
            if result < 0:
                print "Error creating image at VIM: %s." %image_vim_id
                continue
            else:
                rollback_list.append({"where":"vim", "vim_id": vim_id, "what":"image","uuid":image_vim_id})
                image_created="true"
            
        #if reach here the image has been create or exist
        if res_db==0:
            #add new vim_id at datacenters_images
            mydb.new_row('datacenters_images', {'datacenter_id':vim_id, 'image_id':image_mano_id, 'vim_id': image_vim_id, 'created':image_created})
        elif image_db[0]["vim_id"]!=image_vim_id:
            #modify existing vim_id at datacenters_images
            mydb.update_rows('datacenters_images', UPDATE={'vim_id':image_vim_id}, WHERE={'datacenter_id':vim_id, 'image_id':image_mano_id})
            
    return 1, image_vim_id if only_create_at_vim else image_mano_id

def create_or_use_flavor(mydb, vims, flavor_dict, rollback_list, only_create_at_vim=False):
    temp_flavor_dict= {'disk':flavor_dict.get('disk',1),
            'ram':flavor_dict.get('ram'),
            'vcpus':flavor_dict.get('vcpus'),
        }
    if 'extended' in flavor_dict and flavor_dict['extended']==None:
        del flavor_dict['extended']
    if 'extended' in flavor_dict:
        temp_flavor_dict['extended']=json.dumps(flavor_dict['extended'])

    #look if flavor exist
    if only_create_at_vim:
        flavor_mano_id = flavor_dict['uuid']
    else:
        res,content = mydb.get_table(FROM="flavors", WHERE=temp_flavor_dict)
        if res>=1:
            flavor_mano_id = content[0]['uuid']
        elif res<0:
            return res, content
        else:
            #create flavor
            #create one by one the images of aditional disks
            dev_image_list=[] #list of images
            if 'extended' in flavor_dict and flavor_dict['extended']!=None:
                dev_nb=0
                for device in flavor_dict['extended'].get('devices',[]):
                    if "image" not in device:
                        continue
                    image_dict={'location':device['image'], 'name':flavor_dict['name']+str(dev_nb)+"-img", 'description':flavor_dict.get('description')}
                    image_metadata_dict = device('image metadata', None)
                    image_metadata_str = None
                    if image_metadata_dict != None: 
                        image_metadata_str = json.dumps(image_metadata_dict)
                    image_dict['metadata']=image_metadata_str
                    res, image_id = create_or_use_image(mydb, vims, image_dict, rollback_list)
                    if res < 0:
                        return res, image_id + rollback(mydb, vims, rollback_list)[1]
                    print "Additional disk image id for VNFC %s: %s" % (flavor_dict['name']+str(dev_nb)+"-img", image_id)
                    dev_image_list.append(image_id)
                    dev_nb += 1                
            temp_flavor_dict['name'] = flavor_dict['name']
            temp_flavor_dict['description'] = flavor_dict.get('description',None)
            res,content = mydb.new_row('flavors', temp_flavor_dict, tenant_id=None, add_uuid=True)
            if res>0:
                flavor_mano_id= content
                rollback_list.append({"where":"mano", "what":"flavor","uuid":flavor_mano_id})
            else:
                return res if res<0 else -1, content
    #create flavor at every vim
    if 'uuid' in flavor_dict:
        del flavor_dict['uuid']
    flavor_vim_id=None
    for vim_id,vim in vims.items():
        flavor_created="false"
        #look at database
        res_db,flavor_db = mydb.get_table(FROM="datacenters_flavors", WHERE={'datacenter_id':vim_id, 'flavor_id':flavor_mano_id})
        if res_db<0:
            return res_db, flavor_db
        #look at VIM if this flavor exist  SKIPPED
        #res_vim, flavor_vim_id = vim.get_flavor_id_from_path(flavor_dict['location'])
        #if res_vim < 0:
        #    print "Error contacting VIM to know if the flavor %s existed previously." %flavor_vim_id
        #    continue
        #elif res_vim==0:
    
        #Create the flavor in VIM
        #Translate images at devices from MANO id to VIM id
        error=False
        if 'extended' in flavor_dict and flavor_dict['extended']!=None and "devices" in flavor_dict['extended']:
            #make a copy of original devices
            devices_original=[]
            for device in flavor_dict["extended"].get("devices",[]):
                dev={}
                dev.update(device)
                devices_original.append(dev)
                if 'image' in dev:
                    del dev['image']
                if 'image metadata' in dev:
                    del dev['image metadata']
            for index in range(0,len(devices_original)) :
                device=devices_original[index]
                if "image" not in device:
                    continue
                image_dict={'location':device['image'], 'name':flavor_dict['name']+str(dev_nb)+"-img", 'description':flavor_dict.get('description')}
                image_metadata_dict = device.get('image metadata', None)
                image_metadata_str = None
                if image_metadata_dict != None: 
                    image_metadata_str = json.dumps(image_metadata_dict)
                image_dict['metadata']=image_metadata_str
                r,image_vim_id=create_or_use_image(mydb, vims, image_dict, rollback_list, only_create_at_vim=True)
                if r<0:
                    print "Error creating device image for flavor at VIM: %s." %image_vim_id
                    error=True
                    break
                flavor_dict["extended"]["devices"][index]['imageRef']=image_vim_id
        if error:
            continue
        if res_db>0:
            #TODO check that this vim_id exist in VIM, if not create
            flavor_vim_id=flavor_db[0]["vim_id"]
            continue
        #create flavor at vim
        print "nfvo.create_or_use_flavor() adding flavor to VIM %s" % vim["name"]
        result, flavor_vim_id = vim.new_tenant_flavor(flavor_dict)
        
        if result < 0:
            print "Error creating flavor at VIM %s: %s." %(vim["name"], flavor_vim_id)
            continue
        else:
            rollback_list.append({"where":"vim", "vim_id": vim_id, "what":"flavor","uuid":flavor_vim_id})
            flavor_created="true"
        
        #if reach here the flavor has been create or exist
        if res_db==0:
            #add new vim_id at datacenters_flavors
            mydb.new_row('datacenters_flavors', {'datacenter_id':vim_id, 'flavor_id':flavor_mano_id, 'vim_id': flavor_vim_id, 'created':flavor_created})
        elif flavor_db[0]["vim_id"]!=flavor_vim_id:
            #modify existing vim_id at datacenters_flavors
            mydb.update_rows('datacenters_flavors', UPDATE={'vim_id':flavor_vim_id}, WHERE={'datacenter_id':vim_id, 'flavor_id':flavor_mano_id})
            
    return 1, flavor_vim_id if only_create_at_vim else flavor_mano_id

def new_vnf(mydb,nfvo_tenant,vnf_descriptor,public=True,physical=False,datacenter=None,vim_tenant=None):
    global global_config
    
    # TODO: With future versions of the VNFD, different code might be applied for each version.
    # Depending on the new structure of the VNFD (identified by version in vnf_descriptor), we should have separate code for each version, or integrated code with small changes.  
    
    # Step 1. Check the VNF descriptor
    #TODO:
    #WARNING!!!!!!!!!!!!!. For the moment, this check is dummy and returns 200
    #TODO: check that interfaces are consistent in the different sections of the descriptor: bridge and interfaces
    #TODO: external-connection: VM should exist and interface too
    result, message = check_vnf_descriptor(vnf_descriptor)
    if result < 0:
        print "new_vnf error: %s" %message
        return result, "VNF de: %s" %message

    print "Checking that nfvo_tenant_id exists and getting the VIM URI and the VIM tenant_id"

    # Step 2. Get the URL of the VIM from the nfvo_tenant and the datacenter
    result, vims = get_vim(mydb, nfvo_tenant, datacenter, None, vim_tenant)
    if result < 0:
        print "nfvo.new_vnf() error. Datacenter not found"
        return result, vims

    # Step 4. Review the descriptor and add missing  fields
    # TODO: to be moved to step 1????
    #print vnf_descriptor
    print "Refactoring VNF descriptor with fields: description, physical (default: false), public (default: true)"
    vnf_name = vnf_descriptor['vnf']['name']
    vnf_descriptor['vnf']['description'] = vnf_descriptor['vnf'].get("description", vnf_name)
    vnf_descriptor['vnf']['physical'] = vnf_descriptor['vnf'].get("physical", False)
    vnf_descriptor['vnf']['public'] = vnf_descriptor['vnf'].get("public", True)
    print vnf_descriptor
    #TODO:
    #If VNF is public, we should take it into account when creating images and flavors
    
    # Step 5. Check internal connections
    # TODO: to be moved to step 1????
    internal_connections=vnf_descriptor['vnf'].get('internal_connections',[])
    for ic in internal_connections:
        if len(ic['elements'])>2 and ic['type']=='ptp':
            return -HTTP_Bad_Request, "Mismatch 'type':'ptp' with %d elements at 'vnf':'internal-conections'['name':'%s']. Change 'type' to 'data'" %(len(ic), ic['name'])
        elif len(ic['elements'])==2 and ic['type']=='data':
            return -HTTP_Bad_Request, "Mismatch 'type':'data' with 2 elements at 'vnf':'internal-conections'['name':'%s']. Change 'type' to 'ptp'" %(ic['name'])
    
    # Step 6. For each VNFC in the descriptor, flavors and images are created in the VIM 
    print 'BEGIN creation of VNF "%s"' % vnf_name
    print "VNF %s: consisting of %d VNFC(s)" % (vnf_name,len(vnf_descriptor['vnf']['VNFC']))
    
    #For each VNFC, we add it to the VNFCDict and we  create a flavor.
    VNFCDict = {}     # Dictionary, key: VNFC name, value: dict with the relevant information to create the VNF and VMs in the MANO database
    rollback_list = []    # It will contain the new images created in mano. It is used for rollback

    try:
        print "Creating additional disk images and new flavors in the VIM for each VNFC"
        for vnfc in vnf_descriptor['vnf']['VNFC']:
            VNFCitem={}
            VNFCitem["name"] = vnfc['name']
            VNFCitem["description"] = vnfc.get("description", 'VM %s of the VNF %s' %(vnfc['name'],vnf_name))
            
            print "Flavor name: %s. Description: %s" % (VNFCitem["name"]+"-flv", VNFCitem["description"])
            
            myflavorDict = {}
            myflavorDict["name"] = vnfc['name']+"-flv"
            myflavorDict["description"] = VNFCitem["description"]
            myflavorDict["ram"] = vnfc.get("ram", 0)
            myflavorDict["vcpus"] = vnfc.get("vcpus", 0)
            myflavorDict["disk"] = vnfc.get("disk", 1)
            myflavorDict["extended"] = {}
            
            devices = vnfc.get("devices")
            if devices != None:
                myflavorDict["extended"]["devices"] = devices
            
            # TODO:
            # Mapping from processor models to rankings should be available somehow in the NFVO. They could be taken from VIM or directly from a new database table
            # Another option is that the processor in the VNF descriptor specifies directly the ranking of the host 
            
            # Previous code has been commented
            #if vnfc['processor']['model'] == "Intel(R) Xeon(R) CPU E5-4620 0 @ 2.20GHz" :
            #    myflavorDict["flavor"]['extended']['processor_ranking'] = 200
            #elif vnfc['processor']['model'] == "Intel(R) Xeon(R) CPU E5-2697 v2 @ 2.70GHz" :
            #    myflavorDict["flavor"]['extended']['processor_ranking'] = 300
            #else:
            #    result2, message = rollback(myvim, myvimURL, myvim_tenant, flavorList, imageList)
            #    if result2:
            #        print "Error creating flavor: unknown processor model. Rollback successful."
            #        return -HTTP_Bad_Request, "Error creating flavor: unknown processor model. Rollback successful."
            #    else:
            #        return -HTTP_Bad_Request, "Error creating flavor: unknown processor model. Rollback fail: you need to access VIM and delete the following %s" % message
            myflavorDict['extended']['processor_ranking'] = 100  #Hardcoded value, while we decide when the mapping is done
     
            if 'numas' in vnfc and len(vnfc['numas'])>0:
                myflavorDict['extended']['numas'] = vnfc['numas']

            #print myflavorDict
    
            # Step 6.2 New flavors are created in the VIM
            res, flavor_id = create_or_use_flavor(mydb, vims, myflavorDict, rollback_list)
            if res < 0:
                return res, flavor_id + rollback(mydb, vims, rollback_list)[1]

            print "Flavor id for VNFC %s: %s" % (vnfc['name'],flavor_id)
            VNFCitem["flavor_id"] = flavor_id
            VNFCDict[vnfc['name']] = VNFCitem
            
        print "Creating new images in the VIM for each VNFC"
        # Step 6.3 New images are created in the VIM
        #For each VNFC, we must create the appropriate image.
        #This "for" loop might be integrated with the previous one 
        #In case this integration is made, the VNFCDict might become a VNFClist.
        for vnfc in vnf_descriptor['vnf']['VNFC']:
            print "Image name: %s. Description: %s" % (vnfc['name']+"-img", VNFCDict[vnfc['name']]['description'])
            image_dict={'location':vnfc['VNFC image'], 'name':vnfc['name']+"-img", 'description':VNFCDict[vnfc['name']]['description']}
            image_metadata_dict = vnfc.get('image metadata', None)
            image_metadata_str = None
            if image_metadata_dict is not None: 
                image_metadata_str = json.dumps(image_metadata_dict)
            image_dict['metadata']=image_metadata_str
            #print "create_or_use_image", mydb, vims, image_dict, rollback_list
            res, image_id = create_or_use_image(mydb, vims, image_dict, rollback_list)
            if res < 0:
                return res, image_id + rollback(mydb, vims, rollback_list)[1]
            print "Image id for VNFC %s: %s" % (vnfc['name'],image_id)
            VNFCDict[vnfc['name']]["image_id"] = image_id
            VNFCDict[vnfc['name']]["image_path"] = vnfc['VNFC image']

    except KeyError as e:
        print "Error while creating a VNF. KeyError: " + str(e)
        _, message = rollback(mydb, vims, rollback_list)
        return -HTTP_Internal_Server_Error, "Error while creating a VNF. KeyError " + str(e) + "." + message
        
    # Step 7. Storing the VNF in the repository
    print "Storing YAML file of the VNF"
    vnf_descriptor_filename = global_config['vnf_repository'] + "/" + vnf_name + ".vnfd"
    if not os.path.exists(vnf_descriptor_filename):
        f = file(vnf_descriptor_filename, "w")
        f.write(json.dumps(vnf_descriptor, indent=4) + os.linesep)
        f.close()

    # Step 8. Adding the VNF to the NFVO DB
    try:
        result, vnf_id = mydb.new_vnf_as_a_whole(nfvo_tenant,vnf_name,vnf_descriptor_filename,vnf_descriptor,VNFCDict)
    except KeyError as e:
        print "Error while creating a VNF. KeyError: " + str(e)
        _, message = rollback(mydb, vims, rollback_list)
        return -HTTP_Internal_Server_Error, "Error while creating a VNF. KeyError " + str(e) + "." + message
    
    if result < 0:
        _, message = rollback(mydb, vims, rollback_list)
        return result, vnf_id + "." + message

    return 200,vnf_id

def delete_vnf(mydb,nfvo_tenant,vnf_id,datacenter=None,vim_tenant=None):
    print "Checking that nfvo_tenant_id exists and getting the VIM URI and the VIM tenant_id"
    result, vims = get_vim(mydb, nfvo_tenant, datacenter, None, vim_tenant)
    if result < 0:
        return -HTTP_Unauthorized, "delete_vnf error. No VIM found for tenant '%s'" % nfvo_tenant

    print "Checking if it is a valid uuid and, if not, getting the uuid assuming that the name was provided"
    if not af.check_valid_uuid(vnf_id):
        result,vnf_id = mydb.get_uuid_from_name('vnfs',vnf_id)
        if result==0:
            return -HTTP_Not_Found, "No VNF found for tenant. '%s'" % vnf_id
        elif result<0:
            return -HTTP_Internal_Server_Error, "delete_vnf error. Internal server error. %s" % vnf_id
        elif result>1:
            return -HTTP_Not_Found, "Found more than one VNF. %s" % vnf_id 
    
    print "Getting the list of flavors and tenants of the VNF"
    result,flavorList = get_flavorlist(mydb, vnf_id) 
    if result < 0:
        print flavorList
    elif result==0:
        print "delete_vnf error. No flavors found for the VNF id '%s'" % vnf_id
    
    result,imageList = get_imagelist(mydb, vnf_id)
    print "imageList", imageList
    if result < 0:
        print imageList
    elif result==0:
        print "delete_vnf error. No images found for the VNF id '%s'" % vnf_id
    
    result, content = mydb.delete_row('vnfs', vnf_id, nfvo_tenant)
    if result == 0:
        return -HTTP_Not_Found, content
    elif result >0:
        print content
    else:
        print "delete_vnf error",result, content
        return result, content
    
    undeletedItems = []
    for flavor in flavorList:
        #check if flavor is used by other vnf
        r,c = mydb.get_table(FROM='vms', WHERE={'flavor_id':flavor} )
        if r < 0:
            print 'delete_vnf_error. Not possible to delete VIM flavor "%s". %s' % (flavor,c)
            undeletedItems.append("flavor "+ flavor["flavor_id"])
        elif r > 0:
            print 'Flavor %s not deleted because it is being used by another VNF %s' %(flavor,str(c))
            continue
        #flavor not used, must be deleted
        #delelte at VIM
        r,c = mydb.get_table(FROM='datacenters_flavors', WHERE={'flavor_id':flavor})
        if r>0:
            for flavor_vim in c:
                if flavor_vim["datacenter_id"] not in vims:
                    continue
                if flavor_vim['created']=='false': #skip this flavor because not created by openmano
                    continue
                myvim=vims[ flavor_vim["datacenter_id"] ]
                result, message = myvim.delete_tenant_flavor(flavor_vim["vim_id"])
                if result < 0:
                    print 'delete_vnf_error. Not possible to delete VIM flavor "%s". Message: %s' % (flavor,message)
                    if result != -HTTP_Not_Found:
                        undeletedItems.append("flavor %s from VIM %s" % (flavor_vim["vim_id"], flavor_vim["datacenter_id"] ))
        #delete flavor from Database, using table flavors and with cascade foreign key also at datacenters_flavors
        result, content = mydb.delete_row('flavors', flavor)
        if result <0:
            undeletedItems.append("flavor %s" % flavor)
        
    for image in imageList:
        #check if image is used by other vnf
        r,c = mydb.get_table(FROM='vms', WHERE={'image_id':image} )
        if r < 0:
            print 'delete_vnf_error. Not possible to delete VIM image "%s". %s' % (image,c)
            undeletedItems.append("image "+ image["image_id"])
        elif r > 0:
            print 'Image %s not deleted because it is being used by another VNF %s' %(image,str(c))
            continue
        #image not used, must be deleted
        #delelte at VIM
        r,c = mydb.get_table(FROM='datacenters_images', WHERE={'image_id':image})
        if r>0:
            for image_vim in c:
                if image_vim["datacenter_id"] not in vims:
                    continue
                if image_vim['created']=='false': #skip this image because not created by openmano
                    continue
                myvim=vims[ image_vim["datacenter_id"] ]
                result, message = myvim.delete_tenant_image(image_vim["vim_id"])
                if result < 0:
                    print 'delete_vnf_error. Not possible to delete VIM image "%s". Message: %s' % (image,message)
                    if result != -HTTP_Not_Found:
                        undeletedItems.append("image %s from VIM %s" % (image_vim["vim_id"], image_vim["datacenter_id"] ))
        #delete image from Database, using table images and with cascade foreign key also at datacenters_images
        result, content = mydb.delete_row('images', image)
        if result <0:
            undeletedItems.append("image %s" % image)

    if undeletedItems: 
        return 200, "delete_vnf error. Undeleted: %s" %(undeletedItems)
    
    return 200,vnf_id

def get_hosts_info(mydb, nfvo_tenant_id, datacenter_name=None):
    result, vims = get_vim(mydb, nfvo_tenant_id, None, datacenter_name)
    if result < 0:
        return result, vims
    myvim = vims.values()[0]
    result,servers =  myvim.get_hosts_info()
    if result < 0:
        return result, servers
    topology = {'name':myvim['name'] , 'servers': servers}
    return result, topology

def get_hosts(mydb, nfvo_tenant_id):
    result, vims = get_vim(mydb, nfvo_tenant_id)
    if result < 0:
        return result, vims
    myvim = vims.values()[0]
    result,hosts =  myvim.get_hosts()
    if result < 0:
        return result, hosts
    print '==================='
    print 'hosts '+ json.dumps(hosts, indent=4)

    datacenter = {'Datacenters': [ {'name':myvim['name'],'servers':[]} ] }
    for host in hosts:
        server={'name':host['name'], 'vms':[]}
        for vm in host['instances']:
            #get internal name and model
            r,c = mydb.get_table(SELECT=('name',), FROM='instance_vms as iv join vms on iv.vm_id=vms.uuid',\
                WHERE={'vim_vm_id':vm['id']} )
            if r==0:
                print "nfvo.get_hosts virtual machine at VIM (%s) not found at tidnfvo" % vm['id']
                continue
            if r<0:
                print "nfvo.get_hosts virtual machine at VIM (%s) error %d %s" % (vm['id'], r, c)
                continue
            server['vms'].append( {'name':vm['name'] , 'model':c[0]['name']} )
        datacenter['Datacenters'][0]['servers'].append(server)
    #return -400, "en construccion"
    
    #print 'datacenters '+ json.dumps(datacenter, indent=4)
    return result, datacenter

def new_scenario(mydb, nfvo_tenant_id, topo):
    # TODO: With future versions of the NSD, different code might be applied for each version.
    # Depending on the new structure of the NSD (identified by version in topo), we should have separate code for each version, or integrated code with small changes.  

#    result, vims = get_vim(mydb, nfvo_tenant_id)
#    if result < 0:
#        return result, vims
#1: parse input
#1.1: get VNFs and external_networks (other_nets). 
    vnfs={}
    other_nets={}  #external_networks, bridge_networks and data_networkds
    nodes = topo['topology']['nodes']
    for k in nodes.keys():
        if nodes[k]['type'] == 'VNF':
            vnfs[k] = nodes[k]
            vnfs[k]['ifaces'] = {}
        elif nodes[k]['type'] == 'other_network' or nodes[k]['type'] == 'external_network': 
            other_nets[k] = nodes[k]
            other_nets[k]['external']=True
        elif nodes[k]['type'] == 'network': 
            other_nets[k] = nodes[k]
            other_nets[k]['external']=False
        

#1.2: Check that VNF are present at database table vnfs. Insert uuid, desctiption and external interfaces
    for name,vnf in vnfs.items():
        WHERE_={}
        error_text = ""
        error_pos = "'topology':'nodes':'" + name + "'"
        if 'vnf_id' in vnf:
            error_text += " 'vnf_id' " +  vnf['vnf_id']
            WHERE_['uuid'] = vnf['vnf_id']
        if 'VNF model' in vnf:
            error_text += " 'VNF model' " +  vnf['VNF model']
            WHERE_['name'] = vnf['VNF model']
        if len(WHERE_) == 0:
            return -HTTP_Bad_Request, "needed a 'vnf_id' or 'VNF model' at " + error_pos
        r,vnf_db = mydb.get_table(SELECT=('uuid','name','description'), FROM='vnfs', WHERE=WHERE_)
        if r<0:
            print "nfvo.new_scenario Error getting vnfs",r,vnf_db
        elif r==0:
            print "nfvo.new_scenario Error" + error_text + " is not present at database"
            return -HTTP_Bad_Request, "unknown" + error_text + " at " + error_pos
        elif r>1:
            print "nfvo.new_scenario Error more than one" + error_text + " are present at database"
            return -HTTP_Bad_Request, "more than one" + error_text + " at " + error_pos + " Concrete with 'vnf_id'"
        vnf['uuid']=vnf_db[0]['uuid']
        vnf['description']=vnf_db[0]['description']
        #get external interfaces
        r,ext_ifaces = mydb.get_table(SELECT=('external_name as name','i.uuid as iface_uuid', 'i.type as type'), 
            FROM='vnfs join vms on vnfs.uuid=vms.vnf_id join interfaces as i on vms.uuid=i.vm_id', 
            WHERE={'vnfs.uuid':vnf['uuid']}, WHERE_NOTNULL=('external_name',) )
        if r<0:
            print "nfvo.new_scenario Error getting external interfaces of vnfs",r,ext_ifaces
            return -HTTP_Internal_Server_Error, "Error getting external interfaces of vnfs: " + ext_ifaces
        for ext_iface in ext_ifaces:
            vnf['ifaces'][ ext_iface['name'] ] = {'uuid':ext_iface['iface_uuid'], 'type':ext_iface['type']}

#1.4 get list of connections
    conections = topo['topology']['connections']
    conections_list = []
    for k in conections.keys():
        if type(conections[k]['nodes'])==dict: #dict with node:iface pairs
            ifaces_list = conections[k]['nodes'].items()
        elif type(conections[k]['nodes'])==list: #list with dictionary
            ifaces_list=[]
            conection_pair_list = map(lambda x: x.items(), conections[k]['nodes'] )
            for k2 in conection_pair_list:
                ifaces_list += k2
        conections_list.append(set(ifaces_list)) #from list to set to operate as a set (this conversion removes elements that are repeated in a list)
        #print set(ifaces_list)
    #check valid VNF and iface names
        for iface in ifaces_list:
            if iface[0] not in vnfs and iface[0] not in other_nets :
                return -HTTP_Bad_Request, "format error. Invalid VNF name at 'topology':'connections':'%s':'nodes':'%s'" % (str(k), iface[0])
            if iface[0] in vnfs and iface[1] not in vnfs[ iface[0] ]['ifaces']:
                return -HTTP_Bad_Request, "format error. Invalid interface name at 'topology':'connections':'%s':'nodes':'%s':'%s'" % (str(k), iface[0], iface[1])

#1.5 unify connections from the pair list to a consolidated list
    index=0
    while index < len(conections_list):
        index2 = index+1
        while index2 < len(conections_list):
            if len(conections_list[index] & conections_list[index2])>0: #common interface, join nets
                conections_list[index] |= conections_list[index2]
                del conections_list[index2]
            else:
                index2 += 1
        conections_list[index] = list(conections_list[index])  # from set to list again
        index += 1
    #for k in conections_list:
    #    print k
    


#1.6 Delete non external nets
#    for k in other_nets.keys():
#        if other_nets[k]['model']=='bridge' or other_nets[k]['model']=='dataplane_net' or other_nets[k]['model']=='bridge_net':
#            for con in conections_list:
#                delete_indexes=[]
#                for index in range(0,len(con)):
#                    if con[index][0] == k: delete_indexes.insert(0,index) #order from higher to lower
#                for index in delete_indexes:
#                    del con[index]
#            del other_nets[k]
#1.7: Check external_ports are present at database table datacenter_nets
    for k,net in other_nets.items():
        error_pos = "'topology':'nodes':'" + k + "'"
        if net['external']==False:
            if 'name' not in net:
                net['name']=k
            if 'model' not in net:
                return -HTTP_Bad_Request, "needed a 'model' at " + error_pos
            if net['model']=='bridge_net':
                net['type']='bridge';
            elif net['model']=='dataplane_net':
                net['type']='data';
            else:
                return -HTTP_Bad_Request, "unknown 'model' '"+ net['model'] +"' at " + error_pos
        else: #external
            error_text = ""
            WHERE_={}
            if 'net_id' in net:
                error_text += " 'net_id' " +  net['net_id']
                WHERE_['uuid'] = net['net_id']
            if 'model' in net:
                error_text += " 'model' " +  net['model']
                WHERE_['name'] = net['model']
            if len(WHERE_) == 0:
                return -HTTP_Bad_Request, "needed a 'net_id' or 'model' at " + error_pos
            r,net_db = mydb.get_table(SELECT=('uuid','name','description','type','shared'),
                FROM='datacenter_nets', WHERE=WHERE_ )
            if r<0:
                print "nfvo.new_scenario Error getting datacenter_nets",r,net_db
            elif r==0:
                print "nfvo.new_scenario Error" +error_text+ " is not present at database"
                return -HTTP_Bad_Request, "unknown " +error_text+ " at " + error_pos
            #elif r>1:
            #    print "nfvo.new_scenario Error more than one external_network for " +error_text+ " is present at database" 
            #    return -HTTP_Bad_Request, "more than one external_network for " +error_text+ "at "+ error_pos + " Concrete with 'net_id'" 
            other_nets[k].update(net_db[0])
    
    net_list={}
    net_nb=0  #Number of nets
    for con in conections_list:
        #check if this is connected to a external net
        other_net_index=-1
        #print
        #print "con", con
        for index in range(0,len(con)):
            #check if this is connected to a external net
            for net_key in other_nets.keys():
                if con[index][0]==net_key:
                    if other_net_index>=0:
                        error_text="There is some interface connected both to net '%s' and net '%s'" % (con[other_net_index][0], net_key) 
                        print "nfvo.new_scenario " + error_text
                        return -HTTP_Bad_Request, error_text
                    else:
                        other_net_index = index
                        net_target = net_key
                    break
        #print "other_net_index", other_net_index
        try:
            if other_net_index>=0:
                del con[other_net_index]
                if other_nets[net_target]['external'] :
                    type_='data' if len(con)>1 else 'ptp'  #an external net is connected to a external port, so it is ptp if only one connection is done to this net
                    if type_=='data' and other_nets[net_target]['type']=="ptp":
                        error_text = "Error connecting %d nodes on a not multipoint net %s" % (len(con), net_target)
                        print "nfvo.new_scenario " + error_text
                        return -HTTP_Bad_Request, error_text
                for iface in con:
                    vnfs[ iface[0] ]['ifaces'][ iface[1] ]['net_key'] = net_target
            else:
                #create a net
                net_type_bridge=False
                net_type_data=False
                net_target = "__-__net"+str(net_nb)
                net_list[net_target] = {'name': "net-"+str(net_nb), 'description':"net-%s in scenario %s" %(net_nb,topo['name']),
                    'external':False} 
                for iface in con:
                    vnfs[ iface[0] ]['ifaces'][ iface[1] ]['net_key'] = net_target
                    iface_type = vnfs[ iface[0] ]['ifaces'][ iface[1] ]['type']
                    if iface_type=='mgmt' or iface_type=='bridge':
                        net_type_bridge = True
                    else:
                        net_type_data = True
                if net_type_bridge and net_type_data:
                    error_text = "Error connection interfaces of bridge type with data type. Firs node %s, iface %s" % (iface[0], iface[1])
                    print "nfvo.new_scenario " + error_text
                    return -HTTP_Bad_Request, error_text
                elif net_type_bridge:
                    type_='bridge'
                else:
                    type_='data' if len(con)>2 else 'ptp'
                net_list[net_target]['type'] = type_
                net_nb+=1
        except Exception:
            error_text = "Error connection node %s : %s does not match any VNF or interface" % (iface[0], iface[1])
            print "nfvo.new_scenario " + error_text
            #raise e
            return -HTTP_Bad_Request, error_text

#1.8: Connect to management net all not already connected interfaces of type 'mgmt'
    #1.8.1 obtain management net 
    r,mgmt_net = mydb.get_table(SELECT=('uuid','name','description','type','shared'),
        FROM='datacenter_nets', WHERE={'name':'mgmt'} )
    #1.8.2 check all interfaces from all vnfs 
    if r>0:
        add_mgmt_net = False
        for vnf in vnfs.values():
            for iface in vnf['ifaces'].values():
                if iface['type']=='mgmt' and 'net_key' not in iface:
                    #iface not connected
                    iface['net_key'] = 'mgmt'
                    add_mgmt_net = True
        if add_mgmt_net and 'mgmt' not in net_list:
            net_list['mgmt']=mgmt_net[0]
            net_list['mgmt']['external']=True
            net_list['mgmt']['graph']={'visible':False}

    net_list.update(other_nets)
    print
    print 'net_list', net_list
    print
    print 'vnfs', vnfs
    print

#2: insert scenario. filling tables scenarios,sce_vnfs,sce_interfaces,sce_nets
    r,c = mydb.new_scenario( { 'vnfs':vnfs, 'nets':net_list,
        'nfvo_tenant_id':nfvo_tenant_id, 'name':topo['name'], 'description':topo.get('description',topo['name']) } )
    
    return r,c

def edit_scenario(mydb, nfvo_tenant_id, scenario_id, data):
    data["uuid"] = scenario_id
    data["nfvo_tenant_id"] = nfvo_tenant_id
    r,c = mydb.edit_scenario( data )
    return r,c

def start_scenario(mydb, nfvo_tenant, scenario_id, instance_scenario_name, instance_scenario_description, datacenter=None,vim_tenant=None, startvms=True):
    print "Checking that nfvo_tenant_id exists and getting the VIM URI and the VIM tenant_id"
    datacenter_id = None
    datacenter_name=None
    if datacenter != None:
        if af.check_valid_uuid(datacenter): 
            datacenter_id = datacenter
        else:
            datacenter_name = datacenter
    result, vims = get_vim(mydb, nfvo_tenant, datacenter_id, datacenter_name, vim_tenant)
    if result < 0:
        print "start_scenario error. Datacenter not found"
        return result, vims
    elif result > 1:
        print "start_scenario error. Several datacenters available, must be identify"
        return -HTTP_Bad_Request, "Several datacenters available, must be identify"
    myvim = vims.values()[0]
    myvim_tenant = myvim['tenant']
    datacenter_id = myvim['id']
    datacenter_name = myvim['name']
    vim_tenants_uuid = myvim['config']['vim_tenants_uuid']
    rollbackList=[]

    print "Checking that the scenario_id exists and getting the scenario dictionary"
    result, scenarioDict = mydb.get_scenario(scenario_id, nfvo_tenant, datacenter_id)
    if result < 0:
        print "start_scenario error. Error interacting with NFVO DB"
        return result, scenarioDict
    elif result == 0:
        print "start_scenario error. Scenario not found"
        return result, scenarioDict

    scenarioDict['vim_tenant_id'] = myvim_tenant
    scenarioDict['datacenter_id'] = datacenter_id
    print '================scenarioDict======================='
    #print json.dumps(scenarioDict, indent=4)
    print 'BEGIN launching instance scenario "%s" based on "%s"' % (instance_scenario_name,scenarioDict['name'])

    print "Scenario %s: consisting of %d VNF(s)" % (scenarioDict['name'],len(scenarioDict['vnfs']))
    print yaml.safe_dump(scenarioDict, indent=4, default_flow_style=False)
    
    auxNetDict = {}   #Auxiliar dictionary. First key:'scenario' or sce_vnf uuid. Second Key: uuid of the net/sce_net. Value: vim_net_id
    auxNetDict['scenario'] = {}
    
    print "1. Creating new nets (sce_nets) in the VIM"
    for sce_net in scenarioDict['nets']:
        print "Net name: %s. Description: %s" % (sce_net["name"], sce_net["description"])
        
        myNetName = "%s-%s" % (scenarioDict['name'],sce_net['name'])
        myNetName = myNetName[0:36] #limit length
        myNetType = sce_net['type']
        myNetDict = {}
        myNetDict["name"] = myNetName
        myNetDict["type"] = myNetType
        myNetDict["tenant_id"] = myvim_tenant
        #TODO:
        #We should use the dictionary as input parameter for new_tenant_network
        print myNetDict
        if not sce_net["external"]:
            result, network_id = myvim.new_tenant_network(myNetName, myNetType)
            if result < 0:
                print "Error creating network: %s." %network_id
                _, message = rollback(mydb, vims, rollbackList)
                return result, "Error creating network: "+ network_id + "."+message

            print "New VIM network created for scenario %s. Network id:  %s" % (scenarioDict['name'],network_id)
            sce_net['vim_id'] = network_id
            auxNetDict['scenario'][sce_net['uuid']] = network_id
            rollbackList.append({'what':'network','where':'vim','vim_id':datacenter_id,'uuid':network_id})
        else:
            if sce_net['vim_id'] == None:
                error_text = "Error, datacenter '%s' does not have external network '%s'." % (datacenter_name, sce_net['name'])
                _, message = rollback(mydb, vims, rollbackList)
                print "nfvo.start_scenario: " + error_text
                return -HTTP_Bad_Request, error_text
            print "Using existent VIM network for scenario %s. Network id %s" % (scenarioDict['name'],sce_net['vim_id'])
            auxNetDict['scenario'][sce_net['uuid']] = sce_net['vim_id']
    
    print "2. Creating new nets (vnf internal nets) in the VIM"
    #For each vnf net, we create it and we add it to instanceNetlist.
    for sce_vnf in scenarioDict['vnfs']:
        for net in sce_vnf['nets']:
            print "Net name: %s. Description: %s" % (net["name"], net["description"])
            
            myNetName = "%s-%s" % (scenarioDict['name'],net['name'])
            myNetName = myNetName[0:36] #limit length
            myNetType = net['type']
            myNetDict = {}
            myNetDict["name"] = myNetName
            myNetDict["type"] = myNetType
            myNetDict["tenant_id"] = myvim_tenant
            print myNetDict
            #TODO:
            #We should use the dictionary as input parameter for new_tenant_network
            result, network_id = myvim.new_tenant_network(myNetName, myNetType)
            if result < 0:
                error_text="Error creating network: %s." % network_id
                _, message = rollback(mydb, vims, rollbackList)
                error_text += message
                print "start_scenario: " + error_text
                return result, error_text
            print "VIM network id for scenario %s: %s" % (scenarioDict['name'],network_id)
            net['vim_id'] = network_id
            if sce_vnf['uuid'] not in auxNetDict:
                auxNetDict[sce_vnf['uuid']] = {}
            auxNetDict[sce_vnf['uuid']][net['uuid']] = network_id
            rollbackList.append({'what':'network','where':'vim','vim_id':datacenter_id,'uuid':network_id})

    print "auxNetDict:"
    print yaml.safe_dump(auxNetDict, indent=4, default_flow_style=False)
    
    print "3. Creating new vm instances in the VIM"
    #myvim.new_tenant_vminstance(self,vimURI,tenant_id,name,description,image_id,flavor_id,net_dict)
    i = 0
    for sce_vnf in scenarioDict['vnfs']:
        for vm in sce_vnf['vms']:
            i += 1
            myVMDict = {}
            #myVMDict['name'] = "%s-%s-%s" % (scenarioDict['name'],sce_vnf['name'], vm['name'])
            myVMDict['name'] = "%s-%s-VM%d" % (scenarioDict['name'],sce_vnf['name'],i)
            #myVMDict['description'] = vm['description']
            myVMDict['description'] = myVMDict['name'][0:99]
            if not startvms:
                myVMDict['start'] = "no"
            myVMDict['name'] = myVMDict['name'][0:36] #limit name length
            print "VM name: %s. Description: %s" % (myVMDict['name'], myVMDict['name'])
            
            #create image at vim in case it not exist
            res, image_dict = mydb.get_table_by_uuid_name("images", vm['image_id'])
            if res<0:
                print "start_scenario error getting image", image_dict
                return res, image_dict
            res, image_id = create_or_use_image(mydb, vims, image_dict, [], True)                
            if res < 0:
                print "start_scenario error adding image to VIM", image_dict
                return res, image_id
            vm['vim_image_id'] = image_id
                
            #create flavor at vim in case it not exist
            res, flavor_dict = mydb.get_table_by_uuid_name("flavors", vm['flavor_id'])
            if res<0:
                print "start_scenario error getting flavor", flavor_dict
                return res, flavor_dict
            if flavor_dict['extended']!=None:
                flavor_dict['extended']= json.loads(flavor_dict['extended'])
            res, flavor_id = create_or_use_flavor(mydb, vims, flavor_dict, [], True)                
            if res < 0:
                print "start_scenario error adding flavor to VIM", flavor_dict
                return res, flavor_id
            vm['vim_flavor_id'] = flavor_id

            
            myVMDict['imageRef'] = vm['vim_image_id']
            myVMDict['flavorRef'] = vm['vim_flavor_id']
            myVMDict['networks'] = []
            for iface in vm['interfaces']:
                netDict = {}
                #discover type of interface looking at flavor
                #TODO in future, move this information to database interfaces table
                for numa in flavor_dict.get('extended',{}).get('numas',[]):
                    for flavor_iface in numa.get('interfaces',[]):
                        if flavor_iface.get('name') == iface['internal_name']:
                            if flavor_iface['dedicated'] == 'yes':
                                netDict['type']="PF"    #passthrough
                            elif flavor_iface['dedicated'] == 'no':
                                netDict['type']="VF"    #siov
                            elif flavor_iface['dedicated'] == 'yes-sriov':
                                netDict['type']="VF not shared"   #sriov but only one sriov on the PF
                            netDict["mac_address"] = flavor_iface.get("mac_address")
                            break;
                netDict["use"]=iface['type']
                if netDict["use"]=="data" and not "type" in netDict:
                    e_text = "Cannot determine the interface type PF or VF of VNF '%s' VM '%s' iface '%s'" %(sce_vnf['name'], vm['name'], iface['internal_name'])
                    if flavor_dict.get('extended')==None:
                        return -HTTP_Conflict, e_text + "After database migration some information is not available. \
                                Try to delete and create the scenarios and VNFs again"
                    else:
                        return -HTTP_Internal_Server_Error, e_text
                if netDict["use"]=="mgmt" or netDict["use"]=="bridge":
                    netDict["type"]="virtual"
                if "vpci" in iface and iface["vpci"] is not None:
                    netDict['vpci'] = iface['vpci']
                netDict['name'] = iface['internal_name']
                if "model" in iface and iface["model"]!=None:
                    netDict['model']=iface['model']
                if iface['net_id'] is None:
                    for vnf_iface in sce_vnf["interfaces"]:
                        print iface
                        print vnf_iface
                        if vnf_iface['interface_id']==iface['uuid']:
                            netDict['net_id'] = auxNetDict['scenario'][ vnf_iface['sce_net_id'] ]
                            break
                else:
                    netDict['net_id'] = auxNetDict[ sce_vnf['uuid'] ][ iface['net_id'] ]
                #skip bridge ifaces not connected to any net
                #if 'net_id' not in netDict or netDict['net_id']==None:
                #    continue
                myVMDict['networks'].append(netDict)
            print ">>>>>>>>>>>>>>>>>>>>>>>>>>>"
            print myVMDict['name']
            print "networks", json.dumps(myVMDict['networks'], indent=4)
            print "interfaces", json.dumps(vm['interfaces'], indent=4)
            print ">>>>>>>>>>>>>>>>>>>>>>>>>>>"
            result, vm_id = myvim.new_tenant_vminstance(myVMDict['name'],myVMDict['description'],myVMDict.get('start', None),
                    myVMDict['imageRef'],myVMDict['flavorRef'],myVMDict['networks'])
            if result < 0:
                error_text = "Error creating vm instance: %s." % vm_id
                _, message = rollback(mydb, vims, rollbackList)
                error_text += message
                print "start_scenario: " + error_text
                return result, error_text
            print "VIM vm instance id (server id) for scenario %s: %s" % (scenarioDict['name'],vm_id)
            vm['vim_id'] = vm_id
            rollbackList.append({'what':'vm','where':'vim','vim_id':datacenter_id,'uuid':vm_id})
            #put interface uuid back to scenario[vnfs][vms[[interfaces]
            for net in myVMDict['networks']:
                if "vim_id" in net:
                    for iface in vm['interfaces']:
                        if net["name"]==iface["internal_name"]:
                            iface["vim_id"]=net["vim_id"]
                            break
    
    print "==================Deployment done=========="
    scenarioDict['vim_tenants_uuid'] = vim_tenants_uuid
    print json.dumps(scenarioDict, indent=4)
    #r,c = mydb.new_instance_scenario_as_a_whole(nfvo_tenant,scenarioDict['name'],scenarioDict)
    result,c = mydb.new_instance_scenario_as_a_whole(nfvo_tenant,instance_scenario_name, instance_scenario_description, scenarioDict)
    if result <0:
        error_text = c + "." 
        _, message = rollback(mydb, vims, rollbackList)
        error_text += message
        print "start_scenario: " + error_text
        return result, error_text
        
    return mydb.get_instance_scenario(c)

def delete_instance(mydb,nfvo_tenant,instance_id):
    print "Checking that the instance_id exists and getting the instance dictionary"
    result, instanceDict = mydb.get_instance_scenario(instance_id, nfvo_tenant)
    if result < 0:
        print "nfvo.delete_instance() error. Error getting info from database"
        return result, instanceDict
    elif result == 0:
        print "delete_instance error. Instance not found"
        return result, instanceDict
    print json.dumps(instanceDict, indent=4)
    
    print "Checking that nfvo_tenant_id exists and getting the VIM URI and the VIM tenant_id"
    result, vims = get_vim(mydb, nfvo_tenant, instanceDict['datacenter_id'])
    if result < 0:
        print "nfvo.delete_instance() error. Datacenter not found"
        return result, vims
    myvim = vims.values()[0]
    
    
    #1. Delete from Database

    #result,c = mydb.delete_row('instance_scenarios', instance_id, nfvo_tenant)
    result,c = mydb.delete_instance_scenario(instance_id, nfvo_tenant)
    if result<0:
        return result, c

    #2. delete from VIM
    error_msg = ""

    #2.1 deleting VMs
    #vm_fail_list=[]
    for sce_vnf in instanceDict['vnfs']:
        for vm in sce_vnf['vms']:
            result, vm_id = myvim.delete_tenant_vminstance(vm['vim_vm_id'])
            if result < 0:
                error_msg+="\n    Error: " + str(-result) + " VM id=" + vm['vim_vm_id']
                #if result != -HTTP_Not_Found: vm_fail_list.append(vm)
                print "Error " + str(-result) + " deleting VM instance '" + vm['name'] + "', uuid '" + vm['uuid'] + "', VIM id '" + vm['vim_vm_id'] + "', from VNF_id '" + sce_vnf['vnf_id'] + "':"  + vm_id
    
    #2.2 deleting NETS
    #net_fail_list=[]
    for net in instanceDict['nets']:
        if net['external']:
            continue #skip not created nets
        result, net_id = myvim.delete_tenant_network(net['vim_net_id'])
        if result < 0:
            error_msg += "\n    Error: " + str(-result) + " NET id=" + net['vim_net_id']
            #if result == -HTTP_Not_Found: net_fail_list.append(net)
            print "Error " + str(-result) + " deleting NET uuid '" + net['uuid'] + "', VIM id '" + net['vim_net_id'] + "':"  + net_id

    if len(error_msg)>0:
        return 1, 'instance ' + instance_id + ' deleted but some elements could not be deleted, or already deleted (error: 404) from VIM: ' + error_msg
    else:
        return 1, 'instance ' + instance_id + ' deleted'

def refresh_instance(mydb, nfvo_tenant, instanceDict, datacenter=None, vim_tenant=None):
    '''Refreshes a scenario instance. It modifies instanceDict'''
    '''Returns:
         - result: <0 if there is any unexpected error, n>=0 if no errors where n is the number of vms and nets that couldn't be updated in the database
         - error_msg
    '''
    # Assumption: nfvo_tenant and instance_id were checked before entering into this function
    print "nfvo.refresh_instance begins"
    #print json.dumps(instanceDict, indent=4)
    
    print "Getting the VIM URL and the VIM tenant_id"
    result, vims = get_vim(mydb, nfvo_tenant, instanceDict['datacenter_id'])
    if result < 0:
        print "nfvo.refresh_instance() error. Datacenter not found"
        return result, vims
    myvim = vims.values()[0]
     
    # 1. Getting the status of all VMs
    vmDict = {}
    netDict = {}
    for sce_vnf in instanceDict['vnfs']:
        for vm in sce_vnf['vms']:
            vmDict[vm['vim_vm_id']]=vm['status']
    
    # 2. Getting the status of all nets
    # TODO: update nets inside a vnf
    for net in instanceDict['nets']:
        #if net['external']:
        #    continue #skip not created nets
        netDict[net['vim_net_id']]=net['status']
 
    # 3. Refresh the status of VMs and nets from VIM. IT updates vmDict and netDict
    result, refresh_message = myvim.refresh_tenant_vms_and_nets(vmDict, netDict)
    if result < 0:
        return result, refresh_message
    
    # 4. Update the status of VMs in the instanceDict, while collects the VMs whose status changed     
    vms_updated = {} #Dictionary of VM instance uuids in openmano that were updated
    for sce_vnf in instanceDict['vnfs']:
        for vm in sce_vnf['vms']:
            status = vmDict[vm['vim_vm_id']]
            if vm['status']!=status:
                vm['status']=status
                vms_updated[vm['uuid']]=status
    
    # 5. Update the status of nets in the instanceDict, while collects the nets whose status changed     
    nets_updated = {} #Dictionary of net instance uuids in openmano that were updated
    # TODO: update nets inside a vnf  
    for net in instanceDict['nets']:
        #if net['external']:
        #    continue #skip not created nets
        status = netDict[net['vim_net_id']]
        if net['status']!=status:
            net['status']=status
            nets_updated[net['uuid']]=status

    # 6. Update in openmano DB the VMs whose status changed
    vms_notupdated=[]
    for vm in vms_updated:
        result2, _ = mydb.update_rows('instance_vms', UPDATE={'status':vms_updated[vm]}, 
                                WHERE={'uuid':vm})
        if result2<0:
            vms_updated.pop(vm)
            vms_notupdated.append(vm)
        elif result2==0:
            print "WARNING: status of vm instance %s should have been updated to %s" %(vm,vms_updated[vm])

    # 7. Update in openmano DB the nets whose status changed
    nets_notupdated=[]
    for net in nets_updated:
        result2, _ = mydb.update_rows('instance_nets', UPDATE={'status':nets_updated[net]}, 
                                WHERE={'uuid':net})
        if result2<0:
            nets_updated.pop(net)
            nets_notupdated.append(net)
        elif result2==0:
            print "WARNING: status of net instance %s should have been updated to %s" %(net,nets_updated[net])
            
    # Returns appropriate output
    print "nfvo.refresh_instance finishes"
    print "VMs updated in the database: %s; nets updated in the database %s; VMs not updated: %s; nets not updated: %s" \
                % (str(vms_updated), str(nets_updated), str(vms_notupdated), str(nets_notupdated)) 
    instance_id = instanceDict['uuid']
    error_msg=refresh_message
    if len(vms_notupdated)+len(nets_notupdated)>0:
        if len(refresh_message)>0:
            error_msg += "; "
        error_msg += "VMs not updated: " + str(vms_notupdated) + "; nets not updated: " + str(nets_notupdated)
        return len(vms_notupdated)+len(nets_notupdated), 'Scenario instance ' + instance_id + ' refreshed but some elements could not be updated in the database: ' + error_msg
    
    return 0, 'Scenario instance ' + instance_id + ' refreshed. ' + error_msg

def instance_action(mydb,nfvo_tenant,instance_id, action_dict):
    print "Checking that the instance_id exists and getting the instance dictionary"
    result, instanceDict = mydb.get_instance_scenario(instance_id, nfvo_tenant)
    if result < 0:
        print "nfvo.instance_action() error. Error getting info from database"
        return result, instanceDict
    elif result == 0:
        print "instance_action error. Instance not found"
        return -HTTP_Not_Found, "instance %s not found" % instance_id
    #print json.dumps(instanceDict, indent=4)

    print "Checking that nfvo_tenant_id exists and getting the VIM URI and the VIM tenant_id"
    result, vims = get_vim(mydb, nfvo_tenant, instanceDict['datacenter_id'])
    if result < 0:
        print "nfvo.instance_action() error. Datacenter not found"
        return result, vims
    myvim = vims.values()[0]
    

    input_vnfs = action_dict.pop("vnfs", [])
    input_vms = action_dict.pop("vms", [])
    action_over_all = True if len(input_vnfs)==0 and len (input_vms)==0 else False
    vm_result = {}
    vm_error = 0
    vm_ok = 0
    for sce_vnf in instanceDict['vnfs']:
        for vm in sce_vnf['vms']:
            if not action_over_all:
                if sce_vnf['uuid'] not in input_vnfs and vm['uuid'] not in input_vms:
                    continue
            result, vm_id = myvim.action_tenant_vminstance(vm['vim_vm_id'],action_dict)
            if vm_result < 0:
                vm_result[ vm['uuid'] ] = {"vim_result": -result, "description": vm_id}
                vm_error+=1
            else:
                vm_result[ vm['uuid'] ] = {"vim_result": result, "description": "ok", "name":vm['name']}
                vm_ok +=1

    if vm_ok==0: #all goes wrong
        return 1, vm_result
    else:
        return 1, vm_result

def check_tenant(mydb, tenant_id):
    '''check that tenant exists at database'''
    result, _ = mydb.get_table(FROM='nfvo_tenants', SELECT=('uuid',), WHERE={'uuid': tenant_id})
    if result<=0: return False
    return True

def new_tenant(mydb, tenant_dict):
    result, tenant_id = mydb.new_row("nfvo_tenants", tenant_dict, None, add_uuid=True, log=True)
    if result < 0:
        return result, tenant_id
    return 200,tenant_id

def delete_tenant(mydb, tenant):
    #get nfvo_tenant info
    result,tenant_dict = mydb.get_table_by_uuid_name('nfvo_tenants', tenant, 'tenant')
    if result < 0:
        return result, tenant_dict

    result, tenant_id = mydb.delete_row("nfvo_tenants", tenant_dict['uuid'], None)
    if result < 0:
        return result, tenant_id
    return 200, tenant_dict['uuid']

def new_datacenter(mydb, datacenter_descriptor):
    if "config" in datacenter_descriptor:
        datacenter_descriptor["config"]=json.dumps(datacenter_descriptor["config"])
    result, datacenter_id = mydb.new_row("datacenters", datacenter_descriptor, None, add_uuid=True, log=True)
    if result < 0:
        return result, datacenter_id
    return 200,datacenter_id

def edit_datacenter(mydb, datacenter_id, datacenter_descriptor):
    #obtain data, check that only one exist
    result, content = mydb.get_table_by_uuid_name('datacenters', datacenter_id)
    if result < 0:
        return result, content
    #edit data 
    datacenter_id = content['uuid']
    where={'uuid': content['uuid']}
    if "config" in datacenter_descriptor:
        if datacenter_descriptor['config']!=None:
            try:
                new_config_dict = json.dumps(datacenter_descriptor["config"])
                config_dict = json.dumps(content["config"])
                config_dict.update(new_config_dict)
                #delete null fields
                for k in config_dict:
                    if config_dict[k]==None:
                        del config_dict[k]
            except Exception,e:
                return -HTTP_Bad_Request, "Bad format at datacenter:config " + str(e)
        datacenter_descriptor["config"]= json.dumps(config_dict) if len(config_dict)>0 else None
    result, content = mydb.update_rows('datacenters', datacenter_descriptor, where)

    result, content = mydb.new_row("datacenters", datacenter_descriptor, None, add_uuid=True, log=True)
    if result < 0:
        return result, datacenter_id
    return 200, datacenter_id

def delete_datacenter(mydb, datacenter):
    #get nfvo_tenant info
    result,datacenter_dict = mydb.get_table_by_uuid_name('datacenters', datacenter, 'datacenter')
    if result < 0:
        return result, datacenter_dict

    result, datacenter_id = mydb.delete_row("datacenters", datacenter_dict['uuid'], None)
    if result < 0:
        return result, datacenter_id
    return 200, datacenter_dict['uuid']

def associate_datacenter_to_tenant(mydb, nfvo_tenant, datacenter, vim_tenant_id=None, vim_tenant_name=None, vim_username=None, vim_password=None):
    #get datacenter info
    if af.check_valid_uuid(datacenter): 
        result, vims = get_vim(mydb, datacenter_id=datacenter)
    else:
        result, vims = get_vim(mydb, datacenter_name=datacenter)
    if result < 0:
        print "nfvo.associate_datacenter_to_tenant() error. Datacenter not found"
        return result, vims
    elif result>1:
        print "nfvo.associate_datacenter_to_tenant() error. Several datacenters found"
        #print result, vims
        return -HTTP_Conflict, "More than one datacenters found, try to identify with uuid"
    datacenter_id=vims.keys()[0]
    myvim=vims[datacenter_id]
    datacenter_name=myvim["name"]

    #get nfvo_tenant info
    result,tenant_dict = mydb.get_table_by_uuid_name('nfvo_tenants', nfvo_tenant)
    if result < 0:
        return result, tenant_dict
    if vim_tenant_name==None:
        vim_tenant_name=tenant_dict['name']
        
    #check that this association does not exist before
    tenants_datacenter_dict={"nfvo_tenant_id":tenant_dict['uuid'], "datacenter_id":datacenter_id }
    result,content = mydb.get_table(FROM='tenants_datacenters', WHERE=tenants_datacenter_dict)
    if result>0:
        return -HTTP_Conflict, "datacenter %s and tenant %s are already attached" %(datacenter_id, tenant_dict['uuid'])
    elif result<0:
        return result, content

    vim_tenant_id_exist_atdb=False
    if vim_tenant_id!=None or vim_tenant_name!=None:
        where_={"datacenter_id": datacenter_id}
        if vim_tenant_id!=None:
            where_["vim_tenant_id"] = vim_tenant_id
        if vim_tenant_name!=None:
            where_["vim_tenant_name"] = vim_tenant_name
        #check if vim_tenant_id is already at database
        result,vim_tenants_dict = mydb.get_table(FROM='vim_tenants', WHERE=where_)
        if result < 0:
            return result, vim_tenants_dict
        elif result>=1:
            vim_tenants_dict = vim_tenants_dict[0]
            vim_tenant_id_exist_atdb=True
            #TODO check if a field has changed and edit entry at vim_tenants at DB
        else: #result=0
            vim_tenants_dict = {}
            #insert at table vim_tenants
    else: #if vim_tenant_id==None:
        #create tenant at VIM if not provided
        res, vim_tenant_id = myvim.new_tenant(vim_tenant_name, "created by openmano for datacenter "+datacenter_name)
        if res < 0:
            return res, "Not possible to create vim_tenant in VIM " + vim_tenant_id
        vim_tenants_dict = {}
        vim_tenants_dict["created"]="true"
    
    #fill vim_tenants table
    if not vim_tenant_id_exist_atdb:
        vim_tenants_dict["vim_tenant_id"]   = vim_tenant_id
        vim_tenants_dict["vim_tenant_name"] = vim_tenant_name
        vim_tenants_dict["user"]            = vim_username
        vim_tenants_dict["passwd"]          = vim_password
        vim_tenants_dict["datacenter_id"]   = datacenter_id
        res,id_ = mydb.new_row('vim_tenants', vim_tenants_dict, tenant_dict['uuid'], True, True)
        if res<1:
            return -HTTP_Bad_Request, "Not possible to add %s to database vim_tenants table %s " %(vim_tenant_id, id_)
        vim_tenants_dict["uuid"] = id_
    
    #fill tenants_datacenters table
    tenants_datacenter_dict["vim_tenant_id"]=vim_tenants_dict["uuid"]
    res,id_ = mydb.new_row('tenants_datacenters', tenants_datacenter_dict, tenant_dict['uuid'], False, True)
    if res<1:
        return -HTTP_Bad_Request, "Not possible to create vim_tenant at database " + id_
    return 200, datacenter_id

def deassociate_datacenter_to_tenant(mydb, nfvo_tenant, datacenter, vim_tenant_id=None):
    #get datacenter info
    if af.check_valid_uuid(datacenter): 
        result, vims = get_vim(mydb, datacenter_id=datacenter)
    else:
        result, vims = get_vim(mydb, datacenter_name=datacenter)
    if result < 0:
        print "nfvo.associate_datacenter_to_tenant() error. Datacenter not found"
        return result, vims
    elif result>1:
        print "nfvo.associate_datacenter_to_tenant() error. Several datacenters found"
        return -HTTP_Conflict, "More than one datacenters found, try to identify with uuid"
    datacenter_id=vims.keys()[0]
    myvim=vims[datacenter_id]

    #get nfvo_tenant info
    result,tenant_dict = mydb.get_table_by_uuid_name('nfvo_tenants', nfvo_tenant)
    if result < 0:
        return result, tenant_dict

    #check that this association exist before
    tenants_datacenter_dict={"nfvo_tenant_id":tenant_dict['uuid'], "datacenter_id":datacenter_id }
    result,tenant_datacenter_list = mydb.get_table(FROM='tenants_datacenters', WHERE=tenants_datacenter_dict)
    if result==0:
        return -HTTP_Not_Found, "datacenter %s and tenant %s are not  attached" %(datacenter_id, tenant_dict['uuid'])
    elif result<0:
        return result, tenant_datacenter_list

    #delete this association
    result,data = mydb.delete_row_by_dict(FROM='tenants_datacenters', WHERE=tenants_datacenter_dict)
    if result<0:
        return result,data

    #get vim_tenant info and deletes
    warning=''
    result,vim_tenant_dict = mydb.get_table_by_uuid_name('vim_tenants', tenant_datacenter_list[0]['vim_tenant_id'])
    if result > 0:
        #try to delete vim:tenant
        result,data = mydb.delete_row('vim_tenants', tenant_datacenter_list[0]['vim_tenant_id'], tenant_dict['uuid'])
        if result<0:
            pass #the error will be caused because dependencies, vim_tenant can not be deleted
        elif vim_tenant_dict['created']=='true':
            #delete tenant at VIM if created by NFVO
            res, vim_tenant_id = myvim.delete_tenant(vim_tenant_dict['vim_tenant_id'])
            if res < 0:
                warning = " Not possible to delete vim_tenant %s from VIM: %s " % (vim_tenant_dict['vim_tenant_id'], vim_tenant_id)
                print res, warning

    return 200, "datacenter %s detached.%s" %(datacenter_id, warning)

def datacenter_action(mydb, tenant_id, datacenter, action_dict):
    #get datacenter info
    if af.check_valid_uuid(datacenter): 
        result, vims = get_vim(mydb, nfvo_tenant=tenant_id, datacenter_id=datacenter)
    else:
        result, vims = get_vim(mydb, nfvo_tenant=tenant_id, datacenter_name=datacenter)
    if result < 0:
        print "nfvo.associate_datacenter_to_tenant() error. Datacenter not found"
        return result, vims
    elif result>1:
        print "nfvo.associate_datacenter_to_tenant() error. Several datacenters found"
        return -HTTP_Conflict, "More than one datacenters found, try to identify with uuid"
    datacenter_id=vims.keys()[0]
    myvim=vims[datacenter_id]

    if 'net-update' in action_dict:
        result, content = myvim.get_network_list(filter_dict={'shared': True, 'admin_state_up': True, 'status': 'ACTIVE'})
        print content
        if result < 0:
            print " Not possible to get_network_list from VIM: %s " % (content)
            return -HTTP_Internal_Server_Error, content
        #update nets Change from VIM format to NFVO format
        net_list=[]
        for net in content:
            net_nfvo={'datacenter_id': datacenter_id}
            net_nfvo['name']       = net['name']
            #net_nfvo['description']= net['name']
            net_nfvo['vim_net_id'] = net['id']
            net_nfvo['type']       = net['type'][0:6] #change from ('ptp','data','bridge_data','bridge_man')  to ('bridge','data','ptp')
            net_nfvo['shared']     = net['shared']
            net_nfvo['multipoint'] = False if net['type']=='ptp' else True
            net_list.append(net_nfvo)
        result, content = mydb.update_datacenter_nets(datacenter_id, net_list)
        if result < 0:
            return -HTTP_Internal_Server_Error, content
        print "Inserted %d nets, deleted %d old nets" % (result, content)
                
        return 200, result
    elif 'net-edit' in action_dict:
        net = action_dict['net-edit'].pop('net')
        what = 'vim_net_id' if af.check_valid_uuid(net) else 'name'
        result, content = mydb.update_rows('datacenter_nets', action_dict['net-edit'], 
                                WHERE={'datacenter_id':datacenter_id, what: net})
        return result, content
    elif 'net-delete' in action_dict:
        net = action_dict['net-delete'].get('net')
        what = 'vim_net_id' if af.check_valid_uuid(net) else 'name'
        result, content = mydb.delete_row_by_dict(FROM='datacenter_nets', 
                                WHERE={'datacenter_id':datacenter_id, what: net})
        return result, content
    else:
        return -HTTP_Bad_Request, "Unknown action " + str(action_dict)
    


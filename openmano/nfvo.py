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
import json
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
    result, content = mydb.get_table(FROM='vms',SELECT=('vim_flavor_id',),WHERE=WHERE_dict )
    if result < 0:
        print "nfvo.get_flavorlist error %d %s" % (result, content)
        return -result, content
    print "get_flavor_list result:", result
    print "get_flavor_list content:", content
    flavorList=[]
    for flavor in content:
        flavorList.append(flavor['vim_flavor_id'])
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
    result, content = mydb.get_table(FROM='vms',SELECT=('vim_image_id',),WHERE=WHERE_dict )
    if result < 0:
        print "nfvo.get_imagelist error %d %s" % (result, content)
        return -result, content
    print "get_image_list result:", result
    print "get_image_list content:", content
    imageList=[]
    for flavor in content:
        imageList.append(flavor['vim_image_id'])
    return result, imageList

def get_vim(mydb, nfvo_tenant=None, datacenter_id=None, datacenter_name=None, vim_tenant=None):
    '''Obtain VIM or datacenter details with some of the input paremeters
    return result, content:
        <0, error_text upon error
        1, dictionary on success, with keys: nfvo_tenant_id','datacenter_id','vim_tenant_id','vim_url','vim_url_admin','datacenter_name'
    '''
    WHERE_dict={}
    if nfvo_tenant     is not None:  WHERE_dict['nfvo_tenant_id'] = nfvo_tenant
    if datacenter_id   is not None:  WHERE_dict['datacenter_id']  = datacenter_id
    if datacenter_name is not None:  WHERE_dict['datacenter.name']  = datacenter_name
    if vim_tenant      is not None:  WHERE_dict['vim.vim_tenant_id']  = vim_tenant
    
    result, content = mydb.get_table(FROM='tenants_datacenters as td join datacenters as datacenter on td.datacenter_id = datacenter.uuid '\
                                    'join vim_tenants as vim on td.vim_tenant_id = vim.uuid',\
                                    SELECT=('vim.uuid as vim_tenants_uuid','nfvo_tenant_id','datacenter_id','vim.vim_tenant_id', \
                                            'vim_url', 'vim_url_admin','datacenter.name as datacenter_name'),\
                                    WHERE=WHERE_dict )
    if result < 0:
        print "nfvo.get_vim error %d %s" % (result, content)
        return -result, content
    elif result==0:
        print "nfvo.get_vim not found a valid VIM with the input params " + str(WHERE_dict)
        return -HTTP_Unauthorized, "datacenter not found for " +  json.dumps(WHERE_dict)
    elif result>1:
        print "nfvo.get_vim more than one datacenter matches with the input params " + str(WHERE_dict)
        return -HTTP_Unauthorized, "more than one datacenter matches for" +  json.dumps(WHERE_dict)
        #Take the datacenter_id and the vim_tenant_id
    print content
    return 1, content[0]

def rollbackNewVNF(vim, myvimURL, myvim_tenant, flavorList, imageList=[], vnf_id=None, nfvodb=None, vmDict=None, netList=None, interfaceList=None):
    '''Do a rollback when adding a new VNF in the catalogue'''
    undeletedFlavors = []
    undeletedImages = []
    for flavor in flavorList:
        result, message = vim.delete_tenant_flavor(myvimURL, myvim_tenant, flavor)
        if result < 0:
            print 'Error in rollback. Not possible to delete VIM flavor "%s". Message: %s' % (flavor,message)
            undeletedFlavors.append(flavor)
        
    for image in imageList:
        result, message = vim.delete_tenant_image(myvimURL, myvim_tenant, image)
        if result < 0:
            print 'Error in rollback. Not possible to delete VIM image "%s". Message: %s' % (image,message)
            undeletedFlavors.append(flavor)
    
#     for net in netList
#         result, message = delete_row(self, table, uuid):
#     print "Lista de flavors no borrados:",undeletedFlavors
#     print "Lista de images no borrados:",undeletedImages
#     #If lists are empty, return true
    if not undeletedFlavors or not undeletedImages: 
        return True,None
    else:
        return False,"Undeleted flavors: %s. Undeleted images: %s" %(undeletedFlavors,undeletedImages)
    
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

def new_image_at_vim(myvimURL, myvim, myvim_tenant, path, metadata, name, description):
    '''
    Create a new image in the VIM (if it didn't exist previously), otherwise, use the existing one
    Returns the number of new images created (0 or 1) and the image-id:
        0,image-id        if the image existed
        1,image-id        if the image didn't exist previously and has been created
        <0,message        if there was an error
    '''
    myImageDict = {}
    myImageDict["image"] = {}
    myImageDict["image"]["name"] = name
    myImageDict["image"]["description"] = description
    myImageDict["image"]["path"] = path
    if metadata != None:
        myImageDict["image"]["metadata"] = metadata
    #print myImageDict

    res, image_id = myvim.get_image_id_from_path(myvimURL, myvim_tenant, path)
    if res < 0 or res > 1:
        return res, "Error contacting VIM to know if the image %s existed previously." %image_id
    elif res==0: # No images existed with that path
        #Create the image in VIM
        result, image_id = myvim.new_tenant_image(myvimURL, myvim_tenant, json.dumps(myImageDict))
        if result < 0:
            return result, "Error creating image: %s." %image_id
        return 1, image_id
    else: #res==1. Nothing to be created. Return the image_id
        return 0, image_id

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
    result, content = get_vim(mydb, nfvo_tenant, datacenter, None, vim_tenant)
    if result < 0:
        print "nfvo.new_vnf() error. Datacenter not found"
        return result, content
    myvimURL =  content['vim_url']
    myvim_tenant = content['vim_tenant_id']

    # Step 3. Creates a connector to talk to the VIM
    myvim = vimconnector.vimconnector()
    
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
    flavorList = []   # It will contain the new flavors created in VIM. It is used for rollback  
    imageList = []    # It will contain the new images created in VIM. It is used for rollback

    try:
        print "Creating additional disk images and new flavors in the VIM for each VNFC"
        for vnfc in vnf_descriptor['vnf']['VNFC']:
            VNFCitem={}
            VNFCitem["name"] = vnfc['name']
            VNFCitem["description"] = vnfc.get("description", 'VM %s of the VNF %s' %(vnfc['name'],vnf_name))
            
            print "Flavor name: %s. Description: %s" % (VNFCitem["name"]+"-flv", VNFCitem["description"])
            
            myflavorDict = {}
            myflavorDict["flavor"] = {}
            myflavorDict["flavor"]["name"] = vnfc['name']+"-flv"
            myflavorDict["flavor"]["description"] = VNFCitem["description"]
            myflavorDict["flavor"]["ram"] = vnfc.get("ram", 0)
            myflavorDict["flavor"]["vcpus"] = vnfc.get("vcpus", 0)
            myflavorDict["flavor"]["extended"] = {}
            
            devices = vnfc.get("devices", [])
            if len(devices)>0:
                myflavorDict["flavor"]["extended"]["devices"] = []
                dev_nb=0 
            for device in devices:
                dev = {}
                dev.update(device)
                
                if "image" in dev:
                    # Step 6.1 Additional disk images are created in the VIM 
                    res, image_id =  new_image_at_vim(myvimURL, myvim, myvim_tenant, dev['image'], 
                                                      dev.get('image metadata', None), vnfc['name']+str(dev_nb)+"-img", 
                                                      VNFCitem['description'])
                    if res < 0 or res > 1:
                        result2, message = rollbackNewVNF(myvim, myvimURL, myvim_tenant, flavorList, imageList)
                        if result2:
                            return res, image_id + " Rollback successful."
                        else:
                            return res, image_id + " Rollback fail: you need to access VIM and delete manually: %s" % message
                    elif res==1:
                        imageList.append(image_id)
                    print "Additional disk image id for VNFC %s: %s" % (vnfc['name'],image_id)
                    
                    dev["imageRef"]=image_id
                    del dev['image']
                    
                if "image metadata" in dev:
                    del dev["image metadata"]
                myflavorDict["flavor"]["extended"]["devices"].append(dev)
                dev_nb += 1
            
            # TODO:
            # Mapping from processor models to rankings should be available somehow in the NFVO. They could be taken from VIM or directly from a new database table
            # Another option is that the processor in the VNF descriptor specifies directly the ranking of the host 
            
            # Previous code has been commented
            #if vnfc['processor']['model'] == "Intel(R) Xeon(R) CPU E5-4620 0 @ 2.20GHz" :
            #    myflavorDict["flavor"]['extended']['processor_ranking'] = 200
            #elif vnfc['processor']['model'] == "Intel(R) Xeon(R) CPU E5-2697 v2 @ 2.70GHz" :
            #    myflavorDict["flavor"]['extended']['processor_ranking'] = 300
            #else:
            #    result2, message = rollbackNewVNF(myvim, myvimURL, myvim_tenant, flavorList, imageList)
            #    if result2:
            #        print "Error creating flavor: unknown processor model. Rollback successful."
            #        return -HTTP_Bad_Request, "Error creating flavor: unknown processor model. Rollback successful."
            #    else:
            #        return -HTTP_Bad_Request, "Error creating flavor: unknown processor model. Rollback fail: you need to access VIM and delete the following %s" % message
            myflavorDict["flavor"]['extended']['processor_ranking'] = 100  #Hardcoded value, while we decide when the mapping is done
     
            if 'numas' in vnfc:
                myflavorDict["flavor"]['extended']['numas'] = vnfc['numas']

            #print myflavorDict
    
            # Step 6.2 New flavors are created in the VIM
            result, flavor_id = myvim.new_tenant_flavor(myvimURL, myvim_tenant, json.dumps(myflavorDict))
            if result < 0:
                result2, message = rollbackNewVNF(myvim, myvimURL, myvim_tenant, flavorList)
                if result2:
                    print "Error creating flavor: %s. Rollback successful." %flavor_id
                    return result, "Error creating flavor: %s. Rollback successful" %flavor_id
                else:
                    return result, "Error creating flavor: %s. Rollback fail: you need to access VIM and delete manually: %s" % (flavor_id, message)
            
            print "Flavor id for VNFC %s: %s" % (vnfc['name'],flavor_id)
            flavorList.append(flavor_id)
            VNFCitem["vim_flavor_id"] = flavor_id
            VNFCDict[vnfc['name']] = VNFCitem
            
        print "Creating new images in the VIM for each VNFC"
        # Step 6.3 New images are created in the VIM
        #For each VNFC, we must create the appropriate image.
        #This "for" loop might be integrated with the previous one 
        #In case this integration is made, the VNFCDict might become a VNFClist.
        for vnfc in vnf_descriptor['vnf']['VNFC']:
            print "Image name: %s. Description: %s" % (vnfc['name']+"-img", VNFCDict[vnfc['name']]['description'])
            
            res, image_id =  new_image_at_vim(myvimURL, myvim, myvim_tenant, vnfc['VNFC image'], 
                                              vnfc.get('image metadata', None), vnfc['name']+"-img", 
                                              VNFCDict[vnfc['name']]['description'])
            if res < 0 or res > 1:
                result2, message = rollbackNewVNF(myvim, myvimURL, myvim_tenant, flavorList, imageList)
                if result2:
                    return res, image_id + " Rollback successful."
                else:
                    return res, image_id + " Rollback fail: you need to access VIM and delete manually: %s" % message
            elif res==1:
                imageList.append(image_id)
            print "Image id for VNFC %s: %s" % (vnfc['name'],image_id)
            VNFCDict[vnfc['name']]["vim_image_id"] = image_id
            VNFCDict[vnfc['name']]["image_path"] = vnfc['VNFC image']

    except KeyError as e:
        print "Error while creating a VNF. KeyError: " + str(e)
        result2, message = rollbackNewVNF(myvim, myvimURL, myvim_tenant, flavorList, imageList)
        if result2:
            return -HTTP_Internal_Server_Error, "Error while creating a VNF. KeyError: " + str(e) + " Rollback successful."
        else:
            return -HTTP_Internal_Server_Error, "Error while creating a VNF. KeyError: " + str(e) + " Rollback fail: you need to access VIM and delete manually: %s" % message
        
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
        result2, message = rollbackNewVNF(myvim, myvimURL, myvim_tenant, flavorList, imageList)
        if result2:
            return -HTTP_Internal_Server_Error, "Error while creating a VNF. KeyError: " + str(e) + " Rollback successful."
        else:
            return -HTTP_Internal_Server_Error, "Error while creating a VNF. KeyError: " + str(e) + " Rollback fail: you need to access VIM and delete manually: %s" % message
    
    if result < 0:
        result2, message = rollbackNewVNF(myvim, myvimURL, myvim_tenant, flavorList, imageList)
        if result2:
            return result, "%s. Rollback successful." %vnf_id
        else:
            return result, "%s. Rollback fail: you need to delete manually: %s" % (vnf_id, message)

    return 200,vnf_id

def delete_vnf(mydb,nfvo_tenant,vnf_id,datacenter=None,vim_tenant=None):
    print "Checking that nfvo_tenant_id exists and getting the VIM URI and the VIM tenant_id"
    result, content = get_vim(mydb, nfvo_tenant, datacenter, None, vim_tenant)
    if result < 0:
        return -HTTP_Unauthorized, "delete_vnf error. No VIM found for tenant '%s'" % nfvo_tenant
    myvimURL =  content['vim_url']
    myvim_tenant = content['vim_tenant_id']

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
    
    myvim = vimconnector.vimconnector()
    undeletedFlavors = []
    undeletedImages = []
    for flavor in flavorList:
        result, message = myvim.delete_tenant_flavor(myvimURL, myvim_tenant, flavor)
        if result < 0:
            print 'delete_vnf_error. Not possible to delete VIM flavor "%s". Message: %s' % (flavor,message)
            undeletedFlavors.append(flavor)
        
    for image in imageList:
        r,c = mydb.get_table(SELECT=('*',), FROM='vms', WHERE={'vim_image_id':image}, WHERENOT={'vnf_id':vnf_id} )
        if r < 0:
            print 'delete_vnf_error. Not possible to delete VIM image "%s". Message: %s' % (image,message)
            undeletedImages.append(image)
        elif r > 0:
            print 'Image %s not deleted because it is being used by another VNF %s' %(image,str(c))
            continue
        result, message = myvim.delete_tenant_image(myvimURL, myvim_tenant, image)
        if result < 0:
            print 'delete_vnf_error. Not possible to delete VIM image "%s". Message: %s' % (image,message)
            undeletedImages.append(image)
    
    if undeletedFlavors or undeletedImages: 
        return 200, "delete_vnf error. Undeleted flavors: %s. Undeleted images: %s" %(undeletedFlavors,undeletedImages)
    
    return 200,vnf_id

def get_hosts_info(mydb, nfvo_tenant_id, datacenter_name=None):
    myvim = vimconnector.vimconnector();
    result, vim_dict = get_vim(mydb, nfvo_tenant_id, None, datacenter_name)
    if result < 0:
        return result, vim_dict
    result,servers =  myvim.get_hosts_info(vim_dict['vim_url'])
    if result < 0:
        return result, servers
    topology = {'name':vim_dict['datacenter_name'] , 'servers': servers}
    return result, topology

def get_hosts(mydb, nfvo_tenant_id):
    myvim = vimconnector.vimconnector();
    result, vim_dict = get_vim(mydb, nfvo_tenant_id)
    if result < 0:
        return result, vim_dict
    result,hosts =  myvim.get_hosts(vim_dict['vim_url'], vim_dict['vim_tenant_id'])
    if result < 0:
        return result, hosts
    print '==================='
    print 'hosts '+ json.dumps(hosts, indent=4)

    datacenter = {'Datacenters': [ {'name':vim_dict['datacenter_name'],'servers':[]} ] }
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

    result, vim_dict = get_vim(mydb, nfvo_tenant_id)
    if result < 0:
        return result, vim_dict
#1: parse input
#1.1: get VNFs and external_ports. 
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
        

#1.2: Check VNF are present at database table vnfs. Insert uuid
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
            print "nfvo.new_scenario Error more than one" + error_text + " is present at database"
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
        conections_list.append(set(ifaces_list)) #from list to set to operate as a set
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
            elif r>1:
                print "nfvo.new_scenario Error more than one external_network for " +error_text+ " is present at database" 
                return -HTTP_Bad_Request, "more than one external_network for " +error_text+ "at "+ error_pos + " Concrete with 'net_id'" 
            other_nets[k].update(net_db[0])
    
    net_list={}
    net_nb=0
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
                    type_='data' if len(con)>1 else 'ptp'  #an external net is connectect to a external port, so it is ptp if only one connection is done to this net
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

#1.5: Connect to management net all not already connected interfaces of type 'mgmt'
    #1.5.1 obtain management net 
    r,mgmt_net = mydb.get_table(SELECT=('uuid','name','description','type','shared'),
        FROM='datacenter_nets', WHERE={'name':'mgmt'} )
    #1.5.2 check all interfaces from all vnfs 
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

def rollbackNewScenario(vim, myvimURL, myvim_tenant, netList, vmList=()):
    '''Do a rollback when launching a scenario'''
    undeletedNets = []
    undeletedVMs = []
    for vm in vmList:
        result, message = vim.delete_tenant_vminstance(myvimURL, myvim_tenant, vm)
        if result < 0:
            print 'Error in rollback. Not possible to delete VIM vm instance "%s". Message: %s' % (vm,message)
            undeletedVMs.append(vm)
    
    for network in netList:
        result, message = vim.delete_tenant_network(myvimURL, myvim_tenant, network)
        if result < 0:
            print 'Error in rollback. Not possible to delete VIM network "%s". Message: %s' % (network,message)
            undeletedNets.append(network)
        
    if not undeletedNets or not undeletedVMs: 
        return True,None
    else:
        return False,"Undeleted nets: %s. Undeleted VMs: %s" %(undeletedNets,undeletedVMs)

def start_scenario(mydb, nfvo_tenant, scenario_id, instance_scenario_name, instance_scenario_description, datacenter=None,vim_tenant=None, startvms=True):
    print "Checking that nfvo_tenant_id exists and getting the VIM URI and the VIM tenant_id"
    datacenter_id = None
    datacenter_name=None
    if datacenter != None:
        if af.check_valid_uuid(datacenter): 
            datacenter_id = datacenter
        else:
            datacenter_name = datacenter
    result, content = get_vim(mydb, nfvo_tenant, datacenter_id, datacenter_name, vim_tenant)
    if result < 0:
        print "start_scenario error. Datacenter not found"
        return result, content
    myvimURL =  content['vim_url']
    myvim_tenant = content['vim_tenant_id']
    datacenter_id = content['datacenter_id']
    vim_tenants_uuid = content['vim_tenants_uuid']

    myvim = vimconnector.vimconnector()
    
    print "Checking that the scenario_id exists and getting the scenario dictionary"
    result, scenarioDict = mydb.get_scenario(scenario_id, nfvo_tenant)
    if result < 0:
        print "start_scenario error. Error interacting with NFVO DB"
        return result, scenarioDict
    elif result == 0:
        print "start_scenario error. Scenario not found"
        return result, scenarioDict

    scenarioDict['vim_tenant_id'] = myvim_tenant
    scenarioDict['datacenter_id'] = datacenter_id
    print '================scenarioDict======================='
    print 'BEGIN launching instance scenario "%s" based on "%s"' % (instance_scenario_name,scenarioDict['name'])

    print "Scenario %s: consisting of %d VNF(s)" % (scenarioDict['name'],len(scenarioDict['vnfs']))
    print json.dumps(scenarioDict, indent=4)
    
    auxNetDict = {}   #Auxiliar dictionary. First key:'scenario' or sce_vnf uuid. Second Key: uuid of the net/sce_net. Value: vim_net_id
    auxNetDict['scenario'] = {}
    
    print "1. Creating new nets (sce_nets) in the VIM"
    #For each sce_net, we create it and we add it to instanceNetlist.
    instanceNetList = []
    for sce_net in scenarioDict['nets']:
        print "Net name: %s. Description: %s" % (sce_net["name"], sce_net["description"])
        
        myNetName = "%s-%s" % (scenarioDict['name'],sce_net['name'])
        myNetName = myNetName[0:36] #limit length
        myNetType = sce_net['type']
        myNetDict = {}
        myNetDict["network"] = {}
        myNetDict["network"]["name"] = myNetName
        myNetDict["network"]["type"] = myNetType
        myNetDict["network"]["tenant_id"] = myvim_tenant
        #TODO:
        #We should use the dictionary as input parameter for new_tenant_network
        print myNetDict
        if not sce_net["external"]:
            result, network_id = myvim.new_tenant_network(myvimURL, myvim_tenant, myNetName, myNetType)
            if result < 0:
                result2, message = rollbackNewScenario(myvim, myvimURL, myvim_tenant, instanceNetList)
                if result2:
                    print "Error creating network: %s. Rollback successful." %network_id
                    return result, "Error creating network: %s. Rollback successful" %network_id
                else:
                    return result, "Error creating network: %s. Rollback fail: you need to access VIM and delete manually: %s" % (network_id, message)

            print "New VIM network created for scenario %s. Network id:  %s" % (scenarioDict['name'],network_id)
            sce_net['vim_id'] = network_id
            auxNetDict['scenario'][sce_net['uuid']] = network_id
            instanceNetList.append(network_id)
        else:
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
            myNetDict["network"] = {}
            myNetDict["network"]["name"] = myNetName
            myNetDict["network"]["type"] = myNetType
            myNetDict["network"]["tenant_id"] = myvim_tenant
            print myNetDict
    
            result, network_id = myvim.new_tenant_network(myvimURL, myvim_tenant, myNetName, myNetType)
            if result < 0:
                result2, message = rollbackNewScenario(myvim, myvimURL, myvim_tenant, instanceNetList)
                if result2:
                    print "Error creating network: %s. Rollback successful." %network_id
                    return result, "Error creating network: %s. Rollback successful" %network_id
                else:
                    return result, "Error creating network: %s. Rollback fail: you need to access VIM and delete manually: %s" % (network_id, message)
            
            print "VIM network id for scenario %s: %s" % (scenarioDict['name'],network_id)
            net['vim_id'] = network_id
            if sce_vnf['uuid'] not in auxNetDict:
                auxNetDict[sce_vnf['uuid']] = {}
            auxNetDict[sce_vnf['uuid']][net['uuid']] = network_id
            instanceNetList.append(network_id)

    print "auxNetDict: %s" %(str(auxNetDict))
    
    print "3. Creating new vm instances in the VIM"
    #For each vm inside an sce_vnf, we create it and we add it to instanceVMlist.
    #myvim.new_tenant_vminstance(self,vimURI,tenant_id,name,description,image_id,flavor_id,net_dict)
    instanceVMList = []
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
            myVMDict['imageRef'] = vm['vim_image_id']
            myVMDict['flavorRef'] = vm['vim_flavor_id']
            myVMDict['networks'] = []
            for iface in vm['interfaces']:
                if iface['type']!="data":
                    netDict = {}
                    if "vpci" in iface: netDict['vpci'] = iface['vpci']
                    netDict['name'] = iface['internal_name']
                    if "model" in iface and iface["model"]!=None:
                        netDict['model']=iface['model']
                    if iface['net_id'] is None:
                        for vnf_iface in sce_vnf["interfaces"]:
                            print iface
                            print vnf_iface
                            if vnf_iface['interface_id']==iface['uuid']:
                                netDict['uuid'] = auxNetDict['scenario'][vnf_iface['sce_net_id']]
                                break
                    else:
                        netDict['uuid'] = auxNetDict[sce_vnf['uuid']][iface['net_id']]
                    #skip bridge ifaces not connected to any net
                    if 'uuid' not in netDict or netDict['uuid']==None:
                        continue
                    myVMDict['networks'].append(netDict)
            print ">>>>>>>>>>>>>>>>>>>>>>>>>>>"
            print json.dumps(myVMDict['networks'], indent=4)
            print ">>>>>>>>>>>>>>>>>>>>>>>>>>>"
            print json.dumps(vm['interfaces'], indent=4)
            print ">>>>>>>>>>>>>>>>>>>>>>>>>>>"
            result, vm_id = myvim.new_tenant_vminstance(myvimURL,myvim_tenant,myVMDict['name'],myVMDict['description'],myVMDict.get('start', None),
                    myVMDict['imageRef'],myVMDict['flavorRef'],myVMDict['networks'],vm['interfaces'])
            
            if result < 0:
                result2, message = rollbackNewScenario(myvim, myvimURL, myvim_tenant, instanceNetList, instanceVMList)
                if result2:
                    print "Error creating vm instance: %s. Rollback successful." %vm_id
                    return result, "Error creating vm instance: %s. Rollback successful" %vm_id
                else:
                    return result, "Error creating vm instance: %s. Rollback fail: you need to access VIM and delete manually: %s" % (vm_id, message)
            
            print "VIM vm instance id (server id) for scenario %s: %s" % (scenarioDict['name'],vm_id)
            vm['vim_id'] = vm_id
            instanceVMList.append(vm_id)
    
    #attach interfaces to nets
    print "4. attach interfaces to nets"
    print json.dumps(scenarioDict, indent=4)
    #create an auxiliare dictionary
    net_nfvo2vim={}
    for sce_vnf in scenarioDict['vnfs']:
        for net in sce_vnf['nets']: 
            net_nfvo2vim[ net['uuid'] ] = net['vim_id']
    for net in scenarioDict['nets']: 
        net_nfvo2vim[ net['uuid'] ] = net['vim_id']

    #attach inter vnf nets
        
    #attach nets
    for sce_vnf in scenarioDict['vnfs']:
        for vm in sce_vnf['vms']: 
            for interface in vm['interfaces']:
                #look for net_id to connect at vnfs[interfaces]
                net_id = interface.get('net_id', None)
                if net_id is None:
                    for external_iface in sce_vnf['interfaces']:
                        if external_iface['interface_id'] == interface['uuid']:
                            net_id = external_iface.get('sce_net_id', None)
                            break
                if net_id is None:
                    continue
                result, port_id = myvim.connect_port_network(myvimURL, interface['vim_id'], net_nfvo2vim[net_id])
                if result < 0:
                    result2, message = rollbackNewScenario(myvim, myvimURL, myvim_tenant, instanceNetList, instanceVMList)
                    if result2:
                        print "Error attaching port to network: %s. Rollback successful." % port_id
                        return result, "Error attaching port to network: %s. Rollback successful" %port_id
                    else:
                        return result, "Error attaching port to network: %s. Rollback fail: you need to access VIM and delete manually: %s" % (port_id, message)
    
    
    print "==================Deployment done=========="
    scenarioDict['vim_tenants_uuid'] = vim_tenants_uuid
    print json.dumps(scenarioDict, indent=4)
    #r,c = mydb.new_instance_scenario_as_a_whole(nfvo_tenant,scenarioDict['name'],scenarioDict)
    r,c = mydb.new_instance_scenario_as_a_whole(nfvo_tenant,instance_scenario_name, instance_scenario_description, scenarioDict)
    if r <0: 
        result2, message = rollbackNewScenario(myvim, myvimURL, myvim_tenant, instanceNetList, instanceVMList)
        if result2: return r, c+". Rollback successful"
        else: return r,c+". Rollback fail: you need to access VIM and delete manually: "+ message
        
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
    result, content = get_vim(mydb, nfvo_tenant, instanceDict['datacenter_id'])
    if result < 0:
        print "nfvo.delete_instance() error. Datacenter not found"
        return result, content
    myvimURL =  content['vim_url']
    myvim_tenant = content['vim_tenant_id']
    myvim = vimconnector.vimconnector()
    
    
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
            result, vm_id = myvim.delete_tenant_vminstance(myvimURL, myvim_tenant, vm['vim_vm_id'])
            if result < 0:
                error_msg+="\n    Error: " + str(-result) + " VM id=" + vm['vim_vm_id']
                #if result != -HTTP_Not_Found: vm_fail_list.append(vm)
                print "Error " + str(-result) + " deleting VM instance '" + vm['name'] + "', uuid '" + vm['uuid'] + "', VIM id '" + vm['vim_vm_id'] + "', from VNF_id '" + sce_vnf['vnf_id'] + "':"  + vm_id
    
    #2.2 deleting NETS
    #net_fail_list=[]
    for net in instanceDict['nets']:
        if net['external']:
            continue #skip not created nets
        result, net_id = myvim.delete_tenant_network(myvimURL, myvim_tenant, net['vim_net_id'])
        if result < 0:
            error_msg += "\n    Error: " + str(-result) + " NET id=" + net['vim_net_id']
            #if result == -HTTP_Not_Found: net_fail_list.append(net)
            print "Error " + str(-result) + " deleting NET uuid '" + net['uuid'] + "', VIM id '" + net['vim_net_id'] + "':"  + net_id

    if len(error_msg)>0: 
        return 1, 'instance ' + instance_id + ' deleted but Some elements could not be deleted, or already deleted (error: 404) from VIM: ' + error_msg
    else:
        return 1, 'instance ' + instance_id + ' deleted'

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
    result, content = get_vim(mydb, nfvo_tenant, instanceDict['datacenter_id'])
    if result < 0:
        print "nfvo.instance_action() error. Datacenter not found"
        return result, content
    myvimURL =  content['vim_url']
    myvim_tenant = content['vim_tenant_id']
    myvim = vimconnector.vimconnector()
    

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
            result, vm_id = myvim.action_tenant_vminstance(myvimURL, myvim_tenant, vm['vim_vm_id'],action_dict)
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
    result, datacenter_id = mydb.new_row("datacenters", datacenter_descriptor, None, add_uuid=True, log=True)
    if result < 0:
        return result, datacenter_id
    return 200,datacenter_id

def delete_datacenter(mydb, datacenter):
    #get nfvo_tenant info
    result,datacenter_dict = mydb.get_table_by_uuid_name('datacenters', datacenter, 'datacenter')
    if result < 0:
        return result, datacenter_dict

    result, datacenter_id = mydb.delete_row("datacenters", datacenter_dict['uuid'], None)
    if result < 0:
        return result, datacenter_id
    return 200, datacenter_dict['uuid']

def associate_datacenter_to_tenant(mydb, nfvo_tenant, datacenter, vim_tenant_id=None, vim_tenant_name=None):
    #get datacenter info
    result,datacenter_dict = mydb.get_table_by_uuid_name('datacenters', datacenter)
    if result < 0:
        return result,datacenter_dict

    #get nfvo_tenant info
    result,tenant_dict = mydb.get_table_by_uuid_name('nfvo_tenants', nfvo_tenant)
    if result < 0:
        return result, tenant_dict
    if vim_tenant_name==None:
        vim_tenant_name=tenant_dict['name']
        
    #check that this association does not exist before
    tenants_datacenter_dict={"nfvo_tenant_id":tenant_dict['uuid'], "datacenter_id":datacenter_dict['uuid'] }
    result,content = mydb.get_table(FROM='tenants_datacenters', WHERE=tenants_datacenter_dict)
    if result>0:
        return -HTTP_Conflict, "datacenter %s and tenant %s are already attached" %(datacenter_dict['uuid'], tenant_dict['uuid'])
    elif result<0:
        return result, content

    vim_tenant_id_exist_atdb=False
    if vim_tenant_id!=None:
        #check if vim_tenant_id is already at database
        result,vim_tenants_dict = mydb.get_table(FROM='vim_tenants', WHERE={"vim_tenant_id": vim_tenant_id})
        if result < 0:
            return result, vim_tenants_dict
        elif result==1:
            vim_tenants_dict = vim_tenants_dict[0]
            vim_tenant_id_exist_atdb=True
        else: #result=0
            vim_tenants_dict = {}
            #insert at table vim_tenants
    else: #if vim_tenant_id==None:
        #create tenant at VIM if not provided
        myvim = vimconnector.vimconnector();
        myVIMURL=datacenter_dict['vim_url']
        res, vim_tenant_id = myvim.new_tenant(myVIMURL, vim_tenant_name, "created by openmano for datacenter "+datacenter_dict["name"])
        if res < 0:
            return res, "Not possible to create vim_tenant in VIM " + vim_tenant_id
        vim_tenants_dict = {}
        vim_tenants_dict["created"]="true"
    
    #fill vim_tenants table
    if not vim_tenant_id_exist_atdb:
        vim_tenants_dict["vim_tenant_id"]=vim_tenant_id
        vim_tenants_dict["name"]=vim_tenant_name
        res,id_ = mydb.new_row('vim_tenants', vim_tenants_dict, tenant_dict['uuid'], True, True)
        if res<1:
            return -HTTP_Bad_Request, "Not possible to add %s to database vim_tenants table %s " %(vim_tenant_id, id_)
        vim_tenants_dict["uuid"] = id_
    
    #fill tenants_datacenters table
    tenants_datacenter_dict["vim_tenant_id"]=vim_tenants_dict["uuid"]
    res,id_ = mydb.new_row('tenants_datacenters', tenants_datacenter_dict, tenant_dict['uuid'], False, True)
    if res<1:
        return -HTTP_Bad_Request, "Not possible to create vim_tenant at database " + id_
    return 200, datacenter_dict['uuid']

def deassociate_datacenter_to_tenant(mydb, nfvo_tenant, datacenter, vim_tenant_id=None):
    #get datacenter info
    result,datacenter_dict = mydb.get_table_by_uuid_name('datacenters', datacenter)
    if result < 0:
        return result,datacenter_dict

    #get nfvo_tenant info
    result,tenant_dict = mydb.get_table_by_uuid_name('nfvo_tenants', nfvo_tenant)
    if result < 0:
        return result, tenant_dict

    #check that this association exist before
    tenants_datacenter_dict={"nfvo_tenant_id":tenant_dict['uuid'], "datacenter_id":datacenter_dict['uuid'] }
    result,tenant_datacenter_list = mydb.get_table(FROM='tenants_datacenters', WHERE=tenants_datacenter_dict)
    if result==0:
        return -HTTP_Not_Found, "datacenter %s and tenant %s are not  attached" %(datacenter_dict['uuid'], tenant_dict['uuid'])
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
            myvim = vimconnector.vimconnector();
            myVIMURL=datacenter_dict['vim_url']
            res, vim_tenant_id = myvim.delete_tenant(myVIMURL, vim_tenant_dict['vim_tenant_id'])
            if res < 0:
                warning = " Not possible to delete vim_tenant %s from VIM: %s " % (vim_tenant_dict['vim_tenant_id'], vim_tenant_id)
                print res, warning

    return 200, "datacenter %s detached.%s" %(datacenter_dict['uuid'], warning)

def datacenter_action(mydb, datacenter, action_dict):
    #get datacenter info
    result,datacenter_dict = mydb.get_table_by_uuid_name('datacenters', datacenter)
    if result < 0:
        return result,datacenter_dict
    datacenter_id = datacenter_dict['uuid']

    if 'net-update' in action_dict:
        myvim = vimconnector.vimconnector();
        myVIMURL=datacenter_dict['vim_url']
        result, content = myvim.get_tenant_network(myVIMURL, None, {'shared': True, 'admin_state_up': True, 'status': 'ACTIVE'})
        print content
        if result < 0:
            print " Not possible to get_tenant_network from VIM: %s " % (content)
            return -HTTP_Internal_Server_Error, content
        #update nets Change from VIM format to NFVO format
        net_list=[]
        for net in content['networks']:
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
    


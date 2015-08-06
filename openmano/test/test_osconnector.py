#!/usr/bin/env python
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
test_osconnector.py makes a test over osconnector.py (openstack connector)
credentiasl must be provided with environment bash variables or arguments
'''
__author__="Alfonso Tierno, Gerardo Garcia"
__date__ ="$22-jun-2014 11:19:29$"


import os
import sys
import getopt
#import yaml
#from jsonschema import validate as js_v, exceptions as js_e

#load osconnector, insert openmano directory in the path
r=sys.argv[0].rfind('/')
if r<0:
    osconnector_path=".."
else:
    osconnector_path=sys.argv[0][:r+1]+".."
sys.path.insert(0, osconnector_path)
#sys.path.insert(0, '/home/atierno/workspace/openmano/openmano')
import osconnector

version="0.1"

def usage():
    print "Usage: ", sys.argv[0], "[options]"
    print "  -v|--version            openstack version (by default 2)"
    print "  -u|--username USER      user to authenticate (by default bash:OS_USERNAME)"
    print "  -p|--password PASSWD    password to authenticate (by default bash:OS_PASSWORD)"
    print "  -U|--auth_url URL       url of authentication over keystone (by default bash:OS_AUTH_URL)"
    print "  -t|--tenant_name TENANT password to authenticate (by default bash:OS_TENANT_NAME)"
    print "  -i|--image IMAGE        use this local path or url for loading image (by default cirros)"
    print "  --skip-admin-tests      skip tests that requires administrative permissions, like create tenants"
    print "  -h|--help               shows this help"
    return

def delete_items():
    global myvim
    global rollback_list
    print "Making rollback, deleting items"
    for i in range(len(rollback_list)-1, -1, -1):
        item,name,id_ = rollback_list[i]
        if item=="creds":
            print ("changing credentials %s='%s'" % (name, id_)).ljust(50),
        else:
            print ("deleting %s '%s'" % (item, name)).ljust(50),
        sys.stdout.flush()
        if item=="flavor":
            result,message=myvim.delete_tenant_flavor(id_)
        elif item=="image":
            result,message=myvim.delete_tenant_image(id_)
        elif item=="tenant":
            result,message=myvim.delete_tenant(id_)
        elif item=="user":
            result,message=myvim.delete_user(id_)
        elif item=="network":
            result,message=myvim.delete_tenant_network(id_)
        elif item=="vm":
            result,message=myvim.delete_tenant_vminstance(id_)
        elif item=="creds":
            try:
                myvim[name]=id_
                result=1
            except Exception, e:
                result=-1
                message= "  " + str(type(e))[6:-1] + ": "+  str(e)
        else:
            print "Internal error unknown item rollback %s,%s,%s" % (item,name,id_)
            continue
        if result<0:
            print " Fail"
            print "  VIM response:", message
            continue
        else:
            print " Ok"

if __name__=="__main__":
    global myvim
    global rollback_list
    #print "(c) Copyright Telefonica"
    rollback_list=[]
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hv:u:U:p:t:i:",
                 ["username=", "help", "version=", "password=", "tenant=", "url=","skip-admin-tests",'image='])
    except getopt.GetoptError, err:
        # print help information and exit:
        print "Error:", err # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
        
    creds = {}
    creds['version'] = os.environ.get('OS_VERSION', '2')
    creds['username'] = os.environ.get('OS_USERNAME')
    creds['password'] = os.environ.get('OS_PASSWORD')
    creds['auth_url'] = os.environ.get('OS_AUTH_URL')
    creds['tenant_name'] = os.environ.get('OS_TENANT_NAME')
    skip_admin_tests=False
    image_path="http://download.cirros-cloud.net/0.3.3/cirros-0.3.3-x86_64-disk.img"
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-v", "--version"):
            creds['version']=a
        elif o in ("-u", "--username"):
            creds['username']=a
        elif o in ("-p", "--password"):
            creds['password']=a
        elif o in ("-U", "--auth_url"):
            creds['auth_url']=a
        elif o in ("-t", "--tenant_name"):
            creds['tenant_name']=a
        elif o in ("-i", "--image"):
            image_path=a
        elif o=="--skip-admin-tests":
            skip_admin_tests=True
        else:
            assert False, "Unhandled option"
 
    if creds['auth_url']==None:
        print "you must provide openstack url with -U or bash OS_AUTH_URL"
        sys.exit()
    print "creds:", creds
    

    try:
        print 'load osconnector class'.ljust(50),
        sys.stdout.flush()
        try:
            myvim=osconnector.osconnector(uuid=None, name='test-openstack', tenant=creds['tenant_name'], 
                url=creds['auth_url'], url_admin=None,
                user=creds['username'], passwd=creds['password'],
                debug = False, config={'network_vlan_ranges':'physnet_sriov'} )
            print " Ok"
        except Exception, e:
            print " Fail"
            print str(type(e))[6:-1] + ": "+  str(e) 
            exit(-1)
        
        if not skip_admin_tests:
            tenant_name="tos-tenant"
            print ("creating new tenant '%s'" % tenant_name).ljust(50),
            sys.stdout.flush()
            result,new_tenant=myvim.new_tenant(tenant_name, "test tenant_description, trying a long description to get the limit. 2 trying a long description to get the limit. 3. trying a long description to get the limit.")
            if result<0:
                print " Fail"
                print "  you can skip tenant creation with param'--skip-admin-tests'"
                print "  VIM response:", new_tenant
                exit(-1)
            else:
                print " Ok", new_tenant
                rollback_list.append(("tenant",tenant_name,new_tenant))

            user_name="tos-user"
            print ("creating new user '%s'" % user_name).ljust(50),
            sys.stdout.flush()
            result,new_user=myvim.new_user(user_name, user_name, tenant_id=new_tenant)
            if result<0:
                print " Fail"
                print "  VIM response:", new_user
                exit(-1)
            else:
                print " Ok", new_user
                rollback_list.append(("user",user_name,new_user))
                    
        name="tos-fl1"
        print ("creating new flavor '%s'"%name).ljust(50),
        sys.stdout.flush()
        flavor={}
        flavor['name']=name
        result,new_flavor1=myvim.new_tenant_flavor(flavor, True)
        if result<0:
            print " Fail"
            print "  VIM response:", new_flavor1
            exit(-1)
        else:
            print " Ok", new_flavor1
            rollback_list.append(("flavor",name,new_flavor1))
            
        name="tos-cirros"
        print ("creating new image '%s'"%name).ljust(50),
        sys.stdout.flush()
        image={}
        image['name']=name
        image['location']=image_path #"/home/atierno/cirros-0.3.3-x86_64-disk.img"
        result,new_image1=myvim.new_tenant_image(image)
        if result<0:
            print " Fail"
            print "  VIM response:", new_image1
            exit(-1)
        else:
            print " Ok", new_image1
            rollback_list.append(("image",name, new_image1))

        if not skip_admin_tests:
            try:
                print 'changing credentials to new tenant'.ljust(50),
                sys.stdout.flush()
                myvim['tenant']  =tenant_name
                myvim['user']=user_name
                myvim['passwd']=user_name
                print " Ok"
                rollback_list.append(("creds", "tenant", creds["tenant_name"]))
                rollback_list.append(("creds", "user",   creds["username"]))
                rollback_list.append(("creds", "passwd", creds["password"]))
            except Exception, e:
                print " Fail"
                print " Error setting osconnector to new tenant:", str(type(e))[6:-1] + ": "+  str(e)
                exit(-1)

        name="tos-net-bridge"
        print ("creating new net '%s'"%name).ljust(50),
        sys.stdout.flush()
        result,new_net1=myvim.new_tenant_network(name, "bridge")
        if result<0:
            print " Fail"
            print "  VIM response:", new_net1
            exit(-1)
        else:
            print " Ok", new_net1
            rollback_list.append(("network",name, new_net1))

        name="tos-vm-cloud"
        print ("creating new VM '%s'"%name).ljust(50),
        sys.stdout.flush()
        result,new_vm1=myvim.new_tenant_vminstance(name, "vm-cloud-description", False,new_image1,new_flavor1,
                                    [{"net_id":new_net1, "type":"virtio"}] )
        if result<0:
            print " Fail"
            print "  VIM response:", new_vm1
            exit(-1)
        else:
            print " Ok", new_vm1
            rollback_list.append(("vm",name, new_vm1))

            
        print 'DONE  Ok'
        print "Type ENTER to delete items"
        raw_input('> ')  
        exit()      
              
    except KeyboardInterrupt:
        print " Canceled!"
    except SystemExit:
        pass
    if len(rollback_list):
        delete_items()


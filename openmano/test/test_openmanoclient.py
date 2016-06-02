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
Module to test openmanoclient class  
'''
__author__="Alfonso Tierno"
__date__ ="$09-Mar-2016 09:09:48$"
__version__="0.0.2"
version_date="May 2016"

import logging
import imp 
        


def _get_random_name(maxLength):
    '''generates a string with random craracters from space (ASCCI 32) to ~(ASCCI 126)
    with a random length up to maxLength
    '''
    long_name = "testing up to {} size name: ".format(maxLength) 
    #long_name += ''.join(chr(random.randint(32,126)) for _ in range(random.randint(20, maxLength-len(long_name))))
    long_name += ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ') for _ in range(20, maxLength-len(long_name)))
    return long_name


if __name__=="__main__":
    import getopt
    #import os
    import sys
    


    usage =\
    """Make a test against an openmano server.\nUsage: test_openmanoclient [options]
    -v|--verbose: prints more info in the test
    --version:    shows current version
    -h|--help:    shows this help
    -d|--debug:   set logs to debug level
    -t|--tenant:  set the tenant name to test. By default creates one
    --datacenter: set the datacenter name to test. By default creates one at http://localhost:9080/openvim
    -u|--url:     set the openmano server url. By default 'http://localhost:9090/openmano'
    --image:      use this image path for testing a VNF. By default a fake one is generated, valid for VIM in test mode'
    """

    #import openmanoclient from relative path
    module_info = imp.find_module("openmanoclient", [".."] )
    Client = imp.load_module("Client", *module_info)
    
    streamformat = "%(asctime)s %(name)s %(levelname)s: %(message)s"
    logging.basicConfig(format=streamformat)
    try:
        opts, args = getopt.getopt(sys.argv[1:], "t:u:dhv", ["url=", "tenant=", "debug", "help", "version", "verbose", "datacenter=", "image="])
    except getopt.GetoptError as err:
        print ("Error: {}\n Try '{} --help' for more information".format(str(err), sys.argv[0]))
        sys.exit(2)

    debug = False
    verbose = False
    url = "http://localhost:9090/openmano"
    to_delete_list=[]
    test_tenant = None
    test_datacenter = None
    test_vim_tenant = None
    test_image = None
    for o, a in opts:
        if o in ("-v", "--verbose"):
            verbose = True
        elif o in ("--version"):
            print ("{} version".format(sys.argv[0]), __version__, version_date)
            print ("(c) Copyright Telefonica")
            sys.exit()
        elif o in ("-h", "--help"):
            print(usage)
            sys.exit()
        elif o in ("-d", "--debug"):
            debug = True
        elif o in ("-u", "--url"):
            url = a
        elif o in ("-t", "--tenant"):
            test_tenant = a 
        elif o in ("--datacenter"):
            test_datacenter = a 
        elif o in ("--image"):
            test_image = a 
        else:
            assert False, "Unhandled option"

    
    
    client = Client.openmanoclient(
                            endpoint_url=url, 
                            tenant_name=test_tenant,
                            datacenter_name = test_datacenter,
                            debug = debug)

    import random
    test_number=1
    
    #TENANTS
    print("  {}. TEST create_tenant".format(test_number))
    test_number += 1
    long_name = _get_random_name(60)

    tenant = client.create_tenant(name=long_name, description=long_name)
    if verbose: print(tenant)

    print("  {}. TEST list_tenants".format(test_number))
    test_number += 1
    tenants = client.list_tenants()
    if verbose: print(tenants)
    
    print("  {}. TEST list_tenans filter by name".format(test_number))
    test_number += 1
    tenants_ = client.list_tenants(name=long_name)
    if not tenants_["tenants"]:
        raise Exception("Text error, no TENANT found with name")
    if verbose: print(tenants_)
    
    print("  {}. TEST get_tenant by UUID".format(test_number))
    test_number += 1
    tenant = client.get_tenant(uuid=tenants_["tenants"][0]["uuid"])
    if verbose: print(tenant)
        
    print("  {}. TEST delete_tenant by name".format(test_number))
    test_number += 1
    tenant = client.delete_tenant(name = long_name)
    if verbose: print(tenant)
    
    if not test_tenant:
        print("  {}. TEST create_tenant for remaining tests".format(test_number))
        test_number += 1
        test_tenant = "test-tenant "+\
        ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(40))
        tenant = client.create_tenant(name = test_tenant)
        if verbose: print(tenant)
        client["tenant_name"] = test_tenant
        
        to_delete_list.insert(0,{"item": "tenant", "function": client.delete_tenant, "params":{"name": test_tenant} })

    #DATACENTERS
    print("  {}. TEST create_datacenter".format(test_number))
    test_number += 1
    long_name = _get_random_name(60)

    datacenter = client.create_datacenter(name=long_name, vim_url="http://fakeurl/fake")
    if verbose: print(datacenter)

    print("  {}. TEST list_datacenters".format(test_number))
    test_number += 1
    datacenters = client.list_datacenters(all_tenants=True)
    if verbose: print(datacenters)
    
    print("  {}. TEST list_tenans filter by name".format(test_number))
    test_number += 1
    datacenters_ = client.list_datacenters(all_tenants=True, name=long_name)
    if not datacenters_["datacenters"]:
        raise Exception("Text error, no TENANT found with name")
    if verbose: print(datacenters_)
    
    print("  {}. TEST get_datacenter by UUID".format(test_number))
    test_number += 1
    datacenter = client.get_datacenter(uuid=datacenters_["datacenters"][0]["uuid"], all_tenants=True)
    if verbose: print(datacenter)
        
    print("  {}. TEST delete_datacenter by name".format(test_number))
    test_number += 1
    datacenter = client.delete_datacenter(name=long_name)
    if verbose: print(datacenter)
    
    if not test_datacenter:
        print("  {}. TEST create_datacenter for remaining tests".format(test_number))
        test_number += 1
        test_datacenter = "test-datacenter "+\
        ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(40))
        datacenter = client.create_datacenter(name=test_datacenter, vim_url="http://127.0.0.1:9080/openvim")
        if verbose: print(datacenter)
        client["datacenter_name"] = test_datacenter
        to_delete_list.insert(0,{"item": "datacenter", "function": client.delete_datacenter,
                                  "params":{
                                        "name": test_datacenter
                                    } 
                                 })

        print("  {}. TEST datacenter new tenenat".format(test_number))
        test_number += 1
        test_vim_tenant = "test-vimtenant "+\
        ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(40))
        vim_tenant = client.vim_action("create", "tenants", datacenter_name=test_datacenter, all_tenants=True, name=test_vim_tenant)
        if verbose: print(vim_tenant)
        client["datacenter_name"] = test_datacenter
        to_delete_list.insert(0,{"item": "vim_tenant", 
                                 "function": client.vim_action,
                                  "params":{
                                            "action":"delete",
                                            "item":"tenants",
                                            "datacenter_name": test_datacenter,
                                            "all_tenants": True,
                                            "uuid": vim_tenant["tenant"]["id"]
                                            }
                                 })

        print("  {}. TEST datacenter attach".format(test_number))
        test_number += 1
        datacenter = client.attach_datacenter(name=test_datacenter, vim_tenant_name=test_vim_tenant)
        if verbose: print(datacenter)
        client["datacenter_name"] = test_datacenter
        to_delete_list.insert(0,{"item": "datacenter-detach", "function": client.detach_datacenter, "params":{"name": test_datacenter} })

        client["datacenter_name"] = test_datacenter
        
    
    #VIM_ACTIONS
    print("  {}. TEST create_VIM_tenant".format(test_number))
    test_number += 1
    long_name = _get_random_name(60)

    tenant = client.vim_action("create", "tenants", name=long_name)
    if verbose: print(tenant)
    tenant_uuid = tenant["tenant"]["id"] 

    print("  {}. TEST list_VIM_tenants".format(test_number))
    test_number += 1
    tenants = client.vim_action("list", "tenants")
    if verbose: print(tenants)
    
    print("  {}. TEST get_VIM_tenant by UUID".format(test_number))
    test_number += 1
    tenant = client.vim_action("show", "tenants", uuid=tenant_uuid)
    if verbose: print(tenant)
        
    print("  {}. TEST delete_VIM_tenant by id".format(test_number))
    test_number += 1
    tenant = client.vim_action("delete", "tenants", uuid = tenant_uuid)
    if verbose: print(tenant)
    
    print("  {}. TEST create_VIM_network".format(test_number))
    test_number += 1
    long_name = _get_random_name(60)

    network = client.vim_action("create", "networks", name=long_name)
    if verbose: print(network)
    network_uuid = network["network"]["id"] 

    print("  {}. TEST list_VIM_networks".format(test_number))
    test_number += 1
    networks = client.vim_action("list", "networks")
    if verbose: print(networks)
    
    print("  {}. TEST get_VIM_network by UUID".format(test_number))
    test_number += 1
    network = client.vim_action("show", "networks", uuid=network_uuid)
    if verbose: print(network)
        
    print("  {}. TEST delete_VIM_network by id".format(test_number))
    test_number += 1
    network = client.vim_action("delete", "networks", uuid = network_uuid)
    if verbose: print(network)
    #VNFS
    print("  {}. TEST create_vnf".format(test_number))
    test_number += 1
    test_vnf_name = _get_random_name(255)
    if test_image:
        test_vnf_path = test_image
    else:
        test_vnf_path = "/random/path/" + "".join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ') for _ in range(20))
    
    vnf_descriptor={'vnf': {'name': test_vnf_name, 
                                'VNFC': [{'description': _get_random_name(255),
                                          'name': 'linux-VM',
                                          'VNFC image': test_vnf_path,
                                          'ram': 1024,
                                          'vcpus': 1,
                                          'bridge-ifaces': [{'name': 'eth0'}]
                                        }],
                                'description': _get_random_name(255),
                                'nets': [], 
                                'external-connections': [{'name': 'eth0', 
                                                          'local_iface_name': 'eth0',
                                                          'VNFC': 'linux-VM',
                                                          'type': 'bridge'}], 
                                'public': False}}

    vnf = client.create_vnf(descriptor=vnf_descriptor)
    if verbose: print(vnf)
    to_delete_list.insert(0,{"item": "vnf", "function": client.delete_vnf, "params":{"name": test_vnf_name} })

    print("  {}. TEST list_vnfs".format(test_number))
    test_number += 1
    vnfs = client.list_vnfs()
    if verbose: print(vnfs)
    
    print("  {}. TEST list_vnfs filter by name".format(test_number))
    test_number += 1
    vnfs_ = client.list_vnfs(name=test_vnf_name)
    if not vnfs_["vnfs"]:
        raise Exception("Text error, no VNF found with name")
    if verbose: print(vnfs_)
    
    print("  {}. TEST get_vnf by UUID".format(test_number))
    test_number += 1
    vnf = client.get_vnf(uuid=vnfs_["vnfs"][0]["uuid"])
    if verbose: print(vnf)

    #SCENARIOS
    print("  {}. TEST create_scenario".format(test_number))
    test_number += 1
    test_scenario_name = _get_random_name(255)
    
    scenario_descriptor={   'schema_version': 2,
                            'scenario': {
                                'name': test_scenario_name, 
                                'description': _get_random_name(255),
                                'public': True,
                                'vnfs':{
                                    'vnf1': {
                                        'vnf_name': test_vnf_name
                                    }
                                },
                                'networks':{
                                    'net1':{
                                        'external': True,
                                        'interfaces': [
                                            {'vnf1': 'eth0'}
                                        ]
                                    }
                                }
                            }
                        }

    scenario = client.create_scenario(descriptor=scenario_descriptor)
    if verbose: print(scenario)
    to_delete_list.insert(0,{"item": "scenario", "function": client.delete_scenario, "params":{"name": test_scenario_name} })

    print("  {}. TEST list_scenarios".format(test_number))
    test_number += 1
    scenarios = client.list_scenarios()
    if verbose: print(scenarios)
    
    print("  {}. TEST list_scenarios filter by name".format(test_number))
    test_number += 1
    scenarios_ = client.list_scenarios(name=test_scenario_name)
    if not scenarios_["scenarios"]:
        raise Exception("Text error, no VNF found with name")
    if verbose: print(scenarios_)
    
    print("  {}. TEST get_scenario by UUID".format(test_number))
    test_number += 1
    scenario = client.get_scenario(uuid=scenarios_["scenarios"][0]["uuid"])
    if verbose: print(scenario)



    #INSTANCES
    print("  {}. TEST create_instance".format(test_number))
    test_number += 1
    test_instance_name = _get_random_name(255)
    
    instance_descriptor={   'schema_version': 2,
                            'instance': {
                                'name': test_instance_name, 
                                'description': _get_random_name(255),
                                'public': True,
                                'vnfs':{
                                    'vnf1': {
                                        'vnf_name': test_vnf_name
                                    }
                                },
                                'networks':{
                                    'net1':{
                                        'external': True,
                                        'interfaces': [
                                            {'vnf1': 'eth0'}
                                        ]
                                    }
                                }
                            }
                        }

    instance = client.create_instance(scenario_name=test_scenario_name, name=test_instance_name )
    if verbose: print(instance)
    to_delete_list.insert(0,{"item": "instance", "function": client.delete_instance, "params":{"name": test_instance_name} })

    print("  {}. TEST list_instances".format(test_number))
    test_number += 1
    instances = client.list_instances()
    if verbose: print(instances)
    
    print("  {}. TEST list_instances filter by name".format(test_number))
    test_number += 1
    instances_ = client.list_instances(name=test_instance_name)
    if not instances_["instances"]:
        raise Exception("Text error, no VNF found with name")
    if verbose: print(instances_)
    
    print("  {}. TEST get_instance by UUID".format(test_number))
    test_number += 1
    instance = client.get_instance(uuid=instances_["instances"][0]["uuid"])
    if verbose: print(instance)




    #DELETE Create things
    for item in to_delete_list:
        print("  {}. TEST delete_{}".format(test_number, item["item"]))
        test_number += 1
        response = item["function"](**item["params"]) 
        if verbose: print(response)
    

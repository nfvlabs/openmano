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
This is the main program of openvim, it reads the configuration 
and launches the rest of threads: http clients, openflow controller
and host controllers  
'''

__author__="Alfonso Tierno"
__date__ ="$10-jul-2014 12:07:15$"
__version__="0.4.1-r455"
version_date="Jan 2016"
database_version="0.5"      #expected database schema version

import httpserver
from utils import auxiliary_functions as af
import sys
import getopt
import time
import vim_db
import yaml
import os
from jsonschema import validate as js_v, exceptions as js_e
import host_thread as ht
import dhcp_thread as dt
import openflow_thread as oft
import threading
from vim_schema import config_schema
import logging
import imp

global config_dic
global logger
logger = logging.getLogger('vim')

def load_configuration(configuration_file):
    default_tokens ={'http_port':9080, 'http_host':'localhost', 
                     'of_controller_nets_with_same_vlan':True,
                     'image_path':'/opt/VNF/images',
                     'network_vlan_range_start':1000,
                     'network_vlan_range_end': 4096,
                     'log_level': "DEBUG",
                     'log_level_db': "ERROR",
                     'log_level_of': 'ERROR',
            }
    try:
        #First load configuration from configuration file
        #Check config file exists
        if not os.path.isfile(configuration_file):
            return (False, "Configuration file '"+configuration_file+"' does not exists")
            
        #Read and parse file
        (return_status, code) = af.read_file(configuration_file)
        if not return_status:
            return (return_status, "Error loading configuration file '"+configuration_file+"': "+code)
        try:
            config = yaml.load(code)
        except yaml.YAMLError, exc:
            error_pos = ""
            if hasattr(exc, 'problem_mark'):
                mark = exc.problem_mark
                error_pos = " at position: (%s:%s)" % (mark.line+1, mark.column+1)
            return (False, "Error loading configuration file '"+configuration_file+"'"+error_pos+": content format error: Failed to parse yaml format")
        
        
        try:
            js_v(config, config_schema)
        except js_e.ValidationError, exc:
            error_pos = ""
            if len(exc.path)>0: error_pos=" at '" + ":".join(map(str, exc.path))+"'"
            return False, "Error loading configuration file '"+configuration_file+"'"+error_pos+": "+exc.message 
        
        
        #Check default values tokens
        for k,v in default_tokens.items():
            if k not in config: config[k]=v
        #Check vlan ranges
        if config["network_vlan_range_start"]+10 >= config["network_vlan_range_end"]:
            return False, "Error invalid network_vlan_range less than 10 elements"
    
    except Exception,e:
        return (False, "Error loading configuration file '"+configuration_file+"': "+str(e))
    return (True, config)

def create_database_connection(config_dic):
    db = vim_db.vim_db( (config_dic["network_vlan_range_start"],config_dic["network_vlan_range_end"]), config_dic['log_level_db'] );
    if db.connect(config_dic['db_host'], config_dic['db_user'], config_dic['db_passwd'], config_dic['db_name']) == -1:
        logger.error("Cannot connect to database %s at %s@%s", config_dic['db_name'], config_dic['db_user'], config_dic['db_host'])
        exit(-1)
    return db

def usage():
    print "Usage: ", sys.argv[0], "[options]"
    print "      -v|--version: prints current version"
    print "      -c|--config [configuration_file]: loads the configuration file (default: openvimd.cfg)"
    print "      -h|--help: shows this help"
    print "      -p|--port [port_number]: changes port number and overrides the port number in the configuration file (default: 9090)"
    print "      -P|--adminport [port_number]: changes admin port number and overrides the port number in the configuration file (default: 9095)"
    return


if __name__=="__main__":
    #streamformat = "%(levelname)s (%(module)s:%(lineno)d) %(message)s"
    streamformat = "%(asctime)s %(name)s %(levelname)s: %(message)s"
    logging.basicConfig(format=streamformat, level= logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvc:p:P:", ["config", "help", "version", "port", "adminport"])
    except getopt.GetoptError, err:
        # print help information and exit:
        logger.error("%s. Type -h for help", err) # will print something like "option -a not recognized"
        #usage()
        sys.exit(-2)

    port=None
    port_admin = None
    config_file = 'openvimd.cfg'

    for o, a in opts:
        if o in ("-v", "--version"):
            print "openvimd version", __version__, version_date
            print "(c) Copyright Telefonica"
            sys.exit(0)
        elif o in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif o in ("-c", "--config"):
            config_file = a
        elif o in ("-p", "--port"):
            port = a
        elif o in ("-P", "--adminport"):
            port_admin = a
        else:
            assert False, "Unhandled option"

    
    try:
        #Load configuration file
        r, config_dic = load_configuration(config_file)
        #print config_dic
        if not r:
            logger.error(config_dic)
            config_dic={}
            exit(-1)
        logging.basicConfig(level = getattr(logging, config_dic['log_level']))
        logger.setLevel(getattr(logging, config_dic['log_level']))
        #override parameters obtained by command line
        if port is not None: config_dic['http_port'] = port
        if port_admin is not None: config_dic['http_admin_port'] = port_admin
        
        #check mode
        if 'mode' not in config_dic:
            config_dic['mode'] = 'normal'
            #allow backward compatibility of test_mode option
            if 'test_mode' in config_dic and config_dic['test_mode']==True:
                config_dic['mode'] = 'test' 
        if config_dic['mode'] == 'development' and ( 'development_bridge' not in config_dic or config_dic['development_bridge'] not in config_dic.get("bridge_ifaces",None) ):
            logger.error("'%s' is not a valid 'development_bridge', not one of the 'bridge_ifaces'", config_file)
            exit(-1)
            
        if config_dic['mode'] != 'normal':
            print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
            print "!! Warning, openvimd in TEST mode '%s'" % config_dic['mode']
            print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
        config_dic['version'] = __version__

    #Connect to database
        db_http = create_database_connection(config_dic)
        r = db_http.get_db_version()
        if r[0]<0:
            logger.error("DATABASE is not a VIM one or it is a '0.0' version. Try to upgrade to version '%s' with './database_utils/migrate_vim_db.sh'", database_version)
            exit(-1)
        elif r[1]!=database_version:
            logger.error("DATABASE wrong version '%s'. Try to upgrade/downgrade to version '%s' with './database_utils/migrate_vim_db.sh'", r[1], database_version) 
            exit(-1)
        db_of = create_database_connection(config_dic)
        db_lock= threading.Lock()
        config_dic['db'] = db_of
        config_dic['db_lock'] = db_lock

    #precreate interfaces; [bridge:<host_bridge_name>, VLAN used at Host, uuid of network camping in this bridge, speed in Gbit/s
        config_dic['dhcp_nets']=[]
        config_dic['bridge_nets']=[]
        for bridge,vlan_speed in config_dic["bridge_ifaces"].items():
            #skip 'development_bridge'
            if config_dic['mode'] == 'development' and config_dic['development_bridge'] == bridge:
                continue
            config_dic['bridge_nets'].append( [bridge, vlan_speed[0], vlan_speed[1], None] )
        del config_dic["bridge_ifaces"]

        #check if this bridge is already used (present at database) for a network)
        used_bridge_nets=[]
        for brnet in config_dic['bridge_nets']:
            r,nets = db_of.get_table(SELECT=('uuid',), FROM='nets',WHERE={'bind': "bridge:"+brnet[0]})
            if r>0:
                brnet[3] = nets[0]['uuid']
                used_bridge_nets.append(brnet[0])
                if config_dic.get("dhcp_server"):
                    if brnet[0] in config_dic["dhcp_server"]["bridge_ifaces"]:
                        config_dic['dhcp_nets'].append(nets[0]['uuid'])
        if len(used_bridge_nets) > 0 :
            logger.info("found used bridge nets: " + ",".join(used_bridge_nets))
        #get nets used by dhcp
        if config_dic.get("dhcp_server"):
            for net in config_dic["dhcp_server"].get("nets", () ):
                r,nets = db_of.get_table(SELECT=('uuid',), FROM='nets',WHERE={'name': net})
                if r>0:
                    config_dic['dhcp_nets'].append(nets[0]['uuid'])
    
    # get host list from data base before starting threads
        r,hosts = db_of.get_table(SELECT=('name','ip_name','user','uuid'), FROM='hosts', WHERE={'status':'ok'})
        if r<0:
            logger.error("Cannot get hosts from database %s", hosts)
            exit(-1)
    # create connector to the openflow controller
        of_test_mode = False if config_dic['mode']=='normal' or config_dic['mode']=="OF only" else True

        if of_test_mode:
            OF_conn = oft.of_test_connector({"of_debug": config_dic['log_level_of']} )
        else:
            #load other parameters starting by of_ from config dict in a temporal dict
            temp_dict={ "of_ip":  config_dic['of_controller_ip'],
                        "of_port": config_dic['of_controller_port'], 
                        "of_dpid": config_dic['of_controller_dpid'],
                        "of_debug":   config_dic['log_level_of']
                }
            for k,v in config_dic.iteritems():
                if type(k) is str and k[0:3]=="of_" and k[0:13] != "of_controller":
                    temp_dict[k]=v
            if config_dic['of_controller']=='opendaylight':
                module = "ODL"
            elif "of_controller_module" in config_dic:
                module = config_dic["of_controller_module"]
            else:
                module = config_dic['of_controller']
            module_info=None
            try:
                module_info = imp.find_module(module)
            
                OF_conn = imp.load_module("OF_conn", *module_info)
                try:
                    OF_conn = OF_conn.OF_conn(temp_dict)
                except Exception as e: 
                    logger.error("Cannot open the Openflow controller '%s': %s", type(e).__name__, str(e))
                    if module_info and module_info[0]:
                        file.close(module_info[0])
                    exit(-1)
            except (IOError, ImportError) as e:
                if module_info and module_info[0]:
                    file.close(module_info[0])
                logger.error("Cannot open openflow controller module '%s'; %s: %s; revise 'of_controller' field of configuration file.", module, type(e).__name__, str(e))
                exit(-1)


    #create openflow thread
        thread = oft.openflow_thread(OF_conn, of_test=of_test_mode, db=db_of,  db_lock=db_lock,
                        pmp_with_same_vlan=config_dic['of_controller_nets_with_same_vlan'],
                        debug=config_dic['log_level_of'])
        r,c = thread.OF_connector.obtain_port_correspondence()
        if r<0:
            logger.error("Cannot get openflow information %s", c)
            exit()
        thread.start()
        config_dic['of_thread'] = thread

    #create dhcp_server thread
        host_test_mode = True if config_dic['mode']=='test' or config_dic['mode']=="OF only" else False
        dhcp_params = config_dic.get("dhcp_server")
        if dhcp_params:
            thread = dt.dhcp_thread(dhcp_params=dhcp_params, test=host_test_mode, dhcp_nets=config_dic["dhcp_nets"], db=db_of,  db_lock=db_lock, debug=config_dic['log_level_of'])
            thread.start()
            config_dic['dhcp_thread'] = thread

        
    #Create one thread for each host
        host_test_mode = True if config_dic['mode']=='test' or config_dic['mode']=="OF only" else False
        host_develop_mode = True if config_dic['mode']=='development' else False
        host_develop_bridge_iface = config_dic.get('development_bridge', None)
        config_dic['host_threads'] = {}
        for host in hosts:
            host['image_path'] = '/opt/VNF/images/openvim'
            thread = ht.host_thread(name=host['name'], user=host['user'], host=host['ip_name'], db=db_of, db_lock=db_lock,
                    test=host_test_mode, image_path=config_dic['image_path'], version=config_dic['version'],
                    host_id=host['uuid'], develop_mode=host_develop_mode, develop_bridge_iface=host_develop_bridge_iface  )
            thread.start()
            config_dic['host_threads'][ host['uuid'] ] = thread
                
            
        
    #Create thread to listen to web requests
        http_thread = httpserver.httpserver(db_http, 'http', config_dic['http_host'], config_dic['http_port'], False, config_dic)
        http_thread.start()
        
        if 'http_admin_port' in config_dic: 
            db_http = create_database_connection(config_dic)
            http_thread_admin = httpserver.httpserver(db_http, 'http-admin', config_dic['http_host'], config_dic['http_admin_port'], True)
            http_thread_admin.start()
        else:
            http_thread_admin = None
        time.sleep(1)      
        logger.info('Waiting for http clients')
        print 'openvimd ready'
        print '===================='
        sys.stdout.flush()
        
        #TODO: Interactive console would be nice here instead of join or sleep
        
        r="help" #force print help at the beginning
        while True:
            if r=='exit':
                break      
            elif r!='':
                print "type 'exit' for terminate"
            r = raw_input('> ')

    except (KeyboardInterrupt, SystemExit):
        pass

    logger.info('Exiting openvimd')
    threads = config_dic.get('host_threads', {})
    if 'of_thread' in config_dic:
        threads['of'] = (config_dic['of_thread'])
    if 'dhcp_thread' in config_dic:
        threads['dhcp'] = (config_dic['dhcp_thread'])
    
    for thread in threads.values():
        thread.insert_task("exit")
    for thread in threads.values():
        thread.join()
    #http_thread.join()
    #if http_thread_admin is not None: 
    #http_thread_admin.join()
    logger.debug( "bye!")
    exit()


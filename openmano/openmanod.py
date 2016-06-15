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
openmano server.
Main program that implements a reference NFVO (Network Functions Virtualisation Orchestrator).
It interfaces with an NFV VIM through its API and offers a northbound interface, based on REST (openmano API),
where NFV services are offered including the creation and deletion of VNF templates, VNF instances,
network service templates and network service instances. 

It loads the configuration file and launches the http_server thread that will listen requests using openmano API.
'''
__author__="Alfonso Tierno, Gerardo Garcia, Pablo Montes"
__date__ ="$26-aug-2014 11:09:29$"
__version__="0.4.40-r476"
version_date="Jun 2016"
database_version="0.10"      #expected database schema version

import httpserver
import time
import os
import sys
import getopt
import yaml
import nfvo_db
from jsonschema import validate as js_v, exceptions as js_e
import utils
from openmano_schemas import config_schema
import nfvo
import logging

global global_config
logger = logging.getLogger('mano')

class LoadConfigurationException(Exception):
    pass

def load_configuration(configuration_file):
    default_tokens ={'http_port':9090,
                     'http_host':'localhost',
                     'log_level': 'DEBUG',
                     'log_level_db': 'ERROR',
                     'log_level_vimconn': 'DEBUG',
                    }
    try:
        #Check config file exists
        if not os.path.isfile(configuration_file):
            raise LoadConfigurationException("Error: Configuration file '"+configuration_file+"' does not exist.")
            
        #Read file
        (return_status, code) = utils.read_file(configuration_file)
        if not return_status:
            raise LoadConfigurationException("Error loading configuration file '"+configuration_file+"': "+code)
        #Parse configuration file
        try:
            config = yaml.load(code)
        except yaml.YAMLError, exc:
            error_pos = ""
            if hasattr(exc, 'problem_mark'):
                mark = exc.problem_mark
                error_pos = " at position: (%s:%s)" % (mark.line+1, mark.column+1)
            raise LoadConfigurationException("Error loading configuration file '"+configuration_file+"'"+error_pos+": content format error: Failed to parse yaml format")

        #Validate configuration file with the config_schema
        try:
            js_v(config, config_schema)
        except js_e.ValidationError, exc:
            error_pos = ""
            if len(exc.path)>0: error_pos=" at '" + ":".join(map(str, exc.path))+"'"
            raise LoadConfigurationException("Error loading configuration file '"+configuration_file+"'"+error_pos+": "+exc.message) 
        
        #Check default values tokens
        for k,v in default_tokens.items():
            if k not in config: config[k]=v
    
    except Exception,e:
        raise LoadConfigurationException("Error loading configuration file '"+configuration_file+"': "+str(e))
                
    return config

def console_port_iterator():
    '''this iterator deals with the http_console_ports 
    returning the ports one by one
    '''
    index = 0
    while index < len(global_config["http_console_ports"]):
        port = global_config["http_console_ports"][index]
        #print("ports -> ", port)
        if type(port) is int:
            yield port
        else: #this is dictionary with from to keys
            port2 = port["from"]
            #print("ports -> ", port, port2)
            while port2 <= port["to"]:
                #print("ports -> ", port, port2)
                yield port2
                port2 += 1
        index += 1
    
    
def usage():
    print("Usage: ", sys.argv[0], "[options]")
    print( "      -v|--version: prints current version")
    print( "      -c|--config [configuration_file]: loads the configuration file (default: openmanod.cfg)")
    print( "      -h|--help: shows this help")
    print( "      -p|--port [port_number]: changes port number and overrides the port number in the configuration file (default: 9090)")
    print( "      -P|--adminport [port_number]: changes admin port number and overrides the port number in the configuration file (default: 9095)")
    print( "      -V|--vnf-repository: changes the path of the vnf-repository and overrides the path in the configuration file")
    return
    
if __name__=="__main__":
    #streamformat = "%(levelname)s (%(module)s:%(lineno)d) %(message)s"
    streamformat = "%(asctime)s %(name)s %(levelname)s: %(message)s"
    logging.basicConfig(format=streamformat, level= logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    # Read parameters and configuration file 
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvc:V:p:P:", ["config", "help", "version", "port", "vnf-repository", "adminport"])
    
        port=None
        port_admin = None
        config_file = 'openmanod.cfg'
        vnf_repository = None
        
        for o, a in opts:
            if o in ("-v", "--version"):
                print "openmanod version", __version__, version_date
                print "(c) Copyright Telefonica"
                sys.exit()
            elif o in ("-h", "--help"):
                usage()
                sys.exit()
            elif o in ("-V", "--vnf-repository"):
                vnf_repository = a
            elif o in ("-c", "--config"):
                config_file = a
            elif o in ("-p", "--port"):
                port = a
            elif o in ("-P", "--adminport"):
                port_admin = a
            else:
                assert False, "Unhandled option"
    
        global_config = load_configuration(config_file)
        #print global_config
        logging.basicConfig(level = getattr(logging, global_config.get('log_level',"debug")))
        logger.setLevel(getattr(logging, global_config['log_level']))
        # Override parameters obtained by command line
        if port is not None: global_config['http_port'] = port
        if port_admin is not None: global_config['http_admin_port'] = port_admin
        if vnf_repository is not None:
            global_config['vnf_repository'] = vnf_repository
        else:
            if not 'vnf_repository' in global_config:  
                logger.error( os.getcwd() )
                global_config['vnf_repository'] = os.getcwd()+'/vnfrepo'
        #print global_config
        
        if not os.path.exists(global_config['vnf_repository']):
            logger.error( "Creating folder vnf_repository folder: '%s'.", global_config['vnf_repository'])
            try:
                os.makedirs(global_config['vnf_repository'])
            except Exception as e:
                logger.error( "Error '%s'. Ensure the path 'vnf_repository' is properly set at %s",e.args[1], config_file)
                exit(-1)
        
        global_config["console_port_iterator"] = console_port_iterator
        global_config["console_thread"]={}
        global_config["console_ports"]={}
        # Initialize DB connection
        mydb = nfvo_db.nfvo_db();
        if mydb.connect(global_config['db_host'], global_config['db_user'], global_config['db_passwd'], global_config['db_name']) == -1:
            logger.error("Error connecting to database %s at %s@%s", global_config['db_name'], global_config['db_user'], global_config['db_host'])
            exit(-1)
        r = mydb.get_db_version()
        if r[0]<0:
            logger.error("Error DATABASE is not a MANO one or it is a '0.0' version. Try to upgrade to version '%s' with './database_utils/migrate_mano_db.sh'", database_version)
            exit(-1)
        elif r[1]!=database_version:
            logger.error("Error DATABASE wrong version '%s'. Try to upgrade/downgrade to version '%s' with './database_utils/migrate_mano_db.sh'", r[1], database_version)
            exit(-1)
        
        nfvo.global_config=global_config
        
        httpthread = httpserver.httpserver(mydb, False, global_config['http_host'], global_config['http_port'])
        
        httpthread.start()
        if 'http_admin_port' in global_config: 
            httpthreadadmin = httpserver.httpserver(mydb, True, global_config['http_host'], global_config['http_admin_port'])
            httpthreadadmin.start()
        time.sleep(1)      
        logger.info('Waiting for http clients')
        print('openmanod ready')
        print('====================')
        time.sleep(20)
        sys.stdout.flush()

        #TODO: Interactive console must be implemented here instead of join or sleep

        #httpthread.join()
        #if 'http_admin_port' in global_config: 
        #    httpthreadadmin.join()
        while True:
            time.sleep(86400)
        for thread in global_config["console_thread"]:
            thread.terminate = True

    except KeyboardInterrupt:
        logger.info('KyboardInterrupt')
    except SystemExit:
        pass
    except getopt.GetoptError as e:
        logger.error("Error: %s", str(e)) # will print something like "option -a not recognized"
        #usage()
        exit(-1)
    except LoadConfigurationException as e:
        logger.error("Error: %s", str(e))
        exit(-1)


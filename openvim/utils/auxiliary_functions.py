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
Common usuful functions 
'''

__author__="Alfonso Tierno, Pablo Montes"
__date__ ="$10-jul-2014 12:07:15$"


import yaml
import paramiko 
from definitionsClass import definitionsClass
from definitionsClass import Units
import random
from jsonschema import validate as js_v, exceptions as js_e

def check_and_convert_units(value, value_type):
    """TODO: Update description
    This method receives a text with 2 fields using a blank as separator and a list of valid units. The first field must represent a number
    and the second one units. 
    In case the second field is not one of valid_units (False, <error description>) is returned.
    In case the second field is a valid unit the first number is converted in the following way:
    Gbps, Mbps, kbps -> Mbps
    GB,MB,KB,B,GiB,MiB,KiB -> B
    GHz,MHz,KHz,Hz -> Hz
    If conversion is done successfully (True, <converted value>) is returned"""
    try:
        if value_type == Units.no_units:
            if not isinstance(value,int) and not isinstance(value,float):
                return (False, 'When no units are used only an integer or float must be used')
        elif value_type == Units.name:
            if not isinstance(value,str):
                return (False, 'For names str must be used')
        elif value_type == Units.boolean:
            if not isinstance(value,bool):
                return (False, 'A boolean or Yes/No mut be used')
        else:
            splitted  = value.split(' ')
            if len(splitted) != 2:
                return (False, 'Expected format: <value> <units>')
            (value, units) = splitted 
            if ',' in value or '.' in value:
                return (False, 'Use integers to represent numeric values')
                
            value = int(value)
            
#            if not isinstance(value_type, Units):
#                return (False, 'Not valid value_type')
            
            valid_units = definitionsClass.units[value_type]
            
            #Convert everything to upper in order to make comparations easier
            units = units.upper()
            for i in range(0, len(valid_units)):
                valid_units[i] = valid_units[i].upper()
            
            #Check the used units are valid ones
            if units not in valid_units:
                return (False, 'Valid units are: '+', '.join(valid_units))

            if units.startswith('GI'):
                value = value *1024*1024*1024
            elif units.startswith('MI'):
                value = value *1024*1024
            elif units.startswith('KI'):
                value = value *1024
            elif units.startswith('G'):
                value = value *1000000000
            elif units.startswith('M'):
                value = value *1000000
            elif units.startswith('K'):
                value = value *1000
    except Exception,e:
        return (False, 'Unexpected error in auxiliary_functions.py - check_and_convert_units:\n'+str(e))

    return (True, value)
        
def get_ssh_connection(machine, user=None, password=None):
    """Stablishes an ssh connection to the remote server. Returns (True, paramiko_ssh) in case of success or (False, <error message>) in case of error"""
    try:
        s = paramiko.SSHClient()
        s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        s.load_system_host_keys()
        s.connect(machine, 22, user, password, timeout=10)
    except Exception,e:
        return (False, 'It was not possible to connect to '+machine+str(e))
        
    return (True, s)

def run_in_remote_server(s,command):
    """Runs in the remote server the specified command. Returns (True, stdout) in case of success or (False, <error message>) in case of error"""
    try:
        (_, stdout, stderr) = s.exec_command(command)
        error_msg = stderr.read()
        if len(error_msg) > 0:
            return (False, error_msg)
    except Exception,e:
        return (False, str(e))
    
    return (True, stdout)

def read_file(file_):
    """Reads a file specified by 'file' and returns (True,<its content as a string>) in case of success or (False, <error message>) in case of failure"""
    try:
        f = open(file_, 'r')
        read_data = f.read()
        f.close()
    except Exception,e:
        return (False, str(e))
      
    return (True, read_data)

def check_contains(element, keywords):
    """Auxiliary function used to check if a yaml structure contains or not
    an specific field. Returns a bool"""
    for key in keywords:
        if not key in element:
            return False      
    return True

def check_contains_(element, keywords):
    """Auxiliary function used to check if a yaml structure contains or not
    an specific field. Returns a bool,missing_variables"""
    for key in keywords:
        if not key in element:
            return False, key      
    return True, None

def write_file(file_, content):
    """Generates a file specified by 'file' and fills it using 'content'"""
    f = open(file_, 'w')
    f.write(content)
    f.close()

def nice_print(yaml_element):
    """Print a yaml structure. Used mainly for debugging"""
    print(yaml.dump(yaml_element, default_flow_style=False))
    
def new_random_mac():
    mac = (0xE2, random.randint(0x00, 0xff), random.randint(0x00, 0xff), random.randint(0x00, 0xff), random.randint(0x00, 0xff), random.randint(0x00, 0xff) )
    return ':'.join(map(lambda x: "%02X" % x, mac)) 

def parse_dict(var, template):
    if type(var) is not dict: return -1, 'not a dictionary'
    for _,tv in template.items():
        if type(tv) is list:
            return
    
def delete_nulls(var):
    if type(var) is dict:
        for k in var.keys():
            if var[k] is None: del var[k]
            elif type(var[k]) is dict or type(var[k]) is list or type(var[k]) is tuple: 
                if delete_nulls(var[k]): del var[k]
        if len(var) == 0: return True
    elif type(var) is list or type(var) is tuple:
        for k in var:
            if type(k) is dict: delete_nulls(k)
        if len(var) == 0: return True
    return False

def get_next_2pow(var):
    if var==0: return 0
    v=1
    while v<var: v=v*2
    return v        

def check_valid_uuid(uuid):
    id_schema = {"type" : "string", "pattern": "^[a-fA-F0-9]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$"}
    try:
        js_v(uuid, id_schema)
        return True
    except js_e.ValidationError:
        return False

def DeleteNone(var):
    '''Removes recursively empty dictionaries or lists
    return True if var is an empty dict or list '''
    if type(var) is dict:
        for k in var.keys():
            if var[k] is None: del var[k]
            elif type(var[k]) is dict or type(var[k]) is list or type(var[k]) is tuple: 
                if DeleteNone(var[k]): del var[k]
        if len(var) == 0: return True
    elif type(var) is list or type(var) is tuple:
        for k in var:
            if type(k) is dict: DeleteNone(k)
        if len(var) == 0: return True
    return False
    
def gen_random_mac():
    '''generates a random mac address. Avoid multicast, broadcast, etc
    '''
    mac = (
        #52,54,00,
        #2 + 4*random.randint(0x00, 0x3f), #4 multiple, unicast local mac address
        0x52,
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff) 
    )
    return ':'.join(map(lambda x: "%02x" % x, mac))


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
This is a client tester for openvim.
It is almost DEPRECATED by the openvim client

The reason for keeping is because it is used for some scripts
and it contain the -r option (delete recursive)  
that it is very useful for deleting content of database.
Another difference from openvim is that it is more verbose
and so more suitable for the developers
'''

__author__="Alfonso Tierno"
__date__ ="$5-oct-2014 11:09:29$"

import requests
import json
import yaml
import sys
import getopt
from jsonschema import validate as js_v, exceptions as js_e

version="0.0.2"
global global_config


def get_elements(url):
    headers_req = {'content-type': 'application/json'}
    try:
        vim_response = requests.get(url, headers = headers_req)
        #print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
        #print vim_response.json()
        #print json.dumps(vim_response.json(), indent=4)
            content = vim_response.json()
            return 1, content
            #print http_content
        else:
            text = " Error. VIM response '%s': not possible to GET %s" % (vim_response.status_code, url)
            text += "\n " + vim_response.text
            #print text
            return -vim_response.status_code,text
    except requests.exceptions.RequestException, e:
        return -1, " Exception "+ str(e.message)

def delete_elements(url):
    headers_req = {'content-type': 'application/json'}
    
    try:
        vim_response = requests.delete(url, headers = headers_req)
        #print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            pass
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
        else:
            #print vim_response.text
            text = " Error. VIM response '%s': not possible to DELETE %s" % (vim_response.status_code, url)
            text += "\n " + vim_response.text
            #print text
            return -vim_response.status_code,text
    except requests.exceptions.RequestException, e:
        return -1, " Exception "+ str(e.message)
    return 1, None


def new_elements(url, payload):
    headers_req = {'Accept': 'application/json', 'content-type': 'application/json'}
    #print str(payload)
    try:
        vim_response = requests.post(url, data=json.dumps(payload), headers=headers_req)
        #print vim_response
        #print vim_response.status_code
        if vim_response.status_code == 200:
            #print vim_response.json()
            #print json.dumps(vim_response.json(), indent=4)
            return 1, vim_response.text
        else:
            #print vim_response.text
            text = "Error. VIM response '%s': not possible to ADD %s" % (vim_response.status_code, url)
            text += "\n" + vim_response.text
            #print text
            return -vim_response.status_code,text
    except requests.exceptions.RequestException, e:
        return -1, " Exception "+ str(e.message)


def get_details(url, what, c):
    item_list = []
    return_dict = {what+'s': []}
    
    item = c.get(what,None)
    if item is None: item = c.get(what+'s',None)
    if item is None:
        error_text= " Internal error, not found '" + what +"[s]' in content"
        print 'get_details()', error_text, c
        return -1, error_text 
    if type(item) is list: 
        item_list = item
    else:
        item_list.append(item)
    if len(item_list)==0:
        print what, "not found"
        return 1
    for item in item_list: 
        uuid = item.get('id',None)
        if uuid is None: uuid = item.get('uuid',None)
        if uuid is None:
            error_text= " Internal error, not found 'id/uuid' in item"
            print 'get_details()', error_text, item
            return -1, error_text 
        #print " get", what, uuid, "     >>>>>>>> ",
        r,c = get_elements(url + "/" + uuid)
        if r<0:              
        #    print "fail"
            print " get", what, uuid, "fail", c
            return -1, c
        #else:
        #    print 'ok'
        return_dict[what+'s'].append(c[what])
    return 1, return_dict


def action_details(url, what, c, force, payload):
    item_list = []
    return_dict = {what+'s': []}
    headers_req = {'Accept': 'application/json', 'content-type': 'application/json'}
    fail=0
    ok=0
    
    #Allows for payload both keypairs inside a 'server','port' ... or directly. In later case, put keypairs inside what
        
    item = c.get(what,None)
    if item is None: item = c.get(what+'s',None)
    if item is None:
        error_text= " Internal error, not found '" + what +"[s]' in content"
        print 'get_details()', error_text, c
        return -1, error_text 
    if type(item) is list: 
        item_list = item
    else:
        item_list.append(item)
    if len(item_list)==0:
        print what, "not found"
        return 1
    for item in item_list: 
        name = item.get('name',None)
        uuid = item.get('id',None)
        if uuid is None: uuid = item.get('uuid',None)
        if uuid is None:
            error_text= " Internal error, not found 'id/uuid' in item"
            print 'get_details()', error_text, item
            return -1, error_text 
        if not force:
            r = raw_input("Action on  " + what + " " + uuid + " " + name + " (y/N)? ")
            if  len(r)>0  and r[0].lower()=="y":
                print " put", what, uuid, "     >>>>>>>> ",
            else:
                continue

        #print str(payload)
        try:
            vim_response = requests.post(url + "/" + uuid + "/action", data=json.dumps(payload), headers=headers_req)
            if vim_response.status_code == 200:
                print 'ok'
                ok += 1
                return_dict[what+'s'].append(vim_response.json())
                return_dict[what+'s'][-1]['uuid'] = uuid
                return_dict[what+'s'][-1]['name'] = name
            else:
                fail += 1
                print "fail"
                #print vim_response.text
                #text = "Error. VIM response '%s': not possible to PUT %s" % (vim_response.status_code, url)
                #text += "\n" + vim_response.text
                #print text
                error_dict = vim_response.json()
                error_dict['error']['uuid']=uuid
                error_dict['error']['name']=name
                return_dict[what+'s'].append(error_dict)
        except requests.exceptions.RequestException, e:
            return -1, " Exception "+ str(e.message)
    if ok>0 and fail>0: return 0, return_dict
    elif fail==0 :      return 1, return_dict
    else:               return -1, return_dict



def edit_details(url, what, c, force, payload):
    item_list = []
    return_dict = {what+'s': []}
    headers_req = {'Accept': 'application/json', 'content-type': 'application/json'}
    fail=0
    ok=0
    
    #Allows for payload both keypairs inside a 'server','port' ... or directly. In later case, put keypairs inside what
    if what not in payload:
        payload = {what:payload}
        
    item = c.get(what,None)
    if item is None: item = c.get(what+'s',None)
    if item is None:
        error_text= " Internal error, not found '" + what +"[s]' in content"
        print 'get_details()', error_text, c
        return -1, error_text 
    if type(item) is list: 
        item_list = item
    else:
        item_list.append(item)
    if len(item_list)==0:
        print what, "not found"
        return 1
    for item in item_list: 
        name = item.get('name',None)
        uuid = item.get('id',None)
        if uuid is None: uuid = item.get('uuid',None)
        if uuid is None:
            error_text= " Internal error, not found 'id/uuid' in item"
            print 'get_details()', error_text, item
            return -1, error_text 
        if not force:
            r = raw_input("Edit " + what + " " + uuid + " " + name + " (y/N)? ")
            if  len(r)>0  and r[0].lower()=="y":
                print " put", what, uuid, "     >>>>>>>> ",
            else:
                continue

        #print str(payload)
        try:
            vim_response = requests.put(url + "/" + uuid, data=json.dumps(payload), headers=headers_req)
            if vim_response.status_code == 200:
                print 'ok'
                ok += 1
                return_dict[what+'s'].append( vim_response.json()[what] )
            else:
                fail += 1
                print "fail"
                #print vim_response.text
                #text = "Error. VIM response '%s': not possible to PUT %s" % (vim_response.status_code, url)
                #text += "\n" + vim_response.text
                #print text
                error_dict = vim_response.json()
                error_dict['error']['uuid']=uuid
                error_dict['error']['name']=name
                return_dict[what+'s'].append(error_dict)
        except requests.exceptions.RequestException, e:
            return -1, " Exception "+ str(e.message)
    if ok>0 and fail>0: return 0, return_dict
    elif fail==0 :      return 1, return_dict
    else:               return -1, return_dict

def get_del_recursive(url, what, url_suffix, force=False, recursive=False):
    #print
    #print " get", what, a, "     >>>>>>>> ",
    r,c = get_elements(url + what + 's' + url_suffix)
    if r<0:
        print c, "when getting", what, url_suffix
        return -1 
    #    print "ok"

    list_todelete = c.get(what, None)
    if list_todelete is None: list_todelete = c.get(what+'s', None)
    if list_todelete is None:
        print " Internal error, not found '" + what +"[s]' in", c
        return -3,  " Internal error, not found a valid dictionary"
    if type(list_todelete) == dict:
        list_todelete = (list_todelete, )
    
    if len(list_todelete)==0:
        print what, url_suffix, "not found"
        return 1
    for c in list_todelete:
        uuid=c.get('id', None)
        if uuid is None:
            uuid=c.get('uuid', None)
        if uuid is None:
            print "Id not found"
            continue
        name = c.get("name","")
        if recursive:
            if what=='tenant' :
                get_del_recursive(url + uuid + "/", 'server', "", force, recursive)
                get_del_recursive(url + uuid + "/", 'flavor', "", force, recursive)
                get_del_recursive(url + uuid + "/", 'image', "", force, recursive)
                get_del_recursive(url, 'network', "?tenant_id="+uuid, force, recursive)
            elif what=='flavors' :
                #get_del_recursive(url, 'servers', "?flavorRef="+uuid, force, recursive)
                pass
            elif what=='image' :
                get_del_recursive(url, 'server', "?imageRef="+uuid, force, recursive)
            elif what=='hosts' :
                get_del_recursive(url, 'server', "?hostId="+uuid, force, recursive)
                
        if not force:
            r = raw_input("Delete " + what + " " + uuid + " " + name + " (y/N)? ")
            if  len(r)>0  and r[0].lower()=="y":
                pass
            else:
                continue
        r,c = delete_elements(url + what + "s/" + uuid)
        if r<0:
            #print "Error deleting", vimURI, -r
            print c
        else:
            print what, uuid, name, "deleted"
    return 1

def check_valid_uuid(uuid):
    id_schema = {"type" : "string", "pattern": "^[a-fA-F0-9]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$"}
    try:
        js_v(uuid, id_schema)
        return True
    except js_e.ValidationError:
        return False

def change_string(text, var_list):
    end=0
    type_=None
    while True:
        ini = text.find("${", end)
        if ini<0: return text
        end = text.find("}", ini) 
        if end<0: return text
        end+=1
        
        var = text[ini:end]
        if ' ' in var:
            kk=var.split(" ")
            var=kk[0]+"}"
            type_=kk[-1][:-1]
        var = var_list.get(var, None)
        if var==None: return text
        
        text =  text[:ini] + var + text[end:]
        if type_ != None:
            if 'null' in type_ and text=="null":
                return None
            if 'int' in type_ : #and text.isnumeric():
                return int(text)
    return text

def chage_var_recursively(data, var_list):
    '''Check recursively the conent of data, and look for "*${*}*" variables and changes  
    It assumes that this variables are not in the key of dictionary,
    Attributes:
        'data': dictionary, or list. None or empty is consideted valid
        'var_list': dictionary (name:change) pairs
    Return:
        None, data is modified
    '''
        
    if type(data) is dict:
        for k in data.keys():
            if type(data[k]) is dict or type(data[k]) is tuple or type(data[k]) is list:
                chage_var_recursively(data[k], var_list)
            elif type(data[k]) is str:
                data[k] = change_string(data[k], var_list)
    if type(data) is list:
        for k in range(0,len(data)):
            if type(data[k]) is dict or type(data[k]) is list:
                chage_var_recursively(data[k], var_list)
            elif type(data[k]) is str:
                data[k] = change_string(data[k], var_list)

def change_var(data):
    if type(data) is not dict:
        return -1, "Format error, not a object (dictionary)"
    if "${}" not in data:
        return 0, data

    var_list={}
    for var in data["${}"]:
        r = var.find("}",) + 1
        if r<=2 or var[:2] != '${':
            return -1, "Format error at '${}':" + var
        #change variables inside description text
        if "${" in var[r:]:
            var = var[:r] + change_string(var[r:], var_list)
        d_start = var.rfind("(",) + 1
        d_end   = var.rfind(")",) 
        if d_start>0 and d_end>=d_start:
            default = var[d_start:d_end]
        else: default=None
        v = raw_input(var[r:] + "? ")
        if v=="":
            if default != None:
                v = default
            else:
                v = raw_input("  empty string? try again: ")
        var_list[ var[:r] ] = str(v) 
    
    del data["${}"]
    chage_var_recursively(data, var_list)
    return 0, data

def parse_yaml_json(text):
    try:
        data = yaml.load(text)
        return 0, data
    except yaml.YAMLError, exc:
        error_pos = ""
        if hasattr(exc, 'problem_mark'):
            mark = exc.problem_mark
            error_pos = " at position: (%s:%s)" % (mark.line+1, mark.column+1)
        return -1, " Error yaml/json format error at " + error_pos

def load_file(file_, parse=False):
    try:
        f = open(file_, 'r')
        read_data = f.read()
        f.close()
        if not parse:
            return 0, read_data
    except IOError, e:
        return -1, " Error opening file '" + file_ + "': " + e.args[1]
    
    try:
        data = yaml.load(read_data)
        return change_var(data)
    except yaml.YAMLError, exc:
        error_pos = ""
        if hasattr(exc, 'problem_mark'):
            mark = exc.problem_mark
            error_pos = " at position: (%s:%s)" % (mark.line+1, mark.column+1)
        return -2, " Error yaml/json format error at '"+ file_ +"'"+error_pos

def load_configuration(configuration_file):
    default_tokens ={'http_port':8080, 'http_host':'localhost', 'test_mode':False, 'of_controller_nets_with_same_vlan':True}
    
    r, config = load_file(configuration_file, parse=True)
    if r < 0:
        return False, config

    #Check default values tokens
    for k,v in default_tokens.items():
        if k not in config: config[k]=v
    
    return (True, config)

items_list = ('server','host','tenant','image','flavor','network','port')
action_list = ('list','get','new','del','edit','action')


def usage(complete=False):
    global items_list
    global action_list
    print "Usage: ", sys.argv[0], "[options]", " [" + ",".join(action_list) +"] ", "<item>   [<other>] "
    print "   Perform an test action over openvim"
    print "      "+",".join(action_list)+": List (by default), GET detais, Creates, Deletes, Edit"
    print "      <item>: can be one of " + ",".join(items_list)
    print "      <other>: list of uuid|name for 'get|del'; list of json/yaml files for 'new' or 'edit'"
    if not complete:
        print "   Type -h or --help for a complete list of options"
        return
    print "   Options:"
    print "      -v|--version: prints current version"
    print "      -c|--config [configuration_file]: loads the configuration file (default: openvimd.cfg)"
    print "      -h|--help: shows this help"
    print "      -u|--url [URL]: url to use instead of the one loaded from configuration file"
    print "      -t|--tenant [tenant uuid]: tenant to be used for some comands. IF mising it will use the default obtained in configuration file"
    print "      -F|--filter [A=B[&C=D...]: URL query string used for 'get' or 'del' commands"
    print "      -f|--force : Do not ask for confirmation when deleting. Also remove dependent objects."
    print "      -r|--recursive : Delete also dependency elements, (from tenants: images, flavors,server; from hosts: instances; ..."
    print "   Examples:"
    print "     ",sys.argv[0]," tenant                                #list tenants "
    print "     ",sys.argv[0]," -F'device_owner=external' get port    #get details of all external ports"
    print "     ",sys.argv[0]," del server ses pan                    #delete server names 'ses' and 'pan'. Do not ask for confirmation"
    print "     ",sys.argv[0]," -r -f del host                        #delete all host and all the dependencies "
    print "     ",sys.argv[0]," new host ./Host/nfv100.json           #add a host which information is in this file"
    print "     ",sys.argv[0]," edit network f348faf8-59ef-11e4-b4c7-52540030594e  '{\"network\":{\"admin_state_up\":false}}'"
    print "                             #change the admin status of this network"
    return


if __name__=="__main__":
    global vimURI
    global vimURI_admin
    
    global what
    global query_string
#init variables    
    action="list"
    what=None
    url=None
    query_string = ""
    force = False
    recursive = False
    tenant = None
    additional = []
    #look for parent dir
    config_file = '../openvimd.cfg'
    pos = sys.argv[0].rfind("/")
    if pos<0:
        base_dir="./"
    else:
        base_dir = sys.argv[0] [:pos+1]
    if pos>=0:
        config_file = base_dir + config_file

#get params    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvrfc:u:t:F:", 
            ["config", "help", "version", "force", "filter","tenant","url","recursive"])
    except getopt.GetoptError, err:
        print " Error:", err # will print something like "option -a not recognized"
        usage()
        sys.exit(-2)

    for o, a in opts:
        if o in ("-v", "--version"):
            print "test_openvim version", version, "Oct 2014"
            print "(c) Copyright Telefonica"
            sys.exit(0)
        elif o in ("-h", "--help"):
            usage(True)
            sys.exit(0)
        elif o in ("-c", "--config"):  config_file = a
        elif o in ("-f", "--force"):   force = True
        elif o in ("-r", "--recursive"):   recursive = True
        elif o in ("-F", "--filter"):  query_string = "?"+a
        elif o in ("-u", "--url"):     url = a
        elif o in ("-t", "--tenant"):  tenant = a
        else:
            assert False, "Unhandled option"

    for a in args:
        if len(a) == 0:
            print " Warning!!! Found an empty parameter?"
        elif a[0]=="-":
            print " Error!!! Put options parameter at the beginning"
            sys.exit(-2)
        elif what is not None:
            additional.append(a)
        elif a in items_list:
            what=a
        elif a[:-1] in items_list and a[-1]=='s':
            what=a[:-1]
        elif a in action_list:
            action=a
        else:
            print " Missing <item>", ",".join(items_list)
            sys.exit(-2)
    if what is None:
        usage()
        sys.exit(-1)
    #Load configuration file
    r, config_dic = load_configuration(config_file)
    #print config_dic
    if not r:
        print config_dic
        config_dic={}
        #exit(-1)
        
    #override parameters obtained by command line
    try:
        if url is not None:
            vimURI = vimURI_admin = url
        else:
            vimURI = "http://" + config_dic['http_host'] +":"+ str(config_dic['http_port']) + "/openvim/"
            if 'http_admin_port' in config_dic:
                vimURI_admin = "http://" + config_dic['http_host'] +":"+ str(config_dic['http_admin_port']) + "/openvim/"
    except: #key error 
        print " Error: can not get URL; neither option --u,-url, nor reading configuration file"
        exit(-1)
    if tenant is None:
        tenant = config_dic.get('tenant_id', None)
    
#check enough parameters
    URI=vimURI
    if (what in ('host','port') and action in ('del','new')) or (what=='host' and action=='edit' ):
        if vimURI_admin is None:
            print " Error: Can not get admin URL; neither option -t,--tenant, nor reading configuration file"
            exit(-1)
        else:
            URI=vimURI_admin
    if URI[-1] != "/": URI+="/"
    if what in ('server','image','flavor'):
        if tenant is None:
            print " Error: Can not get tenant; neither option -t,--tenant, nor reading configuration file"
            exit(-1)
        URI += tenant + "/"
    
    
    exit_code=0
    try:
#load file for new/edit
        payload_list=[]
        if action=='new' or action=='edit' or action=='action':
            if len(additional)==0:
                if action=='new' : 
                    additional.append(base_dir+what+"s/new_"+what+".yaml")
                    #print " New what? Missing additional parameters to complete action"
                else:
                    print " What must be edited? Missing additional parameters to complete action"
                    exit(-1)
            if action=='edit'or action=='action':
                #obtain only last element
                additional_temp = additional[:-1]
                additional = additional[-1:]
                
            for a in additional:
                r,payload = load_file(a, parse=True)
                if r<0:
                    if r==-1 and "{" in a or ":" in a:
                        #try to parse directly
                        r,payload = parse_yaml_json(a)
                        if r<0:
                            print payload
                            exit (-1)
                    else:
                        print payload
                        exit (-1)
                payload_list.append(payload)
            if action=='edit'or action=='action':
                additional = additional_temp

                
#perform actions NEW
        if action=='new':
            for payload in payload_list:
                print "\n new", what, a, "     >>>>>>>> ",
                r,c = new_elements(URI+what+'s', payload)
                if r>0:
                    print "ok"
                else:
                    print "fail"
                    exit_code = -1
                print c
                #try to decode
            exit(exit_code)
            
    #perform actions GET LIST EDIT DEL
        if len(additional)==0:
            additional=[""]
        for a in additional:
            filter_qs = query_string 
            if a != "" :
                if check_valid_uuid(a):
                    if len(filter_qs) > 0:  filter_qs += "&" + "id=" + str(a)
                    else:                   filter_qs += "?" + "id=" + str(a)
                else:
                    if len(filter_qs) > 0:  filter_qs += "&" + "name=" + str(a)
                    else:                   filter_qs += "?" + "name=" + str(a)

            if action=='list' or action=='get' or action=='edit'or action=='action':
                url = URI + what+'s'
                print url + filter_qs
                #print " get", what, a, "     >>>>>>>> ",
                r,c = get_elements(url + filter_qs)
                if r<0:              
                    #print "fail"
                    exit_code = -1
                    print c
                else:             
                    #print "ok"
                    if action=='list':
                        print json.dumps(c, indent=4)
                        continue
                    
                    if action=='get':
                        r1,c1 = get_details(url, what, c)
                    elif action=='action':
                        r1,c1 = action_details(url, what, c, force, payload_list[0])
                    else: # action=='edit':
                        r1,c1 = edit_details(url, what, c, force, payload_list[0])
                    if r1<0:              
                        exit_code = -1
                    else:             
                        if r>0: print "ok"
                        else: print "ok with some fails"
                    print json.dumps(c1, indent=4)

            elif action=='del':
                r = get_del_recursive(URI, what, filter_qs, force, recursive)
                if r<0:              
                    exit_code = -1
        exit(exit_code)
            
    except KeyboardInterrupt:
        print " Canceled"
    


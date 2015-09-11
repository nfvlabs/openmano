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
This is the thread for the http server North API. 
Two thread will be launched, with normal and administrative permissions.
'''

__author__="Alfonso Tierno"
__date__ ="$10-jul-2014 12:07:15$"

import bottle
import yaml
import json
import threading
import datetime
from utils import RADclass
from jsonschema import validate as js_v, exceptions as js_e
import host_thread as ht
from vim_schema import host_new_schema, host_edit_schema, tenant_new_schema, \
    tenant_edit_schema, \
    flavor_new_schema, flavor_update_schema, \
    image_new_schema, image_update_schema, \
    server_new_schema, server_action_schema, network_new_schema, network_update_schema, \
    port_new_schema, port_update_schema

global my
global url_base
global config_dic

url_base="/openvim"

HTTP_Bad_Request =          400
HTTP_Unauthorized =         401 
HTTP_Not_Found =            404 
HTTP_Forbidden =            403
HTTP_Method_Not_Allowed =   405 
HTTP_Not_Acceptable =       406
HTTP_Request_Timeout =      408
HTTP_Conflict =             409
HTTP_Service_Unavailable =  503 
HTTP_Internal_Server_Error= 500 


def check_extended(extended, allow_net_attach=False):
    '''Makes and extra checking of extended input that cannot be done using jsonschema
    Attributes: 
        allow_net_attach:  for allowing or not the uuid field at interfaces
        that are allowed for instance, but not for flavors
    Return: (<0, error_text) if error; (0,None) if not error '''
    if "numas" not in extended: return 0, None
    id_s=[]
    numaid=0
    for numa in extended["numas"]:
        nb_formats = 0
        if "cores" in numa:
            nb_formats += 1
            if "cores-id" in numa:
                if len(numa["cores-id"]) != numa["cores"]:
                    return -HTTP_Bad_Request, "different number of cores-id (%d) than cores (%d) at numa %d" % (len(numa["cores-id"]), numa["cores"],numaid)
                id_s.extend(numa["cores-id"])
        if "threads" in numa:
            nb_formats += 1
            if "threads-id" in numa:
                if len(numa["threads-id"]) != numa["threads"]:
                    return -HTTP_Bad_Request, "different number of threads-id (%d) than threads (%d) at numa %d" % (len(numa["threads-id"]), numa["threads"],numaid) 
                id_s.extend(numa["threads-id"])
        if "paired-threads" in numa:
            nb_formats += 1
            if "paired-threads-id" in numa:
                if len(numa["paired-threads-id"]) != numa["paired-threads"]:
                    return -HTTP_Bad_Request, "different number of paired-threads-id (%d) than paired-threads (%d) at numa %d" % (len(numa["paired-threads-id"]), numa["paired-threads"],numaid) 
                for pair in numa["paired-threads-id"]:
                    if len(pair) != 2:
                        return -HTTP_Bad_Request, "paired-threads-id must contain a list of two elements list at numa %d" % (numaid) 
                    id_s.extend(pair)
        if nb_formats > 1:
            return -HTTP_Service_Unavailable, "only one of cores, threads,  paired-threads are allowed in this version at numa %d" % numaid 
        #check interfaces
        if "interfaces" in numa:
            ifaceid=0
            names=[]
            vpcis=[]
            for interface in numa["interfaces"]:
                if "uuid" in interface and not allow_net_attach: 
                    return -HTTP_Bad_Request, "uuid field is not allowed at numa %d interface %s position %d" % (numaid, interface.get("name",""), ifaceid )
                if "mac_address" in interface and interface["dedicated"]=="yes":
                    return -HTTP_Bad_Request, "mac_address can not be set for dedicated (passthrough) at numa %d, interface %s position %d" % (numaid, interface.get("name",""), ifaceid )
                if "name" in interface:
                    if interface["name"] in names:
                        return -HTTP_Bad_Request, "name repeated at numa %d, interface %s position %d" % (numaid, interface.get("name",""), ifaceid )
                    names.append(interface["name"])
                if "vpci" in interface:
                    if interface["vpci"] in vpcis:
                        return -HTTP_Bad_Request, "vpci %s repeated at numa %d, interface %s position %d" % (interface["vpci"], numaid, interface.get("name",""), ifaceid )
                    vpcis.append(interface["vpci"])
                ifaceid+=1
        numaid+=1
    if numaid > 1:
        return -HTTP_Service_Unavailable, "only one numa can be defined in this version " 
    for a in range(0,len(id_s)):
        if a not in id_s:
            return -HTTP_Bad_Request, "core/thread identifiers must start at 0 and gaps are not alloed. Missing id number %d" % a 
    
    return 0, None

#
# dictionaries that change from HTTP API to database naming
#
http2db_host={'id':'uuid'}
http2db_tenant={'id':'uuid'}
http2db_flavor={'id':'uuid','imageRef':'image_id'}
http2db_image={'id':'uuid', 'created':'created_at', 'updated':'modified_at', 'public': 'public'}
http2db_server={'id':'uuid','hostId':'host_id','flavorRef':'flavor_id','imageRef':'image_id','created':'created_at'}
http2db_network={'id':'uuid','provider:vlan':'vlan', 'provider:physical': 'bind'}
http2db_port={'id':'uuid', 'network_id':'net_id', 'mac_address':'mac', 'device_owner':'type','device_id':'instance_id','binding:switch_port':'switch_port','binding:vlan':'vlan', 'bandwidth':'Mbps'}

def remove_extra_items(data, schema):
    deleted=[]
    if type(data) is tuple or type(data) is list:
        for d in data:
            a= remove_extra_items(d, schema['items'])
            if a is not None: deleted.append(a)
    elif type(data) is dict:
        for k in data.keys():
            if 'properties' not in schema or k not in schema['properties'].keys():
                del data[k]
                deleted.append(k)
            else:
                a = remove_extra_items(data[k], schema['properties'][k])
                if a is not None:  deleted.append({k:a})
    if len(deleted) == 0: return None
    elif len(deleted) == 1: return deleted[0]
    else: return deleted
                
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


class httpserver(threading.Thread):
    def __init__(self, db_conn, name="http", host='localhost', port=8080, admin=False, config_=None):
        '''
        Creates a new thread to attend the http connections
        Attributes:
            db_conn: database connection
            name: name of this thread
            host: ip or name where to listen
            port: port where to listen
            admin: if this has privileges of administrator or not 
            config_: unless the first thread must be provided. It is a global dictionary where to allocate the self variable 
        '''
        global url_base
        global config_dic
        
        #initialization
        if config_ is not None:
            config_dic = config_
        if 'http_threads' not in config_dic:
            config_dic['http_threads'] = {}
        threading.Thread.__init__(self)
        self.host = host
        self.port = port  
        self.db = db_conn
        self.admin = admin
        if name in config_dic:
            print "httpserver Warning!!! Onether thread with the same name", name
            n=0
            while name+str(n) in config_dic:
                n +=1
            name +=str(n)
        self.name = name
        self.url_preffix = 'http://' + self.host + ':' + str(self.port) + url_base
        config_dic['http_threads'][name] = self

        #Ensure that when the main program exits the thread will also exit
        self.daemon = True      
        self.setDaemon(True)
         
    def run(self):
        bottle.run(host=self.host, port=self.port, debug=True) #quiet=True
           
    def gethost(self, host_id):
        result, content = self.db.get_host(host_id)
        if result < 0:
            print "httpserver.gethost error %d %s" % (result, content)
            bottle.abort(-result, content)
        elif result==0:
            print "httpserver.gethost host '%s' not found" % host_id
            bottle.abort(HTTP_Not_Found, content)
        else:
            data={'host' : content}
            convert_boolean(content, ('admin_state_up',) )
            change_keys_http2db(content, http2db_host, reverse=True)
            print data['host']
            return format_out(data)

@bottle.route(url_base + '/', method='GET')
def http_get():
    print 
    return 'works' #TODO: put links or redirection to /openvim???

#
# Util funcions
#

def change_keys_http2db(data, http_db, reverse=False):
    '''Change keys of dictionary data according to the key_dict values
    This allow change from http interface names to database names.
    When reverse is True, the change is otherwise
    Attributes:
        data: can be a dictionary or a list
        http_db: is a dictionary with hhtp names as keys and database names as value
        reverse: by default change is done from http API to database. If True change is done otherwise
    Return: None, but data is modified'''
    if type(data) is tuple or type(data) is list:
        for d in data:
            change_keys_http2db(d, http_db, reverse)
    elif type(data) is dict or type(data) is bottle.FormsDict:
        if reverse:
            for k,v in http_db.items():
                if v in data: data[k]=data.pop(v)
        else:
            for k,v in http_db.items():
                if k in data: data[v]=data.pop(k)



def format_out(data):
    '''return string of dictionary data according to requested json, yaml, xml. By default json'''
    if 'application/yaml' in bottle.request.headers.get('Accept'):
        bottle.response.content_type='application/yaml'
        return yaml.safe_dump(data, explicit_start=True, indent=4, default_flow_style=False, tags=False, encoding='utf-8', allow_unicode=True) #, canonical=True, default_style='"'
    else: #by default json
        bottle.response.content_type='application/json'
        #return data #json no style
        return json.dumps(data, indent=4) + "\n"

def format_in(schema):
    try:
        format_type = bottle.request.headers.get('Content-Type', 'application/json')
        if 'application/json' in format_type:
            client_data = bottle.request.json
        elif 'application/yaml' in format_type:
            client_data = yaml.load(bottle.request.body)
        elif format_type == 'application/xml':
            bottle.abort(501, "Content-Type: application/xml not supported yet.")
        else:
            print "HTTP HEADERS: " + str(bottle.request.headers.items())
            bottle.abort(HTTP_Not_Acceptable, 'Content-Type ' + str(format_type) + ' not supported.')
            return
        #if client_data == None:
        #    bottle.abort(HTTP_Bad_Request, "Content error, empty")
        #    return
        #check needed_items

        #print "HTTP input data: ", str(client_data)
        js_v(client_data, schema)

        return client_data
    except yaml.YAMLError, exc:
        print "HTTP validate_in error, yaml exception ", exc
        print "  CONTENT: " + str(bottle.request.body.readlines())
        error_pos = ""
        if hasattr(exc, 'problem_mark'):
            mark = exc.problem_mark
            error_pos = " at position: (%s:%s)" % (mark.line+1, mark.column+1)
        bottle.abort(HTTP_Bad_Request, "Content error: Failed to parse Content-Type",  error_pos)
    except ValueError, exc:
        print "HTTP validate_in error, ValueError exception ", exc
        print "  CONTENT: " + str(bottle.request.body.readlines())
        bottle.abort(HTTP_Bad_Request, "invalid format: "+str(exc))
    except js_e.ValidationError, exc:
        print "HTTP validate_in error, jsonschema exception ", exc.message, "at", exc.path
        print "  CONTENT: " + str(bottle.request.body.readlines())
        error_pos = ""
        if len(exc.path)>0: error_pos=" at '" +  ":".join(map(str, exc.path)) + "'"
        bottle.abort(HTTP_Bad_Request, "invalid format"+error_pos+": "+exc.message)
    #except:
    #    bottle.abort(HTTP_Bad_Request, "Content error: Failed to parse Content-Type",  error_pos)
    #    raise

def filter_query_string(qs, http2db, allowed):
    '''Process query string (qs) checking that contains only valid tokens for avoiding SQL injection
    Attributes:
        'qs': bottle.FormsDict variable to be processed. None or empty is considered valid
        'allowed': list of allowed string tokens (API http naming). All the keys of 'qs' must be one of 'allowed'
        'http2db': dictionary with change from http API naming (dictionary key) to database naming(dictionary value)
    Return: A tuple with the (select,where,limit) to be use in a database query. All of then transformed to the database naming
        select: list of items to retrieve, filtered by query string 'field=token'. If no 'field' is present, allowed list is returned
        where: dictionary with key, value, taken from the query string token=value. Empty if nothing is provided
        limit: limit dictated by user with the query string 'limit'. 100 by default
    abort if not permitted, using bottel.abort
    '''
    where={}
    limit=100
    select=[]
    if type(qs) is not bottle.FormsDict:
        print '!!!!!!!!!!!!!!invalid query string not a dictionary'
        #bottle.abort(HTTP_Internal_Server_Error, "call programmer")
    else:
        for k in qs:
            if k=='field':
                select += qs.getall(k)
                for v in select:
                    if v not in allowed:
                        bottle.abort(HTTP_Bad_Request, "Invalid query string at 'field="+v+"'")
            elif k=='limit':
                try:
                    limit=int(qs[k])
                except:
                    bottle.abort(HTTP_Bad_Request, "Invalid query string at 'limit="+qs[k]+"'")
            else:
                if k not in allowed:
                    bottle.abort(HTTP_Bad_Request, "Invalid query string at '"+k+"="+qs[k]+"'")
                if qs[k]!="null":  where[k]=qs[k]
                else: where[k]=None 
    if len(select)==0: select += allowed
    #change from http api to database naming
    for i in range(0,len(select)):
        k=select[i]
        if k in http2db: 
            select[i] = http2db[k]
    change_keys_http2db(where, http2db)
    #print "filter_query_string", select,where,limit
    
    return select,where,limit


def convert_bandwidth(data, reverse=False):
    '''Check the field bandwidth recursively and when found, it removes units and convert to number 
    It assumes that bandwidth is well formed
    Attributes:
        'data': dictionary bottle.FormsDict variable to be checked. None or empty is considered valid
        'reverse': by default convert form str to int (Mbps), if True it convert from number to units
    Return:
        None
    '''
    if type(data) is dict:
        for k in data.keys():
            if type(data[k]) is dict or type(data[k]) is tuple or type(data[k]) is list:
                convert_bandwidth(data[k], reverse)
        if "bandwidth" in data:
            try:
                value=str(data["bandwidth"])
                if not reverse:
                    pos = value.find("bps")
                    if pos>0:
                        if value[pos-1]=="G": data["bandwidth"] =  int(data["bandwidth"][:pos-1]) * 1000
                        elif value[pos-1]=="k": data["bandwidth"]= int(data["bandwidth"][:pos-1]) / 1000
                        else: data["bandwidth"]= int(data["bandwidth"][:pos-1])
                else:
                    value = int(data["bandwidth"])
                    if value % 1000 == 0: data["bandwidth"]=str(value/1000) + " Gbps"
                    else: data["bandwidth"]=str(value) + " Mbps"
            except:
                print "convert_bandwidth exception for type", type(data["bandwidth"]), " data", data["bandwidth"]
                return
    if type(data) is tuple or type(data) is list:
        for k in data:
            if type(k) is dict or type(k) is tuple or type(k) is list:
                convert_bandwidth(k, reverse)

def convert_boolean(data, items):
    '''Check recursively the content of data, and if there is an key contained in items, convert value from string to boolean 
    It assumes that bandwidth is well formed
    Attributes:
        'data': dictionary bottle.FormsDict variable to be checked. None or empty is consideted valid
        'items': tuple of keys to convert
    Return:
        None
    '''
    if type(data) is dict:
        for k in data.keys():
            if type(data[k]) is dict or type(data[k]) is tuple or type(data[k]) is list:
                convert_boolean(data[k], items)
            if k in items:
                if type(data[k]) is str:
                    if   data[k]=="false": data[k]=False
                    elif data[k]=="true":  data[k]=True
    if type(data) is tuple or type(data) is list:
        for k in data:
            if type(k) is dict or type(k) is tuple or type(k) is list:
                convert_boolean(k, items)

def convert_datetime2str(var):
    '''Converts a datetime variable to a string with the format '%Y-%m-%dT%H:%i:%s'
    It enters recursively in the dict var finding this kind of variables
    '''
    if type(var) is dict:
        for k,v in var.items():
            if type(v) is datetime.datetime:
                var[k]= v.strftime('%Y-%m-%dT%H:%M:%S')
            elif type(v) is dict or type(v) is list or type(v) is tuple: 
                convert_datetime2str(v)
        if len(var) == 0: return True
    elif type(var) is list or type(var) is tuple:
        for v in var:
            convert_datetime2str(v)

def check_valid_tenant(my, tenant_id):
    if tenant_id=='any':
        if not my.admin:
            return HTTP_Unauthorized, "Needed admin privileges"
    else:
        result, _ = my.db.get_table(FROM='tenants', SELECT=('uuid',), WHERE={'uuid': tenant_id})
        if result<=0:
            return HTTP_Not_Found, "tenant '%s' not found" % tenant_id
    return 0, None


@bottle.error(400)
@bottle.error(401) 
@bottle.error(404) 
@bottle.error(403)
@bottle.error(405) 
@bottle.error(406)
@bottle.error(409)
@bottle.error(503) 
@bottle.error(500)
def error400(error):
    e={"error":{"code":error.status_code, "type":error.status, "description":error.body}}
    return format_out(e)

@bottle.hook('after_request')
def enable_cors():
    #TODO: Alf: Is it needed??
    bottle.response.headers['Access-Control-Allow-Origin'] = '*'

#
# HOSTS
#

@bottle.route(url_base + '/hosts', method='GET')
def http_get_hosts():
    select_,where_,limit_ = filter_query_string(bottle.request.query, http2db_host,
            ('id','name','description','status','admin_state_up') )
    
    myself = config_dic['http_threads'][ threading.current_thread().name ]
    result, content = myself.db.get_table(FROM='hosts', SELECT=select_, WHERE=where_, LIMIT=limit_)
    if result < 0:
        print "http_get_hosts Error", content
        bottle.abort(-result, content)
    else:
        convert_boolean(content, ('admin_state_up',) )
        change_keys_http2db(content, http2db_host, reverse=True)
        for row in content:
            row['links'] = ( {'href': myself.url_preffix + '/hosts/' + str(row['id']), 'rel': 'bookmark'}, )
        data={'hosts' : content}
        return format_out(data)

@bottle.route(url_base + '/hosts/<host_id>', method='GET')
def http_get_host_id(host_id):
    my = config_dic['http_threads'][ threading.current_thread().name ]
    return my.gethost(host_id)

@bottle.route(url_base + '/hosts', method='POST')
def http_post_hosts():
    '''insert a host into the database. All resources are got and inserted'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check permissions
    if not my.admin:
        bottle.abort(HTTP_Unauthorized, "Needed admin privileges")
    
    #parse input data
    http_content = format_in( host_new_schema )
    r = remove_extra_items(http_content, host_new_schema)
    if r is not None: print "http_post_host_id: Warning: remove extra items ", r
    change_keys_http2db(http_content['host'], http2db_host)

    host = http_content['host']
    warning_text=""
    if 'host-data' in http_content:
        host.update(http_content['host-data'])
        ip_name=http_content['host-data']['ip_name']
        user=http_content['host-data']['user']
        password=http_content['host-data'].get('password', None)
    else:
        ip_name=host['ip_name']
        user=host['user']
        password=host.get('password', None)

        #fill rad info
        rad = RADclass.RADclass()
        (return_status, code) = rad.obtain_RAD(user, password, ip_name)
        
        #return 
        if not return_status:
            print 'http_post_hosts ERROR obtaining RAD', code
            bottle.abort(HTTP_Bad_Request, code)
            return
        warning_text=code
        rad_structure = yaml.load(rad.to_text())
        print 'rad_structure\n---------------------'
        print json.dumps(rad_structure, indent=4)
        print '---------------------'
        #return
        WHERE_={"family":rad_structure['processor']['family'], 'manufacturer':rad_structure['processor']['manufacturer'], 'version':rad_structure['processor']['version']} 
        result, content = my.db.get_table(FROM='host_ranking', 
                    SELECT=('ranking',),
                    WHERE=WHERE_)
        if result > 0:
            host['ranking'] = content[0]['ranking']
        else:
            #error_text= "Host " + str(WHERE_)+ " not found in ranking table. Not valid for VIM management"
            #bottle.abort(HTTP_Bad_Request, error_text)
            #return
            warning_text += "Host " + str(WHERE_)+ " not found in ranking table. Assuming lowest value 100\n"
            host['ranking'] = 100 #TODO: as not used in this version, set the lowest value
    
        features = rad_structure['processor'].get('features', ())
        host['features'] = ",".join(features)
        host['numas'] = [] 
        
        for node in rad_structure['resource topology']['nodes'].itervalues():
            interfaces= []
            cores = []
            eligible_cores=[]
            count = 0
            for core in node['cpu']['eligible_cores']:
                eligible_cores.extend(core)
            for core in node['cpu']['cores']:
                c={'core_id': count, 'thread_id':core[0]}
                if core[0] not in eligible_cores: c['status'] = 'noteligible'
                cores.append(c)
                c={'core_id': count, 'thread_id':core[1]}
                if core[1] not in eligible_cores: c['status'] = 'noteligible'
                cores.append(c)
                count = count+1 

            if 'nics' in node:    
                for port_k, port_v in node['nics']['nic 0']['ports'].iteritems():
                    if port_v['virtual']:
                        continue
                    else:
                        sriovs = []
                        for port_k2, port_v2 in node['nics']['nic 0']['ports'].iteritems():
                            if port_v2['virtual'] and port_v2['PF_pci_id']==port_k:
                                sriovs.append({'pci':port_k2, 'mac':port_v2['mac'], 'source_name':port_v2['source_name']})
                        if len(sriovs)>0:
                            #sort sriov according to pci and rename them to the vf number
                            new_sriovs = sorted(sriovs, key=lambda k: k['pci'])
                            index=0 
                            for sriov in new_sriovs:
                                sriov['source_name'] = index
                                index += 1
                            interfaces.append  ({'pci':str(port_k), 'Mbps': port_v['speed']/1000000, 'sriovs': new_sriovs, 'mac':port_v['mac'], 'source_name':port_v['source_name']})
            #@TODO LA memoria devuelta por el RAD es incorrecta, almenos para IVY1, NFV100
            memory=node['memory']['node_size'] / (1024*1024*1024)
            #memory=get_next_2pow(node['memory']['hugepage_nr'])
            host['numas'].append( {'numa_socket': node['id'], 'hugepages': node['memory']['hugepage_nr'], 'memory':memory, 'interfaces': interfaces, 'cores': cores } )
    print json.dumps(host, indent=4)
    #return
    #
    #insert in data base
    result, content = my.db.new_host(host)
    if result >= 0:
        if content['admin_state_up']:
            #create thread
            host_test_mode = True if config_dic['mode']=='test' or config_dic['mode']=="OF only" else False
            host_develop_mode = True if config_dic['mode']=='development' else False
            host_develop_bridge_iface = config_dic.get('development_bridge', None)
            thread = ht.host_thread(name=host.get('name',ip_name), user=user, host=ip_name, db=config_dic['db'], db_lock=config_dic['db_lock'], 
                test=host_test_mode, image_path=config_dic['image_path'],
                version=config_dic['version'], host_id=content['uuid'],
                develop_mode=host_develop_mode, develop_bridge_iface=host_develop_bridge_iface   )
            thread.start()
            config_dic['host_threads'][ content['uuid'] ] = thread

        #return host data
        change_keys_http2db(content, http2db_host, reverse=True)
        if len(warning_text)>0:
            content["warning"]= warning_text
        data={'host' : content}
        return format_out(data)
    else:
        bottle.abort(HTTP_Bad_Request, content)
        return

@bottle.route(url_base + '/hosts/<host_id>', method='PUT')
def http_put_host_id(host_id):
    '''modify a host into the database. All resources are got and inserted'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check permissions
    if not my.admin:
        bottle.abort(HTTP_Unauthorized, "Needed admin privileges")
    
    #parse input data
    http_content = format_in( host_edit_schema )
    r = remove_extra_items(http_content, host_edit_schema)
    if r is not None: print "http_post_host_id: Warning: remove extra items ", r
    change_keys_http2db(http_content['host'], http2db_host)

    #insert in data base
    result, content = my.db.edit_host(host_id, http_content['host'])
    if result >= 0:
        convert_boolean(content, ('admin_state_up',) )
        change_keys_http2db(content, http2db_host, reverse=True)
        data={'host' : content}

        #reload thread
        config_dic['host_threads'][host_id].name = content.get('name',content['ip_name'])
        config_dic['host_threads'][host_id].user = content['user']
        config_dic['host_threads'][host_id].host = content['ip_name']
        config_dic['host_threads'][host_id].insert_task("reload")

        #print data
        return format_out(data)
    else:
        bottle.abort(HTTP_Bad_Request, content)
        return



@bottle.route(url_base + '/hosts/<host_id>', method='DELETE')
def http_delete_host_id(host_id):
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check permissions
    if not my.admin:
        bottle.abort(HTTP_Unauthorized, "Needed admin privileges")
    result, content = my.db.delete_row('hosts', host_id)
    if result == 0:
        bottle.abort(HTTP_Not_Found, content)
    elif result >0:
        #terminate thread
        if host_id in config_dic['host_threads']:
            config_dic['host_threads'][host_id].insert_task("exit")
        #return data
        data={'result' : content}
        return format_out(data)
    else:
        print "http_delete_host_id error",result, content
        bottle.abort(-result, content)
        return



#
# TENANTS
#

@bottle.route(url_base + '/tenants', method='GET')
def http_get_tenants():
    my = config_dic['http_threads'][ threading.current_thread().name ]
    select_,where_,limit_ = filter_query_string(bottle.request.query, http2db_tenant,
            ('id','name','description','enabled') )
    result, content = my.db.get_table(FROM='tenants', SELECT=select_,WHERE=where_,LIMIT=limit_)
    if result < 0:
        print "http_get_tenants Error", content
        bottle.abort(-result, content)
    else:
        change_keys_http2db(content, http2db_tenant, reverse=True)
        convert_boolean(content, ('enabled',))
        data={'tenants' : content}
        #data['tenants_links'] = dict([('tenant', row['id']) for row in content])
        return format_out(data)

@bottle.route(url_base + '/tenants/<tenant_id>', method='GET')
def http_get_tenant_id(tenant_id):
    my = config_dic['http_threads'][ threading.current_thread().name ]
    result, content = my.db.get_table(FROM='tenants', SELECT=('uuid','name','description', 'enabled'),WHERE={'uuid': tenant_id} )
    if result < 0:
        print "http_get_tenant_id error %d %s" % (result, content)
        bottle.abort(-result, content)
    elif result==0:
        print "http_get_tenant_id tenant '%s' not found" % tenant_id
        bottle.abort(HTTP_Not_Found, "tenant %s not found" % tenant_id)
    else:
        change_keys_http2db(content, http2db_tenant, reverse=True)
        convert_boolean(content, ('enabled',))
        data={'tenant' : content[0]}
        #data['tenants_links'] = dict([('tenant', row['id']) for row in content])
        return format_out(data)


@bottle.route(url_base + '/tenants', method='POST')
def http_post_tenants():
    '''insert a tenant into the database.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #parse input data
    http_content = format_in( tenant_new_schema )
    r = remove_extra_items(http_content, tenant_new_schema)
    if r is not None: print "http_post_tenants: Warning: remove extra items ", r
    change_keys_http2db(http_content['tenant'], http2db_tenant)

    #insert in data base
    result, content = my.db.new_tenant(http_content['tenant'])
            
    if result >= 0:
        return http_get_tenant_id(content)
    else:
        bottle.abort(-result, content)
        return
    
@bottle.route(url_base + '/tenants/<tenant_id>', method='PUT')
def http_put_tenant_id(tenant_id):
    '''update a tenant into the database.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #parse input data
    http_content = format_in( tenant_edit_schema )
    r = remove_extra_items(http_content, tenant_edit_schema)
    if r is not None: print "http_put_tenant_id: Warning: remove extra items ", r
    change_keys_http2db(http_content['tenant'], http2db_tenant)

    #insert in data base
    result, content = my.db.update_rows('tenants', http_content['tenant'], WHERE={'uuid': tenant_id}, log=True )
    if result >= 0:
        return http_get_tenant_id(tenant_id)
    else:
        bottle.abort(-result, content)
        return

@bottle.route(url_base + '/tenants/<tenant_id>', method='DELETE')
def http_delete_tenant_id(tenant_id):
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check permissions
    r, tenants_flavors = my.db.get_table(FROM='tenants_flavors', SELECT=('flavor_id','tenant_id'), WHERE={'tenant_id': tenant_id})
    if r<=0:
        tenants_flavors=()
    r, tenants_images  = my.db.get_table(FROM='tenants_images',  SELECT=('image_id','tenant_id'),  WHERE={'tenant_id': tenant_id})
    if r<=0:
        tenants_images=()
    result, content = my.db.delete_row('tenants', tenant_id)
    if result == 0:
        bottle.abort(HTTP_Not_Found, content)
    elif result >0:
        print "alf", tenants_flavors, tenants_images
        for flavor in tenants_flavors:
            my.db.delete_row_by_key("flavors", "uuid",  flavor['flavor_id'])
        for image in tenants_images:
            my.db.delete_row_by_key("images", "uuid",   image['image_id'])
        data={'result' : content}
        return format_out(data)
    else:
        print "http_delete_tenant_id error",result, content
        bottle.abort(-result, content)
        return

#
# FLAVORS
#

@bottle.route(url_base + '/<tenant_id>/flavors', method='GET')
def http_get_flavors(tenant_id):
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
    #obtain data
    select_,where_,limit_ = filter_query_string(bottle.request.query, http2db_flavor,
            ('id','name','description','public') )
    if tenant_id=='any':
        from_  ='flavors'
    else:
        from_  ='tenants_flavors inner join flavors on tenants_flavors.flavor_id=flavors.uuid'
        where_['tenant_id'] = tenant_id
    result, content = my.db.get_table(FROM=from_, SELECT=select_, WHERE=where_, LIMIT=limit_)
    if result < 0:
        print "http_get_flavors Error", content
        bottle.abort(-result, content)
    else:
        change_keys_http2db(content, http2db_flavor, reverse=True)
        for row in content:
            row['links']=[ {'href': "/".join( (my.url_preffix, tenant_id, 'flavors', str(row['id']) ) ), 'rel':'bookmark' } ]
        data={'flavors' : content}
        return format_out(data)

@bottle.route(url_base + '/<tenant_id>/flavors/<flavor_id>', method='GET')
def http_get_flavor_id(tenant_id, flavor_id):
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
    #obtain data
    select_,where_,limit_ = filter_query_string(bottle.request.query, http2db_flavor,
            ('id','name','description','ram', 'vcpus', 'extended', 'disk', 'public') )
    if tenant_id=='any':
        from_  ='flavors'
    else:
        from_  ='tenants_flavors as tf inner join flavors as f on tf.flavor_id=f.uuid'
        where_['tenant_id'] = tenant_id
    where_['uuid'] = flavor_id
    result, content = my.db.get_table(SELECT=select_, FROM=from_, WHERE=where_, LIMIT=limit_)

    if result < 0:
        print "http_get_flavor_id error %d %s" % (result, content)
        bottle.abort(-result, content)
    elif result==0:
        print "http_get_flavors_id flavor '%s' not found" % str(flavor_id)
        bottle.abort(HTTP_Not_Found, 'flavor %s not found' % flavor_id)
    else:
        change_keys_http2db(content, http2db_flavor, reverse=True)
        if 'extended' in content[0] and content[0]['extended'] is not None:
            extended = json.loads(content[0]['extended'])
            if 'devices' in extended: 
                change_keys_http2db(extended['devices'], http2db_flavor, reverse=True)
            content[0]['extended']=extended
        convert_bandwidth(content[0], reverse=True)
        content[0]['links']=[ {'href': "/".join( (my.url_preffix, tenant_id, 'flavors', str(content[0]['id']) ) ), 'rel':'bookmark' } ]
        data={'flavor' : content[0]}
        #data['tenants_links'] = dict([('tenant', row['id']) for row in content])
        return format_out(data)


@bottle.route(url_base + '/<tenant_id>/flavors', method='POST')
def http_post_flavors(tenant_id):
    '''insert a flavor into the database, and attach to tenant.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
    http_content = format_in( flavor_new_schema )
    r = remove_extra_items(http_content, flavor_new_schema)
    if r is not None: print "http_post_flavors: Warning: remove extra items ", r
    change_keys_http2db(http_content['flavor'], http2db_flavor)
    extended_dict = http_content['flavor'].pop('extended', None)
    if extended_dict is not None: 
        result, content = check_extended(extended_dict)
        if result<0:
            print "http_post_flavors wrong input extended error %d %s" % (result, content)
            bottle.abort(-result, content)
            return
        convert_bandwidth(extended_dict)
        if 'devices' in extended_dict: change_keys_http2db(extended_dict['devices'], http2db_flavor)
        http_content['flavor']['extended'] = json.dumps(extended_dict)
    #insert in data base
    result, content = my.db.new_flavor(http_content['flavor'], tenant_id)
    if result >= 0:
        return http_get_flavor_id(tenant_id, content)
    else:
        print "http_psot_flavors error %d %s" % (result, content)
        bottle.abort(-result, content)
        return
    
@bottle.route(url_base + '/<tenant_id>/flavors/<flavor_id>', method='DELETE')
def http_delete_flavor_id(tenant_id, flavor_id):
    '''Deletes the flavor_id of a tenant. IT removes from tenants_flavors table.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
        return
    result, content = my.db.delete_image_flavor('flavor', flavor_id, tenant_id)
    if result == 0:
        bottle.abort(HTTP_Not_Found, content)
    elif result >0:
        data={'result' : content}
        return format_out(data)
    else:
        print "http_delete_flavor_id error",result, content
        bottle.abort(-result, content)
        return

@bottle.route(url_base + '/<tenant_id>/flavors/<flavor_id>/<action>', method='POST')
def http_attach_detach_flavors(tenant_id, flavor_id, action):
    '''attach/detach an existing flavor in this tenant. That is insert/remove at tenants_flavors table.'''
    #TODO alf:  not tested at all!!!
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
    if tenant_id=='any':
        bottle.abort(HTTP_Bad_Request, "Invalid tenant 'any' with this command")
    #check valid action
    if action!='attach' and action != 'detach':
        bottle.abort(HTTP_Method_Not_Allowed, "actions can be attach or detach")
        return

    #Ensure that flavor exist 
    from_  ='tenants_flavors as tf right join flavors as f on tf.flavor_id=f.uuid'
    where_={'uuid': flavor_id}
    result, content = my.db.get_table(SELECT=('public','tenant_id'), FROM=from_, WHERE=where_)
    if result==0:
        if action=='attach':
            text_error="Flavor '%s' not found" % flavor_id
        else:
            text_error="Flavor '%s' not found for tenant '%s'" % (flavor_id, tenant_id)
        bottle.abort(HTTP_Not_Found, text_error)
        return
    elif result>0:
        flavor=content[0]
        if action=='attach':
            if flavor['tenant_id']!=None:
                bottle.abort(HTTP_Conflict, "Flavor '%s' already attached to tenant '%s'" % (flavor_id, tenant_id))
            if flavor['public']=='no' and not my.admin:
                #allow only attaching public flavors
                bottle.abort(HTTP_Unauthorized, "Needed admin rights to attach a private flavor")
                return
            #insert in data base
            result, content = my.db.new_row('tenants_flavors', {'flavor_id':flavor_id, 'tenant_id': tenant_id})
            if result >= 0:
                return http_get_flavor_id(tenant_id, flavor_id)
        else: #detach
            if flavor['tenant_id']==None:
                bottle.abort(HTTP_Not_Found, "Flavor '%s' not attached to tenant '%s'" % (flavor_id, tenant_id))
            result, content = my.db.delete_row_by_dict(FROM='tenants_flavors', WHERE={'flavor_id':flavor_id, 'tenant_id':tenant_id})
            if result>=0:
                if flavor['public']=='no':
                    #try to delete the flavor completely to avoid orphan flavors, IGNORE error
                    my.db.delete_row_by_dict(FROM='flavors', WHERE={'uuid':flavor_id})
                data={'result' : "flavor detached"}
                return format_out(data)
    
    #if get here is because an error
    print "http_attach_detach_flavors error %d %s" % (result, content)
    bottle.abort(-result, content)
    return

@bottle.route(url_base + '/<tenant_id>/flavors/<flavor_id>', method='PUT')
def http_put_flavor_id(tenant_id, flavor_id):
    '''update a flavor_id into the database.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
    #parse input data
    http_content = format_in( flavor_update_schema )
    r = remove_extra_items(http_content, flavor_update_schema)
    if r is not None: print "http_put_flavor_id: Warning: remove extra items ", r
    change_keys_http2db(http_content['flavor'], http2db_flavor)
    extended_dict = http_content['flavor'].pop('extended', None)
    if extended_dict is not None: 
        result, content = check_extended(extended_dict)
        if result<0:
            print "http_put_flavor_id wrong input extended error %d %s" % (result, content)
            bottle.abort(-result, content)
            return
        convert_bandwidth(extended_dict)
        if 'devices' in extended_dict: change_keys_http2db(extended_dict['devices'], http2db_flavor)
        http_content['flavor']['extended'] = json.dumps(extended_dict)
    #Ensure that flavor exist 
    where_={'uuid': flavor_id}
    if tenant_id=='any':
        from_  ='flavors'
    else:
        from_  ='tenants_flavors as ti inner join flavors as i on ti.flavor_id=i.uuid'
        where_['tenant_id'] = tenant_id
    result, content = my.db.get_table(SELECT=('public',), FROM=from_, WHERE=where_)
    if result==0:
        text_error="Flavor '%s' not found" % flavor_id
        if tenant_id!='any':
            text_error +=" for tenant '%s'" % flavor_id
        bottle.abort(HTTP_Not_Found, text_error)
        return
    elif result>0:
        if content[0]['public']=='yes' and not my.admin:
            #allow only modifications over private flavors
            bottle.abort(HTTP_Unauthorized, "Needed admin rights to edit a public flavor")
            return
        #insert in data base
        result, content = my.db.update_rows('flavors', http_content['flavor'], {'uuid': flavor_id})

    if result < 0:
        print "http_put_flavor_id error %d %s" % (result, content)
        bottle.abort(-result, content)
        return
    else:
        return http_get_flavor_id(tenant_id, flavor_id)



#
# IMAGES
#

@bottle.route(url_base + '/<tenant_id>/images', method='GET')
def http_get_images(tenant_id):
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
    #obtain data
    select_,where_,limit_ = filter_query_string(bottle.request.query, http2db_image,
            ('id','name','description','path','public') )
    if tenant_id=='any':
        from_  ='images'
    else:
        from_  ='tenants_images inner join images on tenants_images.image_id=images.uuid'
        where_['tenant_id'] = tenant_id
    result, content = my.db.get_table(SELECT=select_, FROM=from_, WHERE=where_, LIMIT=limit_)
    if result < 0:
        print "http_get_images Error", content
        bottle.abort(-result, content)
    else:
        change_keys_http2db(content, http2db_image, reverse=True)
        #for row in content: row['links']=[ {'href': "/".join( (my.url_preffix, tenant_id, 'images', str(row['id']) ) ), 'rel':'bookmark' } ]
        data={'images' : content}
        return format_out(data)

@bottle.route(url_base + '/<tenant_id>/images/<image_id>', method='GET')
def http_get_image_id(tenant_id, image_id):
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
    #obtain data
    select_,where_,limit_ = filter_query_string(bottle.request.query, http2db_image,
            ('id','name','description','progress', 'status','path', 'created', 'updated','public') )
    if tenant_id=='any':
        from_  ='images'
    else:
        from_  ='tenants_images as ti inner join images as i on ti.image_id=i.uuid'
        where_['tenant_id'] = tenant_id
    where_['uuid'] = image_id
    result, content = my.db.get_table(SELECT=select_, FROM=from_, WHERE=where_, LIMIT=limit_)

    if result < 0:
        print "http_get_images error %d %s" % (result, content)
        bottle.abort(-result, content)
    elif result==0:
        print "http_get_images image '%s' not found" % str(image_id)
        bottle.abort(HTTP_Not_Found, 'image %s not found' % image_id)
    else:
        convert_datetime2str(content)
        change_keys_http2db(content, http2db_image, reverse=True)
        if 'metadata' in content[0] and content[0]['metadata'] is not None:
            metadata = json.loads(content[0]['metadata'])
            content[0]['metadata']=metadata
        content[0]['links']=[ {'href': "/".join( (my.url_preffix, tenant_id, 'images', str(content[0]['id']) ) ), 'rel':'bookmark' } ]
        data={'image' : content[0]}
        #data['tenants_links'] = dict([('tenant', row['id']) for row in content])
        return format_out(data)

@bottle.route(url_base + '/<tenant_id>/images', method='POST')
def http_post_images(tenant_id):
    '''insert a image into the database, and attach to tenant.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
    http_content = format_in(image_new_schema)
    r = remove_extra_items(http_content, image_new_schema)
    if r is not None: print "http_post_images: Warning: remove extra items ", r
    change_keys_http2db(http_content['image'], http2db_image)
    metadata_dict = http_content['image'].pop('metadata', None)
    if metadata_dict is not None: 
        http_content['image']['metadata'] = json.dumps(metadata_dict)
    #insert in data base
    result, content = my.db.new_image(http_content['image'], tenant_id)
    if result >= 0:
        return http_get_image_id(tenant_id, content)
    else:
        print "http_post_images error %d %s" % (result, content)
        bottle.abort(-result, content)
        return
    
@bottle.route(url_base + '/<tenant_id>/images/<image_id>', method='DELETE')
def http_delete_image_id(tenant_id, image_id):
    '''Deletes the image_id of a tenant. IT removes from tenants_images table.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
    result, content = my.db.delete_image_flavor('image', image_id, tenant_id)
    if result == 0:
        bottle.abort(HTTP_Not_Found, content)
    elif result >0:
        data={'result' : content}
        return format_out(data)
    else:
        print "http_delete_image_id error",result, content
        bottle.abort(-result, content)
        return

@bottle.route(url_base + '/<tenant_id>/images/<image_id>/<action>', method='POST')
def http_attach_detach_images(tenant_id, image_id, action):
    '''attach/detach an existing image in this tenant. That is insert/remove at tenants_images table.'''
    #TODO alf:  not tested at all!!!
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
    if tenant_id=='any':
        bottle.abort(HTTP_Bad_Request, "Invalid tenant 'any' with this command")
    #check valid action
    if action!='attach' and action != 'detach':
        bottle.abort(HTTP_Method_Not_Allowed, "actions can be attach or detach")
        return

    #Ensure that image exist 
    from_  ='tenants_images as ti right join images as i on ti.image_id=i.uuid'
    where_={'uuid': image_id}
    result, content = my.db.get_table(SELECT=('public','tenant_id'), FROM=from_, WHERE=where_)
    if result==0:
        if action=='attach':
            text_error="Image '%s' not found" % image_id
        else:
            text_error="Image '%s' not found for tenant '%s'" % (image_id, tenant_id)
        bottle.abort(HTTP_Not_Found, text_error)
        return
    elif result>0:
        image=content[0]
        if action=='attach':
            if image['tenant_id']!=None:
                bottle.abort(HTTP_Conflict, "Image '%s' already attached to tenant '%s'" % (image_id, tenant_id))
            if image['public']=='no' and not my.admin:
                #allow only attaching public images
                bottle.abort(HTTP_Unauthorized, "Needed admin rights to attach a private image")
                return
            #insert in data base
            result, content = my.db.new_row('tenants_images', {'image_id':image_id, 'tenant_id': tenant_id})
            if result >= 0:
                return http_get_image_id(tenant_id, image_id)
        else: #detach
            if image['tenant_id']==None:
                bottle.abort(HTTP_Not_Found, "Image '%s' not attached to tenant '%s'" % (image_id, tenant_id))
            result, content = my.db.delete_row_by_dict(FROM='tenants_images', WHERE={'image_id':image_id, 'tenant_id':tenant_id})
            if result>=0:
                if image['public']=='no':
                    #try to delete the image completely to avoid orphan images, IGNORE error
                    my.db.delete_row_by_dict(FROM='images', WHERE={'uuid':image_id})
                data={'result' : "image detached"}
                return format_out(data)
    
    #if get here is because an error
    print "http_attach_detach_images error %d %s" % (result, content)
    bottle.abort(-result, content)
    return

@bottle.route(url_base + '/<tenant_id>/images/<image_id>', method='PUT')
def http_put_image_id(tenant_id, image_id):
    '''update a image_id into the database.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
    #parse input data
    http_content = format_in( image_update_schema )
    r = remove_extra_items(http_content, image_update_schema)
    if r is not None: print "http_put_image_id: Warning: remove extra items ", r
    change_keys_http2db(http_content['image'], http2db_image)
    metadata_dict = http_content['image'].pop('metadata', None)
    if metadata_dict is not None: 
        http_content['image']['metadata'] = json.dumps(metadata_dict)
    #Ensure that image exist 
    where_={'uuid': image_id}
    if tenant_id=='any':
        from_  ='images'
    else:
        from_  ='tenants_images as ti inner join images as i on ti.image_id=i.uuid'
        where_['tenant_id'] = tenant_id
    result, content = my.db.get_table(SELECT=('public',), FROM=from_, WHERE=where_)
    if result==0:
        text_error="Image '%s' not found" % image_id
        if tenant_id!='any':
            text_error +=" for tenant '%s'" % image_id
        bottle.abort(HTTP_Not_Found, text_error)
        return
    elif result>0:
        if content[0]['public']=='yes' and not my.admin:
            #allow only modifications over private images
            bottle.abort(HTTP_Unauthorized, "Needed admin rights to edit a public image")
            return
        #insert in data base
        result, content = my.db.update_rows('images', http_content['image'], {'uuid': image_id})

    if result < 0:
        print "http_put_image_id error %d %s" % (result, content)
        bottle.abort(-result, content)
        return
    else:
        return http_get_image_id(tenant_id, image_id)


#
# SERVERS
#

@bottle.route(url_base + '/<tenant_id>/servers', method='GET')
def http_get_servers(tenant_id):
    my = config_dic['http_threads'][ threading.current_thread().name ]
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
        return
    #obtain data
    select_,where_,limit_ = filter_query_string(bottle.request.query, http2db_server,
            ('id','name','description','hostId','imageRef','flavorRef','status', 'tenant_id') )
    if tenant_id!='any':
        where_['tenant_id'] = tenant_id
    result, content = my.db.get_table(SELECT=select_, FROM='instances', WHERE=where_, LIMIT=limit_)
    if result < 0:
        print "http_get_servers Error", content
        bottle.abort(-result, content)
    else:
        change_keys_http2db(content, http2db_server, reverse=True)
        for row in content:
            tenant_id = row.pop('tenant_id')
            row['links']=[ {'href': "/".join( (my.url_preffix, tenant_id, 'servers', str(row['id']) ) ), 'rel':'bookmark' } ]
        data={'servers' : content}
        return format_out(data)

@bottle.route(url_base + '/<tenant_id>/servers/<server_id>', method='GET')
def http_get_server_id(tenant_id, server_id):
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
        return
    #obtain data
    result, content = my.db.get_instance(server_id)
    if result == 0:
        bottle.abort(HTTP_Not_Found, content)
    elif result >0:
        #change image/flavor-id to id and link
        convert_bandwidth(content, reverse=True)
        convert_datetime2str(content)
        if content["ram"]==0 : del content["ram"]
        if content["vcpus"]==0 : del content["vcpus"]
        if 'flavor_id' in content:
            if content['flavor_id'] is not None:
                content['flavor'] = {'id':content['flavor_id'], 
                                     'links':[{'href':  "/".join( (my.url_preffix, content['tenant_id'], 'flavors', str(content['flavor_id']) ) ), 'rel':'bookmark'}] 
                                }
            del content['flavor_id']
        if 'image_id' in content:
            if content['image_id'] is not None:
                content['image'] = {'id':content['image_id'], 
                                    'links':[{'href':  "/".join( (my.url_preffix, content['tenant_id'], 'images', str(content['image_id']) ) ), 'rel':'bookmark'}]
                                }
            del content['image_id']
        change_keys_http2db(content, http2db_server, reverse=True)
        if 'extended' in content:
            if 'devices' in content['extended']: change_keys_http2db(content['extended']['devices'], http2db_server, reverse=True)
        data={'server' : content}
        return format_out(data)
    else:
        bottle.abort(-result, content)
        return

@bottle.route(url_base + '/<tenant_id>/servers', method='POST')
def http_post_server_id(tenant_id):
    '''deploys a new server'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
        return
    if tenant_id=='any':
        bottle.abort(HTTP_Bad_Request, "Invalid tenant 'any' with this command")
    #chek input
    http_content = format_in( server_new_schema )
    r = remove_extra_items(http_content, server_new_schema)
    if r is not None: print "http_post_serves: Warning: remove extra items ", r
    change_keys_http2db(http_content['server'], http2db_server)
    extended_dict = http_content['server'].get('extended', None)
    if extended_dict is not None:
        result, content = check_extended(extended_dict, True)
        if result<0:
            print "http_post_servers wrong input extended error %d %s" % (result, content)
            bottle.abort(-result, content)
            return
        convert_bandwidth(extended_dict)
        if 'devices' in extended_dict: change_keys_http2db(extended_dict['devices'], http2db_server)

    server = http_content['server']
    server_start = server.get('start', 'yes')
    server['tenant_id'] = tenant_id
    #check flavor valid and take info
    result, content = my.db.get_table(FROM='tenants_flavors as tf join flavors as f on tf.flavor_id=f.uuid',
             SELECT=('ram','vcpus','extended'), WHERE={'uuid':server['flavor_id'], 'tenant_id':tenant_id})
    if result<=0:
        bottle.abort(HTTP_Not_Found, 'flavor_id %s not found' % server['flavor_id'])
        return
    server['flavor']=content[0]
    #check image valid and take info
    result, content = my.db.get_table(FROM='tenants_images as ti join images as i on ti.image_id=i.uuid',
        SELECT=('path','metadata'), WHERE={'uuid':server['image_id'], 'tenant_id':tenant_id, "status":"ACTIVE"})
    if result<=0:
        bottle.abort(HTTP_Not_Found, 'image_id %s not found or not ACTIVE' % server['image_id'])
        return
    server['image']=content[0]
    if "hosts_id" in server:
        result, content = my.db.get_table(FROM='hosts', SELECT=('uuid',), WHERE={'uuid': server['host_id']})
        if result<=0:
            bottle.abort(HTTP_Not_Found, 'hostId %s not found' % server['host_id'])
            return
    #print json.dumps(server, indent=4)
     
    result, content = ht.create_server(server, config_dic['db'], config_dic['db_lock'], config_dic['mode']=='normal')

    if result >= 0:
    #Insert instance to database
        nets=[]
        print
        print "inserting at DB"
        print
        if server_start == 'no':
            content['status'] = 'INACTIVE'
        new_instance_result, new_instance = my.db.new_instance(content, nets)
        if new_instance_result < 0:
            print "Error http_post_servers() :", new_instance_result, new_instance
            return new_instance_result, new_instance
        print
        print "inserted at DB"
        print
        #updata nets
        for net in nets:
            r,c = config_dic['of_thread'].insert_task("update-net", net)
            if r < 0:
                print ':http_post_servers ERROR UPDATING NETS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' +  c
        
    #Start server
        
        server['uuid'] = new_instance
        #server_start = server.get('start', 'yes')
        if server_start != 'no':
            server['paused'] = True if server_start == 'paused' else False 
            server['action'] = {"start":None}
            server['status'] = "CREATING"
            #Program task
            r,c = config_dic['host_threads'][ server['host_id'] ].insert_task( 'instance',server )
            if r<0:
                my.db.update_rows('instances', {'status':"ERROR"}, {'uuid':server['uuid'], 'last_error':c}, log=True)
        
        return http_get_server_id(tenant_id, new_instance)
    else:
        bottle.abort(HTTP_Bad_Request, content)
        return

def http_server_action(server_id, tenant_id, action):
    '''Perform actions over a server as resume, reboot, terminate, ...'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    server={"uuid": server_id, "action":action}
    where={'uuid': server_id}
    if tenant_id!='any':
        where['tenant_id']= tenant_id
    result, content = my.db.get_table(FROM='instances', WHERE=where)
    if result == 0:
        bottle.abort(HTTP_Not_Found, "server %s not found" % server_id)
        return
    if result < 0:
        print "http_post_server_action error getting data %d %s" % (result, content)
        bottle.abort(HTTP_Internal_Server_Error, content)
        return
    server.update(content[0])
    tenant_id = server["tenant_id"]

    #TODO check a right content
    new_status = None
    if 'terminate' in action:
        new_status='DELETING'
    elif server['status'] == 'ERROR': #or server['status'] == 'CREATING':
        if 'terminate' not in action and 'rebuild' not in action:
            bottle.abort(HTTP_Method_Not_Allowed, "Server is in ERROR status, must be rebuit or deleted ")
            return
#     elif server['status'] == 'INACTIVE':
#         if 'start' not in action and 'createImage' not in action:
#             bottle.abort(HTTP_Method_Not_Allowed, "The only possible action over an instance in 'INACTIVE' status is 'start'")
#             return
#         if 'start' in action:
#             new_status='CREATING'
#             server['paused']='no'
#     elif server['status'] == 'PAUSED':
#         if 'resume' not in action:
#             bottle.abort(HTTP_Method_Not_Allowed, "The only possible action over an instance in 'PAUSED' status is 'resume'")
#             return
#     elif server['status'] == 'ACTIVE':
#         if 'pause' not in action and 'reboot'not in action and 'shutoff'not in action:
#             bottle.abort(HTTP_Method_Not_Allowed, "The only possible action over an instance in 'ACTIVE' status is 'pause','reboot' or 'shutoff'")
#             return

    if 'start' in action or 'createImage' in action or 'rebuild' in action:
        #check image valid and take info
        image_id = server['image_id']
        if 'createImage' in action:
            if 'imageRef' in action['createImage']:
                image_id = action['createImage']['imageRef']
            elif 'disk' in action['createImage']:
                result, content = my.db.get_table(FROM='instance_devices',
                    SELECT=('image_id','dev'), WHERE={'instance_id':server['uuid'],"type":"disk"})
                if result<=0:
                    bottle.abort(HTTP_Not_Found, 'disk not found for server')
                    return
                elif result>1:
                    disk_id=None
                    if action['createImage']['imageRef']['disk'] != None:
                        for disk in content:
                            if disk['dev'] == action['createImage']['imageRef']['disk']:
                                disk_id = disk['image_id']
                                break
                        if disk_id == None:
                            bottle.abort(HTTP_Not_Found, 'disk %s not found for server' % action['createImage']['imageRef']['disk'])
                            return
                    else:
                        bottle.abort(HTTP_Not_Found, 'more than one disk found for server' )
                        return
                    image_id = disk_id    
                else: #result==1
                    image_id = content[0]['image_id']    
                
        result, content = my.db.get_table(FROM='tenants_images as ti join images as i on ti.image_id=i.uuid',
            SELECT=('path','metadata'), WHERE={'uuid':image_id, 'tenant_id':tenant_id, "status":"ACTIVE"})
        if result<=0:
            bottle.abort(HTTP_Not_Found, 'image_id %s not found or not ACTIVE' % image_id)
            return
        if content[0]['metadata'] is not None:
            metadata = json.loads(content[0]['metadata'])
            content[0]['metadata']=metadata
        else:
            content[0]['metadata'] = {}
        server['image']=content[0]
        if 'createImage' in action:
            action['createImage']['source'] = {'image_id': image_id, 'path': content[0]['path']}
            
    if 'createImage' in action:
        #Create an entry in Database for the new image
        new_image={'status':'BUILD', 'progress': 0 }
        new_image_metadata=content[0]
        if 'metadata' in server['image'] and server['image']['metadata'] != None:
            new_image_metadata.update(server['image']['metadata'])
        new_image_metadata = {"use_incremental":"no"}
        if 'metadata' in action['createImage']:
            new_image_metadata.update(action['createImage']['metadata'])
        new_image['metadata'] = json.dumps(new_image_metadata)
        new_image['name'] = action['createImage'].get('name', None)
        new_image['description'] = action['createImage'].get('description', None)
        new_image['uuid']=my.db.new_uuid()
        if 'path' in action['createImage']:
            new_image['path'] = action['createImage']['path']
        else:
            new_image['path']="/provisional/path/" + new_image['uuid']
        result, image_uuid = my.db.new_image(new_image, tenant_id)
        if result<=0:
            bottle.abort(HTTP_Bad_Request, 'Error: ' + image_uuid)
            return
        server['new_image'] = new_image

                
    #Program task
    r,c = config_dic['host_threads'][ server['host_id'] ].insert_task( 'instance',server )
    if r<0:
        bottle.abort(HTTP_Request_Timeout, c)
    if 'createImage' in action and result >= 0:
        return http_get_image_id(tenant_id, image_uuid)
    
    #Update DB only for CREATING or DELETING status
    data={'result' : 'in process'}
    if new_status != None and new_status == 'DELETING':
        nets=[]
        r,c = my.db.delete_instance(server_id, tenant_id, nets, "requested by http")
        for net in nets:
            r1,c1 = config_dic['of_thread'].insert_task("update-net", net)
            if r1 < 0:
                print ' http_post_server_action error at server deletion ERROR UPDATING NETS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' +  c1
                data={'result' : 'deleting in process, but openflow rules cannot be deleted!!!!!'}

    return format_out(data)



@bottle.route(url_base + '/<tenant_id>/servers/<server_id>', method='DELETE')
def http_delete_server_id(tenant_id, server_id):
    '''delete a server'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
        return

    return http_server_action(server_id, tenant_id, {"terminate":None} )

    
@bottle.route(url_base + '/<tenant_id>/servers/<server_id>/action', method='POST')
def http_post_server_action(tenant_id, server_id):
    '''take an action over a server'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #check valid tenant_id
    result,content = check_valid_tenant(my, tenant_id)
    if result != 0:
        bottle.abort(result, content)
        return
    http_content = format_in( server_action_schema )
    #r = remove_extra_items(http_content, server_action_schema)
    #if r is not None: print "http_post_server_action: Warning: remove extra items ", r
    
    return http_server_action(server_id, tenant_id, http_content)

#
# NETWORKS
#


@bottle.route(url_base + '/networks', method='GET')
def http_get_networks():
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #obtain data
    select_,where_,limit_ = filter_query_string(bottle.request.query, http2db_network,
            ('id','name','tenant_id','type',
             'shared','provider:vlan','status','last_error','admin_state_up','provider:physical') )
    result, content = my.db.get_table(SELECT=select_, FROM='nets', WHERE=where_, LIMIT=limit_)
    if result < 0:
        print "http_get_networks error %d %s" % (result, content)
        bottle.abort(-result, content)
    else:
        convert_boolean(content, ('shared', 'admin_state_up') )
        delete_nulls(content)      
        change_keys_http2db(content, http2db_network, reverse=True)  
        data={'networks' : content}
        return format_out(data)

@bottle.route(url_base + '/networks/<network_id>', method='GET')
def http_get_network_id(network_id):
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #obtain data
    where_ = bottle.request.query
    where_['uuid'] = network_id
    result, content = my.db.get_table(FROM='nets', WHERE=where_, LIMIT=100)

    if result < 0:
        print "http_get_networks_id error %d %s" % (result, content)
        bottle.abort(-result, content)
    elif result==0:
        print "http_get_networks_id network '%s' not found" % network_id
        bottle.abort(HTTP_Not_Found, 'network %s not found' % network_id)
    else:
        convert_boolean(content, ('shared', 'admin_state_up') )
        change_keys_http2db(content, http2db_network, reverse=True)        
        #get ports
        result, ports = my.db.get_table(FROM='ports', SELECT=('uuid as port_id',), 
                                              WHERE={'net_id': network_id}, LIMIT=100)
        if len(ports) > 0:
            content[0]['ports'] = ports
        delete_nulls(content[0])      
        data={'network' : content[0]}
        return format_out(data)

@bottle.route(url_base + '/networks', method='POST')
def http_post_networks():
    '''insert a network into the database.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #parse input data
    http_content = format_in( network_new_schema )
    r = remove_extra_items(http_content, network_new_schema)
    if r is not None: print "http_post_networks: Warning: remove extra items ", r
    change_keys_http2db(http_content['network'], http2db_network)
    network=http_content['network']
    #check valid tenant_id
    tenant_id= network.get('tenant_id')
    if tenant_id!=None:
        result, _ = my.db.get_table(FROM='tenants', SELECT=('uuid',), WHERE={'uuid': tenant_id,"enabled":True})
        if result<=0:
            bottle.abort(HTTP_Not_Found, 'tenant %s not found or not enabled' % tenant_id)
            return
    bridge_net = None
    #check valid params
    net_bind = network.get('bind')
    net_type = network.get('type')
    net_vlan = network.get("vlan")
    
    if net_bind!=None:
        if net_bind[:9]=="openflow:":
            if net_type!=None:
                if net_type!="ptp" and net_type!="data":
                    bottle.abort(HTTP_Bad_Request, "Only 'ptp' or 'data' net types can be bound to 'openflow'")
            else:
                net_type='data'
        else:
            if net_type!=None:
                if net_type!="bridge_man" and net_type!="bridge_data":
                    bottle.abort(HTTP_Bad_Request, "Only 'bridge_man' or 'bridge_data' net types can be bound to 'bridge', 'macvtap' or 'default")
            else:
                net_type='bridge_man'
    
    if net_type==None:
        net_type='bridge_man' 
        
    if net_bind != None:
        if net_bind[:7]=='bridge:':
            #check it is one of the pre-provisioned bridges
            bridge_net_name = net_bind[7:]
            for brnet in config_dic['bridge_nets']:
                if brnet[0]==bridge_net_name: # free
                    if brnet[3] != None:
                        bottle.abort(HTTP_Conflict, "invalid binding at 'provider:physical', bridge '%s' is already used" % bridge_net_name)
                        return
                    bridge_net=brnet
                    net_vlan = brnet[1]
                    break
#            if bridge_net==None:     
#                bottle.abort(HTTP_Bad_Request, "invalid binding at 'provider:physical', bridge '%s' is not one of the provisioned 'bridge_ifaces' in the configuration file" % bridge_net_name)
#                return
    elif net_type=='bridge_data' or net_type=='bridge_man':
        #look for a free precreated nets
        for brnet in config_dic['bridge_nets']:
            if brnet[3]==None: # free
                if bridge_net != None:
                    if net_type=='bridge_man': #look for the smaller speed
                        if brnet[2] < bridge_net[2]:   bridge_net = brnet
                    else: #look for the larger speed
                        if brnet[2] > bridge_net[2]:   bridge_net = brnet
                else:
                    bridge_net = brnet
                    net_vlan = brnet[1]
        if bridge_net==None:
            bottle.abort(HTTP_Bad_Request, "Max limits of bridge networks reached. Future versions of VIM will overcome this limit")
            return
        else:
            print "using net", bridge_net
            net_bind = "bridge:"+bridge_net[0]
            net_vlan = bridge_net[1]
    if net_vlan==None and (net_type=="data" or net_type=="ptp"):
        net_vlan = my.db.get_free_net_vlan()
        if net_vlan < 0:
            bottle.abort(HTTP_Internal_Server_Error, "Error getting an available vlan")
            return
    
    network['bind'] = net_bind
    network['type'] = net_type
    network['vlan'] = net_vlan
    result, content = my.db.new_row('nets', network, True, True)
    
    if result >= 0:
        if bridge_net!=None:
            bridge_net[3] = content
        return http_get_network_id(content)
    else:
        print "http_post_networks error %d %s" % (result, content)
        bottle.abort(-result, content)
        return


@bottle.route(url_base + '/networks/<network_id>', method='PUT')
def http_put_network_id(network_id):
    '''update a network_id into the database.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #parse input data
    http_content = format_in( network_update_schema )
    r = remove_extra_items(http_content, network_update_schema)
    change_keys_http2db(http_content['network'], http2db_network)
    network=http_content['network']

    #Look for the previous data
    where_ = {'uuid': network_id}
    result, network_old = my.db.get_table(FROM='nets', WHERE=where_)
    if result < 0:
        print "http_put_network_id error %d %s" % (result, network_old)
        bottle.abort(-result, network_old)
        return
    elif result==0:
        print "http_put_network_id network '%s' not found" % network_id
        bottle.abort(HTTP_Not_Found, 'network %s not found' % network_id)
        return
    #get ports
    nbports, content = my.db.get_table(FROM='ports', SELECT=('uuid as port_id',), 
                                              WHERE={'net_id': network_id}, LIMIT=100)
    if result < 0:
        print "http_put_network_id error %d %s" % (result, network_old)
        bottle.abort(-result, content)
        return
    if nbports>0:
        if 'type' in network and network['type'] != network_old[0]['type']:
            bottle.abort(HTTP_Method_Not_Allowed, "Can not change type of network while having ports attached")
        if 'vlan' in network and network['vlan'] != network_old[0]['vlan']:
            bottle.abort(HTTP_Method_Not_Allowed, "Can not change vlan of network while having ports attached")

    #check valid params
    net_bind = network.get('bind', network_old[0]['bind'])
    net_type = network.get('type', network_old[0]['type'])
    if net_bind!=None:
        if net_bind[:9]=="openflow:":
            if net_type!="ptp" and net_type!="data":
                bottle.abort(HTTP_Bad_Request, "Only 'ptp' or 'data' net types can be bound to 'openflow'")
        else:
            if net_type!="bridge_man" and net_type!="bridge_data":
                    bottle.abort(HTTP_Bad_Request, "Only 'bridge_man' or 'bridge_data' net types can be bound to 'bridge', 'macvtap' or 'default")

    #insert in data base
    result, content = my.db.update_rows('nets', network, WHERE={'uuid': network_id}, log=True )
    if result >= 0:
        if result>0 and nbports>0 and 'admin_state_up' in network and network['admin_state_up'] != network_old[0]['admin_state_up']:
            r,c = config_dic['of_thread'].insert_task("update-net", network_id)
            if r  < 0:
                print "http_put_network_id error while launching openflow rules"
                bottle.abort(HTTP_Internal_Server_Error, c)
        return http_get_network_id(network_id)
    else:
        bottle.abort(-result, content)
        return

  
@bottle.route(url_base + '/networks/<network_id>', method='DELETE')
def http_delete_network_id(network_id):
    '''delete a network_id from the database.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]

    #delete from the data base
    result, content = my.db.delete_row('nets', network_id )
   
    if result == 0:
        bottle.abort(HTTP_Not_Found, content)
    elif result >0:
        for brnet in config_dic['bridge_nets']:
            if brnet[3]==network_id:
                brnet[3]=None
                break
        data={'result' : content}
        return format_out(data)
    else:
        print "http_delete_network_id error",result, content
        bottle.abort(-result, content)
        return
#
# OPENFLOW
#
@bottle.route(url_base + '/networks/<network_id>/openflow', method='GET')
def http_get_openflow_id(network_id):
    '''To obtain the list of openflow rules of a network
    '''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #ignore input data
    if network_id=='all':
        where_={}
    else:
        where_={"net_id": network_id}
    result, content = my.db.get_table(SELECT=("name","net_id","priority","vlan_id","ingress_port","src_mac","dst_mac","actions"),
            WHERE=where_, FROM='of_flows')
    if result < 0:
        bottle.abort(-result, content)
        return
    data={'openflow-rules' : content}
    return format_out(data)

@bottle.route(url_base + '/networks/<network_id>/openflow', method='PUT')
def http_put_openflow_id(network_id):
    '''To make actions over the net. The action is to reinstall the openflow rules
    network_id can be 'all'
    '''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    if not my.admin:
        bottle.abort(HTTP_Unauthorized, "Needed admin privileges")
        return
    #ignore input data
    if network_id=='all':
        where_={}
    else:
        where_={"uuid": network_id}
    result, content = my.db.get_table(SELECT=("uuid","type"), WHERE=where_, FROM='nets')
    if result < 0:
        bottle.abort(-result, content)
        return
    
    for net in content:
        if net["type"]!="ptp" and net["type"]!="data":
            result-=1
            continue
        r,c = config_dic['of_thread'].insert_task("update-net", net['uuid'])
        if r  < 0:
            print "http_put_openflow_id error while launching openflow rules"
            bottle.abort(HTTP_Internal_Server_Error, c)
    data={'result' : str(result)+" nets updates"}
    return format_out(data)

@bottle.route(url_base + '/networks/openflow/clear', method='DELETE')
@bottle.route(url_base + '/networks/clear/openflow', method='DELETE')
def http_clear_openflow_rules():
    '''To make actions over the net. The action is to delete ALL openflow rules
    '''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    if not my.admin:
        bottle.abort(HTTP_Unauthorized, "Needed admin privileges")
        return
    #ignore input data
    r,c = config_dic['of_thread'].insert_task("clear-all")
    if r  < 0:
        print "http_delete_openflow_id error while launching openflow rules"
        bottle.abort(HTTP_Internal_Server_Error, c)
        return

    data={'result' : " Clearing openflow rules in process"}
    return format_out(data)

@bottle.route(url_base + '/networks/openflow/ports', method='GET')
def http_get_openflow_ports():
    '''Obtain switch ports names of openflow controller
    '''
    data={'ports' : config_dic['of_thread'].OF_connector.pp2ofi}
    return format_out(data)


#
# PORTS
#

@bottle.route(url_base + '/ports', method='GET')
def http_get_ports():
    #obtain data
    my = config_dic['http_threads'][ threading.current_thread().name ]
    select_,where_,limit_ = filter_query_string(bottle.request.query, http2db_port,
            ('id','name','tenant_id','network_id','vpci','mac_address','device_owner','device_id',
             'binding:switch_port','binding:vlan','bandwidth','status','admin_state_up') )
    #result, content = my.db.get_ports(where_)
    result, content = my.db.get_table(SELECT=select_, WHERE=where_, FROM='ports',LIMIT=limit_)
    if result < 0:
        print "http_get_ports Error", result, content
        bottle.abort(-result, content)
        return
    else:
        convert_boolean(content, ('admin_state_up',) )
        delete_nulls(content)      
        change_keys_http2db(content, http2db_port, reverse=True)
        data={'ports' : content}
        return format_out(data)

@bottle.route(url_base + '/ports/<port_id>', method='GET')
def http_get_port_id(port_id):
    my = config_dic['http_threads'][ threading.current_thread().name ]
    #obtain data
    result, content = my.db.get_table(WHERE={'uuid': port_id}, FROM='ports')
    if result < 0:
        print "http_get_ports error", result, content
        bottle.abort(-result, content)
    elif result==0:
        print "http_get_ports port '%s' not found" % str(port_id)
        bottle.abort(HTTP_Not_Found, 'port %s not found' % port_id)
    else:
        convert_boolean(content, ('admin_state_up',) )
        delete_nulls(content)      
        change_keys_http2db(content, http2db_port, reverse=True)
        data={'port' : content[0]}
        return format_out(data)
    

@bottle.route(url_base + '/ports', method='POST')
def http_post_ports():
    '''insert an external port into the database.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    if not my.admin:
        bottle.abort(HTTP_Unauthorized, "Needed admin privileges")
    #parse input data
    http_content = format_in( port_new_schema )
    r = remove_extra_items(http_content, port_new_schema)
    if r is not None: print "http_post_ports: Warning: remove extra items ", r
    change_keys_http2db(http_content['port'], http2db_port)
    port=http_content['port']

    port['type'] = 'external'
    if 'net_id' in port and port['net_id'] == None:
        del port['net_id']

    if 'net_id' in port:
        #check that new net has the correct type
        result, new_net = my.db.check_target_net(port['net_id'], None, 'external' )
        if result < 0:
            bottle.abort(HTTP_Bad_Request, new_net)
            return
    #insert in data base
    result, uuid = my.db.new_row('ports', port, True, True)
    if result > 0:
        if 'net_id' in port: 
            r,c = config_dic['of_thread'].insert_task("update-net", port['net_id'])
            if r < 0:
                print "http_post_ports error while launching openflow rules"
                bottle.abort(HTTP_Internal_Server_Error, c)
        return http_get_port_id(uuid)
    else:
        bottle.abort(-result, uuid)
        return
    
@bottle.route(url_base + '/ports/<port_id>', method='PUT')
def http_put_port_id(port_id):
    '''update a port_id into the database.'''

    my = config_dic['http_threads'][ threading.current_thread().name ]
    #parse input data
    http_content = format_in( port_update_schema )
    change_keys_http2db(http_content['port'], http2db_port)
    port_dict=http_content['port']

    #Look for the previous port data
    where_ = {'uuid': port_id}
    result, content = my.db.get_table(FROM="ports",WHERE=where_)
    if result < 0:
        print "http_put_port_id error", result, content
        bottle.abort(-result, content)
        return
    elif result==0:
        print "http_put_port_id port '%s' not found" % port_id
        bottle.abort(HTTP_Not_Found, 'port %s not found' % port_id)
        return
    print port_dict
    for k in ('vlan','switch_port','mac_address', 'tenant_id'):
        if k in port_dict and not my.admin:
            bottle.abort(HTTP_Unauthorized, "Needed admin privileges for changing " + k)
            return
    
    port=content[0]
    #change_keys_http2db(port, http2db_port, reverse=True)
    nets = []
    host_id = None
    result=1
    if 'net_id' in port_dict:
        #change of net. 
        old_net = port.get('net_id', None)
        new_net = port_dict['net_id']
        if old_net != new_net:
            
            if old_net is not None: nets.append(old_net)
            if new_net is not None: nets.append(new_net)
            if port['type'] == 'instance:bridge':
                bottle.abort(HTTP_Forbidden, "bridge interfaces cannot be attached to a different net")
                return
            elif port['type'] == 'external':
                if not my.admin:
                    bottle.abort(HTTP_Unauthorized, "Needed admin privileges")
                    return
            else:
                if new_net != None:
                    #check that new net has the correct type
                    result, new_net_dict = my.db.check_target_net(new_net, None, port['type'] )
                
                #change VLAN for SR-IOV ports
                if result>0 and port["type"]=="instance:data" and port["model"]=="VF": #TODO consider also VFnotShared
                    if new_net == None:
                        port_dict["vlan"] = None
                    else:
                        port_dict["vlan"] = new_net_dict["vlan"]
                    #get host where this VM is allocated
                    result, content = my.db.get_table(FROM="instances",WHERE={"uuid":port["instance_id"]})
                    if result<0:
                        print "http_put_port_id database error", content
                    elif result>0:
                        host_id = content[0]["host_id"]
    
    #insert in data base
    if result >= 0:
        result, content = my.db.update_rows('ports', port_dict, WHERE={'uuid': port_id}, log=False )
        
    #Insert task to complete actions
    if result > 0: 
        for net_id in nets:
            r,v = config_dic['of_thread'].insert_task("update-net", net_id)
            if r<0: print "Error *********   http_put_port_id  update_of_flows: ", v
            #TODO Do something if fails
        if host_id != None:
            config_dic['host_threads'][host_id].insert_task("edit-iface", port_id, old_net, new_net)
    
    if result >= 0:
        return http_get_port_id(port_id)
    else:
        bottle.abort(HTTP_Bad_Request, content)
        return

  
@bottle.route(url_base + '/ports/<port_id>', method='DELETE')
def http_delete_port_id(port_id):
    '''delete a port_id from the database.'''
    my = config_dic['http_threads'][ threading.current_thread().name ]
    if not my.admin:
        bottle.abort(HTTP_Unauthorized, "Needed admin privileges")
        return

    #Look for the previous port data
    where_ = {'uuid': port_id, "type": "external"}
    result, ports = my.db.get_table(WHERE=where_, FROM='ports',LIMIT=100)
    
    if result<=0:
        print "http_delete_port_id port '%s' not found" % port_id
        bottle.abort(HTTP_Not_Found, 'port %s not found or device_owner is not external' % port_id)
        return
    #delete from the data base
    result, content = my.db.delete_row('ports', port_id )

    if result == 0:
        bottle.abort(HTTP_Not_Found, content)
    elif result >0:
        network = ports[0].get('net_id', None)
        if network is not None:
            #change of net. 
            r,c = config_dic['of_thread'].insert_task("update-net", network)
            if r<0: print "!!!!!! http_delete_port_id update_of_flows error", r, c 
        data={'result' : content}
        return format_out(data)
    else:
        print "http_delete_port_id error",result, content
        bottle.abort(-result, content)
    return
    

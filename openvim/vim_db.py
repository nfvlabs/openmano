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
This module interact with the openvim database,
It implements general table management
and complex writings 'transactional' sures, 
that is, or all is changed or nothing
'''

__author__="Alfonso Tierno"
__date__ ="$10-jul-2014 12:07:15$"

import MySQLdb as mdb
import uuid as myUuid
from utils import auxiliary_functions as af

HTTP_Bad_Request = 400
HTTP_Unauthorized = 401 
HTTP_Not_Found = 404 
HTTP_Method_Not_Allowed = 405 
HTTP_Request_Timeout = 408
HTTP_Conflict = 409
HTTP_Service_Unavailable = 503 
HTTP_Internal_Server_Error = 500 


class vim_db():
    def __init__(self, vlan_range, debug=False):
        '''vlan_range must be a tuple (vlan_ini, vlan_end) with available vlan values for networks
        every dataplane network contain a unique value, regardless of it is used or not 
        ''' 
        #initialization
        self.net_vlan_range = vlan_range
        self.net_vlan_usedlist = None
        self.net_vlan_lastused = self.net_vlan_range[0] -1
        self.debug=debug

    def connect(self, host=None, user=None, passwd=None, database=None):
        '''Connect to the concrete data base. 
        The first time a valid host, user, passwd and database must be provided,
        Following calls can skip this parameters
        '''
        try:
            if host     is not None: self.host = host
            if user     is not None: self.user = user
            if passwd   is not None: self.passwd = passwd
            if database is not None: self.database = database

            self.con = mdb.connect(self.host, self.user, self.passwd, self.database)
            print "DB: conected to %s@%s -> %s" % (self.user, self.host, self.database)
            return 0
        except mdb.Error, e:
            print "Error connecting to DB %s@%s -> %s Error %d: %s" % (self.user, self.host, self.database, e.args[0], e.args[1])
            return -1

    def get_db_version(self):
        ''' Obtain the database schema version.
        Return: (negative, text) if error or version 0.0 where schema_version table is missing
                (version_int, version_text) if ok
        '''
        cmd = "SELECT version_int,version,openvim_ver FROM schema_version"
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    rows = self.cur.fetchall()
                    highest_version_int=0
                    highest_version=""
                    #print rows
                    for row in rows: #look for the latest version
                        if row[0]>highest_version_int:
                            highest_version_int, highest_version = row[0:2]
                    return highest_version_int, highest_version
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "get_db_version DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c    
                
    def disconnect(self):
        '''disconnect from the data base'''
        try:
            self.con.close()
            del self.con
        except mdb.Error, e:
            print "Error disconnecting to DB: Error %d: %s" % (e.args[0], e.args[1])
            return -1
        except AttributeError, e: #self.con not defined
            if e[0][-5:] == "'con'": return -1, "Database internal error, no connection."
            else: raise
    
    def format_error(self, e, command=None, extra=None): 
        if type(e[0]) is str:
            if e[0][-5:] == "'con'": return -HTTP_Internal_Server_Error, "DB Exception, no connection."
            else: raise
        if e.args[0]==2006 or e.args[0]==2013 : #MySQL server has gone away (((or)))    Exception 2013: Lost connection to MySQL server during query
            #reconnect
            self.connect()
            return -HTTP_Request_Timeout,"Database reconnection. Try Again"
        fk=e.args[1].find("foreign key constraint fails")
        if fk>=0:
            if command=="update": return -HTTP_Bad_Request, "tenant_id %s not found." % extra
            elif command=="delete":  return -HTTP_Bad_Request, "Resource is not free. There are %s that prevent its deletion." % extra
        de = e.args[1].find("Duplicate entry")
        fk = e.args[1].find("for key")
        uk = e.args[1].find("Unknown column")
        wc = e.args[1].find("in 'where clause'")
        fl = e.args[1].find("in 'field list'")
        #print de, fk, uk, wc,fl
        if de>=0:
            if fk>=0: #error 1062
                return -HTTP_Conflict, "Value %s already in use for %s" % (e.args[1][de+15:fk], e.args[1][fk+7:])
        if uk>=0:
            if wc>=0:
                return -HTTP_Bad_Request, "Field %s can not be used for filtering" % e.args[1][uk+14:wc]
            if fl>=0:
                return -HTTP_Bad_Request, "Field %s does not exist" % e.args[1][uk+14:wc]
        return -HTTP_Internal_Server_Error, "Database internal Error %d: %s" % (e.args[0], e.args[1])
    
    def __get_used_net_vlan(self):
        #get used from database if needed
        try:
            with self.con:
                self.cur = self.con.cursor()
                cmd = "SELECT vlan FROM nets WHERE vlan>='%s' and (type='ptp' or type='data') ORDER BY vlan LIMIT 25" % self.net_vlan_lastused
                if self.debug: print cmd
                self.cur.execute(cmd)
                vlan_tuple = self.cur.fetchall()
                #convert a tuple of tuples in a list of numbers
                self.net_vlan_usedlist = []
                for k in vlan_tuple:
                    self.net_vlan_usedlist.append(k[0])
            return 0
        except (mdb.Error, AttributeError), e:
            if not self.debug: print cmd
            print "get_free_net_vlan DB Exception %d: %s" % (e.args[0], e.args[1])
            return self.format_error(e)
    
    def get_free_net_vlan(self):
        '''obtain a vlan not used in any net'''
        
        while True:
            print "net_vlan_lastused", self.net_vlan_lastused, "self.net_vlan_range", self.net_vlan_range,"net_vlan_usedlist", self.net_vlan_usedlist
            self.net_vlan_lastused += 1
            if self.net_vlan_lastused ==  self.net_vlan_range[1]:
                #start from the begining
                self.net_vlan_lastused =  self.net_vlan_range[0]
                self.net_vlan_usedlist = None
            if self.net_vlan_usedlist is None \
            or (len(self.net_vlan_usedlist)>0 and self.net_vlan_lastused >= self.net_vlan_usedlist[-1] and len(self.net_vlan_usedlist)==25):
                r = self.__get_used_net_vlan()
                if r<0: return r
                print "new net_vlan_usedlist", self.net_vlan_usedlist
            if self.net_vlan_lastused in self.net_vlan_usedlist:
                continue
            else:
                return self.net_vlan_lastused
                
    def get_table(self, **sql_dict):
        ''' Obtain rows from a table.
        Atribure sql_dir: dictionary with the following key: value
            'SELECT': [list of fields to retrieve] (by default all)
            'FROM': string of table name (Mandatory)
            'WHERE': dict of key:values, translated to key=value AND ... (Optional)
            'WHERE_OR': dict of key:values, translated to key=value OR ... (Optional)
            'LIMIT': limit of number of rows (Optional)
        Return: a list with dictionarys at each row
        '''
        #print sql_dict
        select_= "SELECT " + ("*" if 'SELECT' not in sql_dict else ",".join(map(str,sql_dict['SELECT'])) )
        #print 'select_', select_
        from_  = "FROM " + str(sql_dict['FROM'])
        #print 'from_', from_
        
        where_and = None
        where_or = None
        if 'WHERE' in sql_dict and len(sql_dict['WHERE']) > 0:
            w=sql_dict['WHERE']
            where_and = " AND ".join(map( lambda x: str(x) + (" is Null" if w[x] is None else "='"+str(w[x])+"'"),  w.keys()) ) 
        if 'WHERE_OR' in sql_dict and len(sql_dict['WHERE_OR']) > 0:
            w=sql_dict['WHERE_OR']
            where_or =  " OR ".join(map( lambda x: str(x) + (" is Null" if w[x] is None else "='"+str(w[x])+"'"),  w.keys()) )
             
        if where_and!=None and where_or!=None:
            where_ = "WHERE (" + where_and + ") OR " + where_or
        elif where_and!=None and where_or==None:
            where_ = "WHERE " + where_and
        elif where_and==None and where_or!=None:
            where_ = "WHERE " + where_or
        else:
            where_ = ""
        #print 'where_', where_
        limit_ = "LIMIT " + str(sql_dict['LIMIT']) if 'LIMIT' in sql_dict else ""
        #print 'limit_', limit_
        cmd =  " ".join( (select_, from_, where_, limit_) )
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    rows = self.cur.fetchall()
                    return self.cur.rowcount, rows
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "get_table DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
        
    def new_tenant(self, tenant_dict):
        ''' Add one row into a table.
        Attribure 
            tenant_dict: dictionary with the key: value to insert
        It checks presence of uuid and add one automatically otherwise
        Return: (result, uuid) where result can be 0 if error, or 1 if ok
        '''
        for retry_ in range(0,2):
            cmd=""
            inserted=-1
            try:
                #create uuid if not provided
                if 'uuid' not in tenant_dict:
                    uuid = tenant_dict['uuid'] = str(myUuid.uuid1()) # create_uuid
                else: 
                    uuid = str(tenant_dict['uuid'])
                #obtain tenant_id for logs
                tenant_id = uuid
                with self.con:
                    self.cur = self.con.cursor()
                    #inserting new uuid
                    cmd = "INSERT INTO uuids (uuid, used_at) VALUES ('%s','tenants')" % uuid
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    #insert tenant
                    cmd= "INSERT INTO tenants (" + \
                        ",".join(map(str, tenant_dict.keys() ))   + ") VALUES(" + \
                        ",".join(map(lambda x: "Null" if x is None else "'"+str(x)+"'",tenant_dict.values() )) + ")"
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    inserted = self.cur.rowcount
                    #inserting new log
                    del tenant_dict['uuid'] # not interested for the log
                    cmd = "INSERT INTO logs (related,level,tenant_id,uuid,description) VALUES ('tenants','debug','%s','%s',\"new tenant %s\")" % (uuid, tenant_id, str(tenant_dict))
                    if self.debug: print cmd
                    self.cur.execute(cmd)  
                    #commit transaction
                    self.cur.close()
                if inserted == 0: return 0, uuid
                with self.con:
                    self.cur = self.con.cursor()
                    #adding public flavors
                    cmd = "INSERT INTO tenants_flavors(flavor_id,tenant_id) SELECT uuid as flavor_id,'"+ tenant_id + "' FROM flavors WHERE public = 'yes'"
                    if self.debug: print cmd
                    self.cur.execute(cmd) 
                    if self.debug: print "attached public flavors: ", self.cur.rowcount
                    #rows = self.cur.fetchall()
                    #for row in rows:
                    #    cmd = "INSERT INTO tenants_flavors(flavor_id,tenant_id) VALUES('%s','%s')" % (row[0], tenant_id)
                    #    self.cur.execute(cmd )
                    #adding public images
                    cmd = "INSERT INTO tenants_images(image_id,tenant_id) SELECT uuid as image_id,'"+ tenant_id + "' FROM images WHERE public = 'yes'"
                    if self.debug: print cmd
                    self.cur.execute(cmd) 
                    if self.debug: print "attached public images: ", self.cur.rowcount

                    return 1, uuid
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "new_tenant DB Exception %d: %s" % (e.args[0], e.args[1])
                if inserted==1: return 1, uuid
                else: 
                    r,c = self.format_error(e)
                    if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def new_row(self, table, INSERT, add_uuid=False, log=False):
        ''' Add one row into a table.
        Atribure 
            INSERT: dictionary with the key: value to insert
            table: table where to insert
            add_uuid: if True, it will crated an uuid key entry at INSERT if not provided
        It checks presence of uuid and add one automatically otherwise
        Return: (result, uuid) where result can be 0 if error, or 1 if ok
        '''
        for retry_ in range(0,2):
            cmd=""
            try:
                if add_uuid:
                    #create uuid if not provided
                    if 'uuid' not in INSERT:
                        uuid = INSERT['uuid'] = str(myUuid.uuid1()) # create_uuid
                    else: 
                        uuid = str(INSERT['uuid'])
                else:
                    uuid=None
                with self.con:
                    self.cur = self.con.cursor()
                    if add_uuid:
                        #inserting new uuid
                        cmd = "INSERT INTO uuids (uuid, used_at) VALUES ('%s','%s')" % (uuid, table)
                        if self.debug: print cmd
                        self.cur.execute(cmd)
                    #insertion
                    cmd= "INSERT INTO " + table +" (" + \
                        ",".join(map(str, INSERT.keys() ))   + ") VALUES(" + \
                        ",".join(map(lambda x: 'Null' if x is None else "'"+str(x)+"'", INSERT.values() )) + ")"
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    nb_rows = self.cur.rowcount
                    #inserting new log
                    if nb_rows > 0 and log:                
                        if add_uuid: del INSERT['uuid']
                        #obtain tenant_id for logs
                        if 'tenant_id' in INSERT: 
                            tenant_id = INSERT['tenant_id']
                            del INSERT['tenant_id']
                        elif table == 'tenants':    
                            tenant_id = uuid
                        else:                       
                            tenant_id = None
                        if uuid is None: uuid_k = uuid_v = ""
                        else: uuid_k=",uuid"; uuid_v=",'" + str(uuid) + "'"
                        if tenant_id is None: tenant_k = tenant_v = ""
                        else: tenant_k=",tenant_id"; tenant_v=",'" + str(tenant_id) + "'"
                        cmd = "INSERT INTO logs (related,level%s%s,description) VALUES ('%s','debug'%s%s,\"new %s %s\")" \
                            % (uuid_k, tenant_k, table, uuid_v, tenant_v, table[:-1], str(INSERT))
                        if self.debug: print cmd
                        self.cur.execute(cmd)                    
                    return nb_rows, uuid

            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "new_row DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
    
    def __remove_quotes(self, data):
        '''remove single quotes ' of any string content of data dictionary'''
        for k,v in data.items():
            if type(v) == str:
                if "'" in v: 
                    data[k] = data[k].replace("'","_")

    def update_rows(self, table, UPDATE, WHERE, log=False):
        ''' Update one or several rows into a table.
        Atributes
            UPDATE: dictionary with the key: value to change
            table: table where to update
            WHERE: dictionary of elements to update
        Return: (result, None) where result indicates the number of updated files
        '''
        self.__remove_quotes(UPDATE)
        for retry_ in range(0,2):
            cmd=""
            try:
                #gettting uuid 
                uuid = WHERE['uuid'] if 'uuid' in WHERE else None

                with self.con:
                    self.cur = self.con.cursor()
                    cmd= "UPDATE " + table +" SET " + \
                        ",".join(map(lambda x: str(x)+ ('=Null' if UPDATE[x] is None else "='"+ str(UPDATE[x]) +"'"  ),   UPDATE.keys() )) + \
                        " WHERE " + " and ".join(map(lambda x: str(x)+ (' is Null' if WHERE[x] is None else"='"+str(WHERE[x])+"'" ),  WHERE.keys() ))
                    if self.debug: print cmd
                    self.cur.execute(cmd) 
                    nb_rows = self.cur.rowcount
                    if nb_rows > 0 and log:                
                        #inserting new log
                        if uuid is None: uuid_k = uuid_v = ""
                        else: uuid_k=",uuid"; uuid_v=",'" + str(uuid) + "'"
                        cmd = "INSERT INTO logs (related,level%s,description) VALUES ('%s','debug'%s,\"updating %d entry %s\")" \
                            % (uuid_k, table, uuid_v, nb_rows, (str(UPDATE)).replace('"','-')  )
                        if self.debug: print cmd
                        self.cur.execute(cmd)                    
                    return nb_rows, uuid
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "update_rows DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
            
    def get_host(self, host_id):
        if af.check_valid_uuid(host_id):
            where_filter="uuid='" + host_id + "'"
        else:
            where_filter="name='" + host_id + "'"
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    #get HOST
                    cmd = "SELECT uuid, user, name, ip_name, description, ranking, admin_state_up, DATE_FORMAT(created_at,'%Y-%m-%dT%H:%i:%s') as created_at \
                        FROM hosts WHERE " + where_filter
                    if self.debug: print cmd 
                    self.cur.execute(cmd)
                    if self.cur.rowcount == 0 : 
                        return 0, "host '" + str(host_id) +"'not found."
                    elif self.cur.rowcount > 1 : 
                        return 0, "host '" + str(host_id) +"' matches more than one result."
                    host = self.cur.fetchone()
                    host_id = host['uuid']
                    #get numa
                    cmd = "SELECT id, numa_socket, hugepages, memory, admin_state_up FROM numas WHERE host_id = '" + str(host_id) + "'"
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    host['numas'] = self.cur.fetchall()
                    for numa in host['numas']:
                        #print "SELECT core_id, instance_id, status, thread_id, v_thread_id FROM resources_core  WHERE numa_id = '" + str(numa['id']) + "'"
                        #get cores
                        cmd = "SELECT core_id, instance_id, status, thread_id, v_thread_id FROM resources_core  WHERE numa_id = '" + str(numa['id']) + "'"
                        if self.debug: print cmd
                        self.cur.execute(cmd)
                        numa['cores'] = self.cur.fetchall()
                        for core in numa['cores']: 
                            if core['instance_id'] == None: del core['instance_id'], core['v_thread_id']
                            if core['status'] == 'ok': del core['status']
                        #get used memory
                        cmd = "SELECT sum(consumed) as hugepages_consumed FROM resources_mem  WHERE numa_id = '" + str(numa['id']) + "' GROUP BY numa_id"
                        if self.debug: print cmd
                        self.cur.execute(cmd)
                        used = self.cur.fetchone()
                        used_= int(used['hugepages_consumed']) if used != None else 0
                        numa['hugepages_consumed'] = used_
                        #get ports
                        #cmd = "CALL GetPortsFromNuma(%s)'" % str(numa['id'])
                        #self.cur.callproc('GetPortsFromNuma', (numa['id'],) )
                        #every time a Procedure is launched you need to close and open the cursor 
                        #under Error 2014: Commands out of sync; you can't run this command now
                        #self.cur.close()   
                        #self.cur = self.con.cursor(mdb.cursors.DictCursor)
                        cmd="SELECT Mbps, pci, status, Mbps_consumed, switch_port, switch_dpid, mac, source_name, sriovs-1 as sriovs\
                            FROM(SELECT * FROM resources_port WHERE numa_id=%d AND id=root_id) as A\
                            INNER JOIN(SELECT root_id, count(pci) as sriovs, sum(Mbps_used) as Mbps_consumed\
                            FROM resources_port WHERE numa_id=%d GROUP BY root_id) as B ON A.id = B.root_id;" % (numa['id'], numa['id'])
                        if self.debug: print cmd
                        self.cur.execute(cmd)
                        numa['interfaces'] = self.cur.fetchall()
                        for iface in numa['interfaces']: 
                            iface['Mbps_consumed'] = int(iface['Mbps_consumed']) #change to a Normal format
                            if iface['status'] == 'ok': del iface['status']

                        #delete internal field
                        del numa['id']
                    return 1, host
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "get_host DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
        
    def new_uuid(self):
        max_retries=10
        while max_retries>0:
            uuid =  str( myUuid.uuid1() )
            if self.check_uuid(uuid)[0] == 0:
                return uuid
            max_retries-=1
        return uuid

    def check_uuid(self, uuid):
        '''check in the database if this uuid is already present'''
        try:
            with self.con:
                self.cur = self.con.cursor(mdb.cursors.DictCursor)
                cmd = "SELECT * FROM uuids where uuid='" + str(uuid) + "'"
                if self.debug: print cmd
                self.cur.execute(cmd)
                rows = self.cur.fetchall()
                return self.cur.rowcount, rows
        except (mdb.Error, AttributeError), e:
            if not self.debug: print cmd
            print "check_uuid DB Exception %d: %s" % (e.args[0], e.args[1])
            return self.format_error(e)
            
    def __get_next_ids(self):
        '''get next auto increment index of all table in the database'''
        self.cur.execute("SELECT table_name,AUTO_INCREMENT FROM information_schema.tables WHERE AUTO_INCREMENT IS NOT NULL AND table_schema = DATABASE()") 
        rows = self.cur.fetchall()
        return self.cur.rowcount, dict(rows)
    
    def edit_host(self, host_id, host_dict):
        #get next port index
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:
                    self.cur = self.con.cursor()

                    #update table host
                    numa_list = host_dict.pop('numas', [])                    
                    if len(host_dict)>0:
                        cmd= "UPDATE hosts SET " + \
                            ",".join(map(lambda x: str(x)+ ('=Null' if host_dict[x] is None else "='"+ str(host_dict[x]) +"'"  ),   host_dict.keys() )) + \
                            " WHERE uuid='" + host_id +"'"
                        if self.debug: print cmd
                        self.cur.execute(cmd) 
                    for numa_dict in numa_list:
                        cmd= "UPDATE numas SET admin_state_up='" + str(numa_dict['admin_state_up']) + \
                            "' WHERE host_id='" + host_id +"' AND numa_socket='"+ str(numa_dict['numa_socket']) + "'"
                        if self.debug: print cmd
                        self.cur.execute(cmd) 
                return self.get_host(host_id)
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "edit_host DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def new_host(self, host_dict):
        #get next port index
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:
                    self.cur = self.con.cursor()

                    result, next_ids = self.__get_next_ids()
                    print "next_ids: " + str(next_ids)
                    if result <= 0: return result, "Internal DataBase error getting next id of tables"

                    #create uuid if not provided
                    if 'uuid' not in host_dict:
                        uuid = host_dict['uuid'] = str(myUuid.uuid1()) # create_uuid
                    else: #check uuid is valid
                        uuid = str(host_dict['uuid'])
                    #    result, data = self.check_uuid(uuid)
                    #    if (result == 1):
                    #        return -1, "UUID '%s' already in use" % uuid

                    #inserting new uuid
                    cmd = "INSERT INTO uuids (uuid, used_at) VALUES ('%s','hosts')" % uuid
                    if self.debug: print cmd
                    result = self.cur.execute(cmd)

                    #insert in table host
                    numa_list = host_dict.pop('numas', [])
                    #get nonhupages and nonisolated cpus
                    host_dict['RAM']=0
                    host_dict['cpus']=0
                    for numa in numa_list:
                        mem_numa = numa.get('memory', 0) - numa.get('hugepages',0)
                        if mem_numa>0:
                            host_dict['RAM'] += mem_numa 
                        for core in numa.get("cores", []):
                            if "status" in core and core["status"]=="noteligible":
                                host_dict['cpus']+=1
                    host_dict['RAM']*=1024 # from GB to MB
                                            
                    keys    = ",".join(host_dict.keys())
                    values  = ",".join( map(lambda x: "Null" if x is None else "'"+str(x)+"'", host_dict.values() ) )
                    cmd = "INSERT INTO hosts (" + keys + ") VALUES (" + values + ")"
                    if self.debug: print cmd
                    result = self.cur.execute(cmd)
                    #if result != 1: return -1, "Database Error while inserting at hosts table"

                    #insert numas
                    nb_numas = nb_cores = nb_ifaces = 0
                    for numa_dict in numa_list:
                        nb_numas += 1
                        interface_list = numa_dict.pop('interfaces', [])
                        core_list = numa_dict.pop('cores', [])
                        numa_dict['id'] = next_ids['numas'];   next_ids['numas'] += 1
                        numa_dict['host_id'] = uuid
                        keys    = ",".join(numa_dict.keys())
                        values  = ",".join( map(lambda x: "Null" if x is None else "'"+str(x)+"'", numa_dict.values() ) )
                        cmd = "INSERT INTO numas (" + keys + ") VALUES (" + values + ")"
                        if self.debug: print cmd
                        result = self.cur.execute(cmd)

                        #insert cores
                        for core_dict in core_list:
                            nb_cores += 1
                            core_dict['numa_id'] = numa_dict['id']
                            keys    = ",".join(core_dict.keys())
                            values  = ",".join( map(lambda x: "Null" if x is None else "'"+str(x)+"'", core_dict.values() ) )
                            cmd = "INSERT INTO resources_core (" + keys + ") VALUES (" + values + ")"
                            if self.debug: print cmd
                            result = self.cur.execute(cmd)

                        #insert ports
                        for port_dict in interface_list:
                            nb_ifaces += 1
                            sriov_list = port_dict.pop('sriovs', [])
                            port_dict['numa_id'] = numa_dict['id']
                            port_dict['id'] = port_dict['root_id'] = next_ids['resources_port']
                            next_ids['resources_port'] += 1
                            switch_port = port_dict.get('switch_port', None)
                            switch_dpid = port_dict.get('switch_dpid', None)
                            keys    = ",".join(port_dict.keys())
                            values  = ",".join( map(lambda x:  "Null" if x is None else "'"+str(x)+"'", port_dict.values() ) )
                            cmd = "INSERT INTO resources_port (" + keys + ") VALUES (" + values + ")"
                            if self.debug: print cmd
                            result = self.cur.execute(cmd)

                            #insert sriovs into port table
                            for sriov_dict in sriov_list:
                                sriov_dict['switch_port'] = switch_port
                                sriov_dict['switch_dpid'] = switch_dpid
                                sriov_dict['numa_id'] = port_dict['numa_id']
                                sriov_dict['Mbps'] = port_dict['Mbps']
                                sriov_dict['root_id'] = port_dict['id']
                                sriov_dict['id'] = next_ids['resources_port']
                                if "vlan" in sriov_dict:
                                    del sriov_dict["vlan"]
                                next_ids['resources_port'] += 1
                                keys    = ",".join(sriov_dict.keys())
                                values  = ",".join( map(lambda x:  "Null" if x is None else "'"+str(x)+"'", sriov_dict.values() ) )
                                cmd = "INSERT INTO resources_port (" + keys + ") VALUES (" + values + ")"
                                if self.debug: print cmd
                                result = self.cur.execute(cmd)

                    #inserting new log
                    cmd = "INSERT INTO logs (related,level,uuid,description) VALUES ('hosts','debug','%s','new host: %d numas, %d theads, %d ifaces')" % (uuid, nb_numas, nb_cores, nb_ifaces)
                    if self.debug: print cmd
                    result = self.cur.execute(cmd)                    

                    #inseted ok
                with self.con:
                    self.cur = self.con.cursor()
                    if self.debug: print "callproc('UpdateSwitchPort', () )"
                    self.cur.callproc('UpdateSwitchPort', () )

                if self.debug: print "getting host '%s'" % str(host_dict['uuid'])
                return self.get_host(host_dict['uuid'])
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "new_host DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def new_flavor(self, flavor_dict, tenant_id ):
        '''Add new flavor into the database. Create uuid if not provided
        Atributes
            flavor_dict: flavor dictionary with the key: value to insert. Must be valid flavors columns
            tenant_id: if not 'any', it matches this flavor/tenant inserting at tenants_flavors table
        Return: (result, data) where result can be
            negative: error at inserting. data contain text
            1, inserted, data contain inserted uuid flavor
        '''
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:
                    self.cur = self.con.cursor()

                    #create uuid if not provided
                    if 'uuid' not in flavor_dict:
                        uuid = flavor_dict['uuid'] = str(myUuid.uuid1()) # create_uuid
                    else: #check uuid is valid
                        uuid = str(flavor_dict['uuid'])
                    #    result, data = self.check_uuid(uuid)
                    #    if (result == 1):
                    #        return -1, "UUID '%s' already in use" % uuid

                    #inserting new uuid
                    cmd = "INSERT INTO uuids (uuid, used_at) VALUES ('%s','flavors')" % uuid
                    if self.debug: print cmd
                    self.cur.execute(cmd)

                    #insert in table flavor
                    keys    = ",".join(flavor_dict.keys())
                    values  = ",".join( map(lambda x:  "Null" if x is None else "'"+str(x)+"'", flavor_dict.values() ) )
                    cmd = "INSERT INTO flavors (" + keys + ") VALUES (" + values + ")"
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    #if result != 1: return -1, "Database Error while inserting at flavors table"

                    #insert tenants_flavors
                    if tenant_id != 'any':
                        cmd = "INSERT INTO tenants_flavors (tenant_id,flavor_id) VALUES ('%s','%s')" % (tenant_id, uuid)
                        if self.debug: print cmd
                        self.cur.execute(cmd)

                    #inserting new log
                    del flavor_dict['uuid']
                    if 'extended' in flavor_dict: del flavor_dict['extended'] #remove two many information
                    cmd = "INSERT INTO logs (related,level,uuid, tenant_id, description) VALUES ('flavors','debug','%s','%s',\"new flavor: %s\")" \
                        % (uuid, tenant_id, str(flavor_dict))
                    if self.debug: print cmd
                    self.cur.execute(cmd)                    

                    #inseted ok
                return 1, uuid
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "new_flavor DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e, "update", tenant_id)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
        
    def new_image(self, image_dict, tenant_id):
        '''Add new image into the database. Create uuid if not provided
        Atributes
            image_dict: image dictionary with the key: value to insert. Must be valid images columns
            tenant_id: if not 'any', it matches this image/tenant inserting at tenants_images table
        Return: (result, data) where result can be
            negative: error at inserting. data contain text
            1, inserted, data contain inserted uuid image
        '''
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:
                    self.cur = self.con.cursor()

                    #create uuid if not provided
                    if 'uuid' not in image_dict:
                        uuid = image_dict['uuid'] = str(myUuid.uuid1()) # create_uuid
                    else: #check uuid is valid
                        uuid = str(image_dict['uuid'])
                    #    result, data = self.check_uuid(uuid)
                    #    if (result == 1):
                    #        return -1, "UUID '%s' already in use" % uuid

                    #inserting new uuid
                    cmd = "INSERT INTO uuids (uuid, used_at) VALUES ('%s','images')" % uuid
                    if self.debug: print cmd
                    self.cur.execute(cmd)

                    #insert in table image
                    keys    = ",".join(image_dict.keys())
                    values  = ",".join( map(lambda x:  "Null" if x is None else "'"+str(x)+"'", image_dict.values() ) )
                    cmd = "INSERT INTO images (" + keys + ") VALUES (" + values + ")"
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    #if result != 1: return -1, "Database Error while inserting at images table"

                    #insert tenants_images
                    if tenant_id != 'any':
                        cmd = "INSERT INTO tenants_images (tenant_id,image_id) VALUES ('%s','%s')" % (tenant_id, uuid)
                        if self.debug: print cmd
                        self.cur.execute(cmd)

                    #inserting new log
                    cmd = "INSERT INTO logs (related,level,uuid, tenant_id, description) VALUES ('images','debug','%s','%s',\"new image: %s path: %s\")" % (uuid, tenant_id, image_dict['name'], image_dict['path'])
                    if self.debug: print cmd
                    self.cur.execute(cmd)                    

                    #inseted ok
                return 1, uuid
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "new_image DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e, "update", tenant_id)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
        
    def delete_image_flavor(self, item_type, item_id, tenant_id):
        '''deletes an image or flavor from database
        item_type must be a 'image' or 'flavor'
        item_id is the uuid
        tenant_id is the asociated tenant, can be 'any' with means all
        If tenan_id is not any, it deletes from tenants_images/flavors,
        which means this image/flavor is used by this tenant, and if success, 
        it tries to delete from images/flavors in case this is not public, 
        that only will success if image is private and not used by other tenants
        If tenant_id is any, it tries to delete from both tables at the same transaction
        so that image/flavor is completely deleted from all tenants or nothing
        '''
        for retry_ in range(0,2):
            deleted = -1
            deleted_item = -1
            result = (-HTTP_Internal_Server_Error, "internal error")
            cmd=""
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    cmd = "DELETE FROM tenants_%ss WHERE %s_id = '%s'" % (item_type, item_type, item_id)
                    if tenant_id != 'any':
                        cmd += " AND tenant_id = '%s'" % tenant_id
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    deleted = self.cur.rowcount
                    if tenant_id == 'any': #delete from images/flavors in the SAME transaction
                        cmd = "DELETE FROM %ss WHERE uuid = '%s'" % (item_type, item_id)
                        if self.debug: print cmd
                        self.cur.execute(cmd)
                        deleted = self.cur.rowcount
                        if deleted>=1:
                            #delete uuid
                            cmd = "DELETE FROM uuids WHERE uuid = '%s'" % item_id
                            if self.debug: print cmd
                            self.cur.execute(cmd)
                            #inserting new log
                            cmd = "INSERT INTO logs (related,level,uuid,tenant_id,description) \
                                   VALUES ('%ss','debug','%s','%s','delete %s completely')" % \
                                   (item_type, item_id, tenant_id, item_type)
                            if self.debug: print cmd
                            self.cur.execute(cmd)
                            return deleted, "%s '%s' completely deleted" % (item_type, item_id)
                        return 0, "%s '%s' not found" % (item_type, item_id)
                    
                    if deleted == 1:
                        #inserting new log
                        cmd = "INSERT INTO logs (related,level,uuid,tenant_id,description) \
                                VALUES ('%ss','debug','%s','%s','delete %s reference for this tenant')" % \
                                (item_type, item_id, tenant_id, item_type)
                        if self.debug: print cmd
                        self.cur.execute(cmd)

                        #commit transaction
                        self.cur.close()
                #if tenant!=any  delete from images/flavors in OTHER transaction. If fails is because dependencies so that not return error
                if deleted==1:
                    with self.con:
                        self.cur = self.con.cursor()

                        #delete image/flavor if not public
                        cmd = "DELETE FROM %ss WHERE uuid = '%s' AND public = 'no'" % (item_type, item_id)
                        if self.debug: print cmd
                        self.cur.execute(cmd)
                        deleted_item = self.cur.rowcount
                        if deleted_item == 1:
                            #delete uuid
                            cmd = "DELETE FROM uuids WHERE uuid = '%s'" % item_id
                            if self.debug: print cmd
                            self.cur.execute(cmd)
                            #inserting new log
                            cmd = "INSERT INTO logs (related,level,uuid,tenant_id,description) \
                                   VALUES ('%ss','debug','%s','%s','delete %s completely')" % \
                                   (item_type, item_id, tenant_id, item_type)
                            if self.debug: print cmd
                            self.cur.execute(cmd)
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "delete_%s DB Exception %d: %s" % (item_type, e.args[0], e.args[1])
                if deleted <0: result = self.format_error(e, "delete", "servers")
            finally:
                if deleted==1:
                    return 1, "%s '%s' from tenant '%s' %sdeleted" % \
                    (item_type, item_id, tenant_id, "completely " if deleted_item==1 else "")
                elif deleted==0:
                    return 0, "%s '%s' from tenant '%s' not found" % (item_type, item_id, tenant_id)
                else: 
                    if result[0]!=-HTTP_Request_Timeout or retry_==1: return result  
            
    def delete_row(self, table, uuid):
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:
                    #delete host
                    self.cur = self.con.cursor()
                    cmd = "DELETE FROM %s WHERE uuid = '%s'" % (table, uuid)
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    deleted = self.cur.rowcount
                    if deleted == 1:
                        #delete uuid
                        if table == 'tenants': tenant_str=uuid
                        else: tenant_str='Null'
                        self.cur = self.con.cursor()
                        cmd = "DELETE FROM uuids WHERE uuid = '%s'" % uuid
                        if self.debug: print cmd
                        self.cur.execute(cmd)
                        #inserting new log
                        cmd = "INSERT INTO logs (related,level,uuid,tenant_id,description) VALUES ('%s','debug','%s','%s','delete %s')" % (table, uuid, tenant_str, table[:-1])
                        if self.debug: print cmd
                        self.cur.execute(cmd)                    
                return deleted, table[:-1] + " '%s' %s" %(uuid, "deleted" if deleted==1 else "not found")
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "delete_row DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e, "delete", 'instances' if table=='hosts' or table=='tenants' else 'dependencies')
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def delete_row_by_key(self, table, key, value):
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:
                    #delete host
                    self.cur = self.con.cursor()
                    cmd = "DELETE FROM %s" % (table)
                    if key!=None:
                        if value!=None:
                            cmd += " WHERE %s = '%s'" % (key, value)
                        else:
                            cmd += " WHERE %s is null" % (key)
                    else: #delete all
                        pass
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    deleted = self.cur.rowcount
                    if deleted < 1:
                        return -1, 'Not found'
                        #delete uuid
                    return 0, deleted
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "delete_row_by_key DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e, "delete", 'instances' if table=='hosts' or table=='tenants' else 'dependencies')
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
                
    def delete_row_by_dict(self, **sql_dict):
        ''' Deletes rows from a table.
        Attribute sql_dir: dictionary with the following key: value
            'FROM': string of table name (Mandatory)
            'WHERE': dict of key:values, translated to key=value AND ... (Optional)
            'WHERE_NOT': dict of key:values, translated to key<>value AND ... (Optional)
            'WHERE_NOTNULL': (list or tuple of items that must not be null in a where ... (Optional)
            'LIMIT': limit of number of rows (Optional)
        Return: the (number of items deleted, descriptive test) if ok; (negative, descriptive text) if error
        '''
        #print sql_dict
        from_  = "FROM " + str(sql_dict['FROM'])
        #print 'from_', from_
        if 'WHERE' in sql_dict and len(sql_dict['WHERE']) > 0:
            w=sql_dict['WHERE']
            where_ = "WHERE " + " AND ".join(map( lambda x: str(x) + (" is Null" if w[x] is None else "='"+str(w[x])+"'"),  w.keys()) ) 
        else: where_ = ""
        if 'WHERE_NOT' in sql_dict and len(sql_dict['WHERE_NOT']) > 0: 
            w=sql_dict['WHERE_NOT']
            where_2 = " AND ".join(map( lambda x: str(x) + (" is not Null" if w[x] is None else "<>'"+str(w[x])+"'"),  w.keys()) )
            if len(where_)==0:   where_ = "WHERE " + where_2
            else:                where_ = where_ + " AND " + where_2
        if 'WHERE_NOTNULL' in sql_dict and len(sql_dict['WHERE_NOTNULL']) > 0: 
            w=sql_dict['WHERE_NOTNULL']
            where_2 = " AND ".join(map( lambda x: str(x) + " is not Null",  w) )
            if len(where_)==0:   where_ = "WHERE " + where_2
            else:                where_ = where_ + " AND " + where_2
        #print 'where_', where_
        limit_ = "LIMIT " + str(sql_dict['LIMIT']) if 'LIMIT' in sql_dict else ""
        #print 'limit_', limit_
        cmd =  " ".join( ("DELETE", from_, where_, limit_) )
        if self.debug: print cmd
        for retry_ in range(0,2):
            try:
                with self.con:
                    #delete host
                    self.cur = self.con.cursor()
                    self.cur.execute(cmd)
                    deleted = self.cur.rowcount
                return deleted, "%d deleted from %s" % (deleted, sql_dict['FROM'][:-1] )
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "delete_row_by_dict DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c =  self.format_error(e, "delete", 'dependencies')
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    
    def get_instance(self, instance_id):
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    #get INSTANCE
                    cmd = "SELECT uuid, name, description, progress, host_id, flavor_id, image_id, status, last_error, tenant_id, ram, vcpus, created_at \
                        FROM instances WHERE uuid = '" +  str(instance_id) +"'"
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    if self.cur.rowcount == 0 : return 0, "instance '" + str(instance_id) +"'not found."
                    instance = self.cur.fetchone()
                    #get networks
                    cmd = "SELECT uuid as iface_id, net_id, mac as mac_address, name, Mbps as bandwidth, vpci, model \
                        FROM ports WHERE type = 'instance:bridge' AND instance_id = '" + instance_id + "'"
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    if self.cur.rowcount > 0 :
                        instance['networks'] = self.cur.fetchall()

                    #get extended
                    extended = {}
                    #get devices
                    cmd = "SELECT type, vpci, image_id, xml,dev FROM instance_devices WHERE instance_id = '%s' " %  str(instance_id)
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    if self.cur.rowcount > 0 :
                        extended['devices'] = self.cur.fetchall()
                    #get numas
                    numas = []
                    cmd = "SELECT id, numa_socket as source FROM numas WHERE host_id = '" + str(instance['host_id']) + "'"
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    host_numas = self.cur.fetchall()
                    print 'host_numas', host_numas
                    for k in host_numas:
                        numa_id = str(k['id'])
                        numa_dict ={}
                        #get memory
                        cmd = "SELECT consumed FROM resources_mem WHERE instance_id = '%s' AND numa_id = '%s'" % ( instance_id, numa_id)
                        if self.debug: print cmd
                        self.cur.execute(cmd)
                        if self.cur.rowcount > 0:
                            mem_dict = self.cur.fetchone()
                            numa_dict['memory'] = mem_dict['consumed']
                        #get full cores
                        cursor2 = self.con.cursor()
                        cmd = "SELECT core_id, paired, MIN(v_thread_id) as v1, MAX(v_thread_id) as v2, COUNT(instance_id) as nb, MIN(thread_id) as t1, MAX(thread_id) as t2 FROM resources_core WHERE instance_id = '%s' AND numa_id = '%s' GROUP BY core_id,paired" % ( str(instance_id), numa_id) 
                        if self.debug: print cmd
                        cursor2.execute(cmd)
                        core_list = [];     core_source = []
                        paired_list = [];   paired_source = []
                        thread_list = [];   thread_source = []
    #                     print '***************** antes if '+str(cursor2.rowcount) 
                        if cursor2.rowcount > 0: 
                            cores = cursor2.fetchall()
    #                         print 'cores', cores
                            for core in cores:
                                if core[4] == 2: #number of used threads from core
                                    if core[3] == core[2]:  #only one thread asigned to VM, so completely core
                                        core_list.append(core[2])
                                        core_source.append(core[5])
                                    elif core[1] == 'Y':
                                        paired_list.append(core[2:4])
                                        paired_source.append(core[5:7])
                                    else:
                                        thread_list.extend(core[2:4])
                                        thread_source.extend(core[5:7])

                                else:
                                    thread_list.append(core[2])
                                    thread_source.append(core[5])
                            if len(core_list) > 0:
                                numa_dict['cores'] = len(core_list)
                                numa_dict['cores-id'] = core_list
                                numa_dict['cores-source'] = core_source
                            if len(paired_list) > 0:
                                numa_dict['paired-threads'] = len(paired_list)
                                numa_dict['paired-threads-id'] = paired_list
                                numa_dict['paired-threads-source'] = paired_source
                            if len(thread_list) > 0:
                                numa_dict['threads'] = len(thread_list)
                                numa_dict['threads-id'] = thread_list
                                numa_dict['threads-source'] = thread_source

                        #get dedicated ports and SRIOV
                        cmd = "SELECT port_id as iface_id, p.vlan as vlan, p.mac as mac_address, net_id, if(model='PF','yes',if(model='VF','no','yes:sriov')) as dedicated,\
                            rp.Mbps as bandwidth, name, vpci, pci as source \
                            FROM resources_port as rp join ports as p on port_id=uuid  WHERE p.instance_id = '%s' AND numa_id = '%s' and p.type='instance:data'" % (instance_id, numa_id) 
                        if self.debug: print cmd
                        self.cur.execute(cmd)
                        if self.cur.rowcount > 0: 
                            numa_dict['interfaces'] = self.cur.fetchall()
                            print 'interfaces', numa_dict

                        if len(numa_dict) > 0 : 
                            numa_dict['source'] = k['source'] #numa socket
                            numas.append(numa_dict)

                    if len(numas) > 0 :  extended['numas'] = numas
                    if len(extended) > 0 :  instance['extended'] = extended
                    af.DeleteNone(instance)
                    return 1, instance
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "get_instance DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
        
    def get_numas(self, requirements, prefered_host_id=None, only_of_ports=True):
        '''Obtain a valid NUMA/HOST for deployment a VM
        requirements: contain requirement regarding:
            requirements['ram']: Non huge page memory in MB; 0 to skip 
            requirements['vcpus']: Non isolated cpus; 0 to skip 
            requirements['numa']: Requiremets to be fixed in ONE Numa node
                requirements['numa']['memory']: Huge page memory in GB at ; 0 for any 
                requirements['numa']['proc_req_type']: Type of processor, cores or threads 
                requirements['numa']['proc_req_nb']: Number of isolated cpus  
                requirements['numa']['port_list']: Physical NIC ports list ; [] for any 
                requirements['numa']['sriov_list']: Virtual function NIC ports list ; [] for any
        prefered_host_id: if not None return this host if it match 
        only_of_ports: if True only those ports conected to the openflow (of) are valid,
            that is, with switch_port information filled; if False, all NIC ports are valid. 
        Return a valid numa and host
        '''
         
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:              
#                     #Find numas of prefered host
#                     prefered_numas = ()
#                     if prefered_host_id != None:
#                         self.cur = self.con.cursor()
#                         self.cur.execute("SELECT id FROM numas WHERE host_id='%s'" + prefered_host_id)
#                         prefered_numas = self.cur.fetchall()
#                         self.cur.close()
                        
                    #Find valid host for the ram and vcpus
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    cmd = "CALL GetHostByMemCpu(%s, %s)" % (str(requirements['ram']), str(requirements['vcpus']))
                    if self.debug: print cmd   
                    self.cur.callproc('GetHostByMemCpu', (str(requirements['ram']), str(requirements['vcpus'])) )
                    valid_hosts = self.cur.fetchall()
                    self.cur.close()   
                    self.cur = self.con.cursor()
                    match_found = False
                    if len(valid_hosts)<=0:
                        error_text = 'No room at data center. Can not find a host with %s MB memory and %s cpus available' % (str(requirements['ram']), str(requirements['vcpus'])) 
                        print  error_text
                        return -1, error_text
                    
                    #elif req_numa != None:
                    #Find valid numa nodes for memory requirements
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    cmd = "CALL GetNumaByMemory(%s)" % str(requirements['numa']['memory'])
                    if self.debug: print cmd   
                    self.cur.callproc('GetNumaByMemory', (requirements['numa']['memory'],) )
                    valid_for_memory = self.cur.fetchall()
                    self.cur.close()   
                    self.cur = self.con.cursor()
                    if len(valid_for_memory)<=0:
                        error_text = 'No room at data center. Can not find a host with %s GB Hugepages memory available' % str(requirements['numa']['memory']) 
                        print  error_text
                        return -1, error_text

                    #Find valid numa nodes for processor requirements
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    if requirements['numa']['proc_req_type'] == 'threads':
                        cpu_requirement_text='cpu-threads'
                        cmd = "CALL GetNumaByThread(%s)" % str(requirements['numa']['proc_req_nb'])
                        if self.debug: print cmd 
                        self.cur.callproc('GetNumaByThread', (requirements['numa']['proc_req_nb'],) )
                    else:
                        cpu_requirement_text='cpu-cores'
                        cmd = "CALL GetNumaByCore(%s)" % str(requirements['numa']['proc_req_nb'])
                        if self.debug: print cmd 
                        self.cur.callproc('GetNumaByCore', (requirements['numa']['proc_req_nb'],) )
                    valid_for_processor = self.cur.fetchall()
                    self.cur.close()   
                    self.cur = self.con.cursor()
                    if len(valid_for_processor)<=0:
                        error_text = 'No room at data center. Can not find a host with %s %s available' % (str(requirements['numa']['proc_req_nb']),cpu_requirement_text)  
                        print  error_text
                        return -1, error_text

                    #Find the numa nodes that comply for memory and processor requirements
                    #sorting from less to more memory capacity
                    valid_numas = []
                    for m_numa in valid_for_memory:
                        numa_valid_for_processor = False
                        for p_numa in valid_for_processor:
                            if m_numa['numa_id'] == p_numa['numa_id']:
                                numa_valid_for_processor = True
                                break
                        numa_valid_for_host = False
                        prefered_numa = False
                        for p_host in valid_hosts:
                            if m_numa['host_id'] == p_host['uuid']:
                                numa_valid_for_host = True
                                if p_host['uuid'] == prefered_host_id:
                                    prefered_numa = True
                                break
                        if numa_valid_for_host and numa_valid_for_processor:
                            if prefered_numa:
                                valid_numas.insert(0, m_numa['numa_id'])
                            else:
                                valid_numas.append(m_numa['numa_id'])
                    if len(valid_numas)<=0:
                        error_text = 'No room at data center. Can not find a host with %s MB hugepages memory and %s %s available in the same numa' %\
                            (requirements['numa']['memory'], str(requirements['numa']['proc_req_nb']),cpu_requirement_text)  
                        print  error_text
                        return -1, error_text
                    
    #                 print 'Valid numas list: '+str(valid_numas)

                    #Find valid numa nodes for interfaces requirements
                    #For each valid numa we will obtain the number of available ports and check if these are valid          
                    match_found = False    
                    for numa_id in valid_numas:
    #                     print 'Checking '+str(numa_id)
                        match_found = False
                        self.cur = self.con.cursor(mdb.cursors.DictCursor)
                        if only_of_ports:
                            cmd="CALL GetAvailablePorts(%s)" % str(numa_id) 
                            if self.debug: print cmd
                            self.cur.callproc('GetAvailablePorts', (numa_id,) )
                        else:
                            cmd="CALL GetAllAvailablePorts(%s)" % str(numa_id) 
                            if self.debug: print cmd
                            self.cur.callproc('GetAllAvailablePorts', (numa_id,) )
                        available_ports = self.cur.fetchall()
                        self.cur.close()   
                        self.cur = self.con.cursor()

                        #Set/reset reservations
                        for port in available_ports:
                            port['Mbps_reserved'] = 0
                            port['SRIOV_reserved'] = 0

                        #Try to allocate physical ports
                        physical_ports_found = True
                        for iface in requirements['numa']['port_list']:
    #                         print '\t\tchecking iface: '+str(iface)
                            portFound = False
                            for port in available_ports:
    #                             print '\t\t\tfor port: '+str(port)
                                #If the port is not empty continue
                                if port['Mbps_free'] != port['Mbps'] or port['Mbps_reserved'] != 0:
    #                                 print '\t\t\t\t Not empty port'
                                    continue;
                                #If the port speed is not enough continue
                                if port['Mbps'] < iface['bandwidth']:
    #                                 print '\t\t\t\t Not enough speed'
                                    continue;

                                #Otherwise this is a valid port  
                                port['Mbps_reserved'] = port['Mbps']
                                port['SRIOV_reserved'] = 0
                                iface['port_id'] = port['port_id']
                                iface['vlan'] = None
                                iface['mac'] = port['mac']
                                iface['switch_port'] = port['switch_port']
    #                             print '\t\t\t\t Dedicated port found '+str(port['port_id'])
                                portFound = True
                                break;

                            #if all ports have been checked and no match has been found
                            #this is not a valid numa
                            if not portFound:
    #                             print '\t\t\t\t\tAll ports have been checked and no match has been found for numa '+str(numa_id)+'\n\n'
                                physical_ports_found = False
                                break

                        #if there is no match continue checking the following numa
                        if not physical_ports_found:
                            continue

                        #Try to allocate SR-IOVs
                        sriov_ports_found = True
                        for iface in requirements['numa']['sriov_list']:
    #                         print '\t\tchecking iface: '+str(iface)
                            portFound = False
                            for port in available_ports:
    #                             print '\t\t\tfor port: '+str(port)
                                #If there are not available SR-IOVs continue
                                if port['availableSRIOV'] - port['SRIOV_reserved'] <= 0:
    #                                 print '\t\t\t\t Not enough SR-IOV'
                                    continue;
                                #If the port free speed is not enough continue
                                if port['Mbps_free'] - port['Mbps_reserved'] < iface['bandwidth']:
    #                                 print '\t\t\t\t Not enough speed'
                                    continue;

                                #Otherwise this is a valid port  
                                port['Mbps_reserved'] += iface['bandwidth']
                                port['SRIOV_reserved'] += 1
    #                             print '\t\t\t\t SR-IOV found '+str(port['port_id'])
                                iface['port_id'] = port['port_id']
                                iface['vlan'] = None
                                iface['mac'] = port['mac']
                                iface['switch_port'] = port['switch_port']
                                portFound = True
                                break;

                            #if all ports have been checked and no match has been found
                            #this is not a valid numa
                            if not portFound:
    #                             print '\t\t\t\t\tAll ports have been checked and no match has been found for numa '+str(numa_id)+'\n\n'
                                sriov_ports_found = False
                                break

                        #if there is no match continue checking the following numa
                        if not sriov_ports_found:
                            continue


                        if sriov_ports_found and physical_ports_found:
                            match_found = True
                            break

                    if not match_found:
                        error_text = 'No room at data center. Can not find a host with the required hugepages, vcpus and interfaces'  
                        print  error_text
                        return -1, error_text

                    print 'Full match found in numa '+str(numa_id)

                for numa in valid_for_processor:
                    if numa_id==numa['numa_id']:
                        host_id=numa['host_id']
                        break
                return 0, {'numa_id':numa_id, 'host_id': host_id, }
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "get_numas DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def new_instance(self, instance_dict, nets):
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:
                    self.cur = self.con.cursor()

                    #create uuid if not provided
                    if 'uuid' not in instance_dict:
                        uuid = instance_dict['uuid'] = str(myUuid.uuid1()) # create_uuid
                    else: #check uuid is valid
                        uuid = str(instance_dict['uuid'])


                    #inserting new uuid
                    cmd = "INSERT INTO uuids (uuid, root_uuid, used_at) VALUES ('%s','%s', 'instances')" % (uuid, uuid)
                    if self.debug: print cmd
                    self.cur.execute(cmd)

                    #insert in table instance
                    extended = instance_dict.pop('extended', None);
                    bridgedifaces = instance_dict.pop('bridged-ifaces', () );

                    keys    = ",".join(instance_dict.keys())
                    values  = ",".join( map(lambda x: "Null" if x is None else "'"+str(x)+"'", instance_dict.values() ) )
                    cmd = "INSERT INTO instances (" + keys + ") VALUES (" + values + ")"
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    #if result != 1: return -1, "Database Error while inserting at instances table"

                    #insert resources
                    nb_bridge_ifaces = nb_cores = nb_ifaces = nb_numas = 0
                    #insert bridged_ifaces
                    for iface in bridgedifaces:
                        #generate and insert a iface uuid
                        iface['uuid'] = str(myUuid.uuid1()) # create_uuid
                        cmd = "INSERT INTO uuids (uuid, root_uuid, used_at) VALUES ('%s','%s', 'ports')" % (iface['uuid'], uuid)
                        if self.debug: print cmd
                        self.cur.execute(cmd)
                        #insert iface
                        iface['instance_id'] = uuid
                        iface['type'] = 'instance:bridge'
                        if 'name' not in iface: iface['name']="br"+str(nb_bridge_ifaces)
                        iface['Mbps']=iface.pop('bandwidth', None)
                        if 'mac_address' not in iface:
                            iface['mac'] = af.gen_random_mac()
                        else:
                            iface['mac'] = iface['mac_address']
                            del iface['mac_address']
                        #iface['mac']=iface.pop('mac_address', None)  #for leaving mac generation to libvirt
                        keys    = ",".join(iface.keys())
                        values  = ",".join( map(lambda x: "Null" if x is None else "'"+str(x)+"'", iface.values() ) )
                        cmd = "INSERT INTO ports (" + keys + ") VALUES (" + values + ")"
                        if self.debug: print cmd
                        self.cur.execute(cmd)
                        nb_bridge_ifaces += 1

                    if extended is not None:
                        if 'numas' not in extended or extended['numas'] is None: extended['numas'] = ()
                        for numa in extended['numas']:
                            nb_numas += 1
                            #cores
                            if 'cores' not in numa or numa['cores'] is None: numa['cores'] = ()
                            for core in numa['cores']:
                                nb_cores += 1
                                cmd = "UPDATE resources_core SET instance_id='%s'%s%s WHERE id='%s'" \
                                    % (uuid, \
                                    (",v_thread_id='" + str(core['vthread']) + "'") if 'vthread' in core else '', \
                                    (",paired='"      + core['paired']  + "'") if 'paired' in core else '', \
                                    core['id'] )
                                if self.debug: print cmd
                                self.cur.execute(cmd)
                            #interfaces
                            if 'interfaces' not in numa or numa['interfaces'] is None: numa['interfaces'] = ()
                            for iface in numa['interfaces']:
                                #generate and insert an uuid; iface[id]=iface_uuid; iface[uuid]= net_id
                                iface['id'] = str(myUuid.uuid1()) # create_uuid
                                cmd = "INSERT INTO uuids (uuid, root_uuid, used_at) VALUES ('%s','%s', 'ports')" % (iface['id'], uuid)
                                if self.debug: print cmd
                                self.cur.execute(cmd)
                                nb_ifaces += 1
                                mbps_=("'"+str(iface['Mbps_used'])+"'") if 'Mbps_used' in iface and iface['Mbps_used'] is not None else "Mbps"
                                if iface["dedicated"]=="yes": 
                                    iface_model="PF"
                                elif iface["dedicated"]=="yes:sriov": 
                                    iface_model="VFnotShared"
                                elif iface["dedicated"]=="no": 
                                    iface_model="VF"
                                #else error
                                INSERT=(iface['mac_address'], iface['switch_port'], iface.get('vlan',None), 'instance:data', iface['Mbps_used'], iface['id'],
                                        uuid, instance_dict['tenant_id'], iface.get('name',None), iface.get('vpci',None), iface.get('uuid',None), iface_model )
                                cmd = "INSERT INTO ports (mac,switch_port,vlan,type,Mbps,uuid,instance_id,tenant_id,name,vpci,net_id, model) " + \
                                       " VALUES (" + ",".join(map(lambda x: 'Null' if x is None else "'"+str(x)+"'", INSERT )) + ")"
                                if self.debug: print cmd
                                self.cur.execute(cmd)
                                if 'uuid' in iface:
                                    nets.append(iface['uuid'])

                                cmd = "UPDATE resources_port SET instance_id='%s', port_id='%s',Mbps_used=%s WHERE id='%s'" \
                                    % (uuid, iface['id'], mbps_, iface['port_id'])
                                #if Mbps_used not suply, set the same value of 'Mpbs', that is the total
                                if self.debug: print cmd
                                self.cur.execute(cmd)
                            #memory
                            if 'memory' in numa and numa['memory'] is not None and numa['memory']>0:
                                cmd = "INSERT INTO resources_mem (numa_id, instance_id, consumed) VALUES ('%s','%s','%s')" % (numa['numa_id'], uuid, numa['memory'])
                                if self.debug: print cmd
                                self.cur.execute(cmd)
                        if 'devices' not in extended or extended['devices'] is None: extended['devices'] = ()
                        for device in extended['devices']:
                            if 'vpci' in device:    vpci = "'" + device['vpci'] + "'"
                            else:                   vpci = 'Null'
                            if 'image_id' in device: image_id = "'" + device['image_id'] + "'"
                            else:                    image_id = 'Null'
                            if 'xml' in device: xml = "'" + device['xml'] + "'"
                            else:                    xml = 'Null'
                            if 'dev' in device: dev = "'" + device['dev'] + "'"
                            else:                    dev = 'Null'
                            cmd = "INSERT INTO instance_devices (type, instance_id, image_id, vpci, xml, dev) VALUES ('%s','%s', %s, %s, %s, %s)" % \
                                (device['type'], uuid, image_id, vpci, xml, dev)
                            if self.debug: print cmd
                            self.cur.execute(cmd)
                    #inserting new log
                    cmd = "INSERT INTO logs (related,level,uuid,description) VALUES ('instances','debug','%s','new instance: %d numas, %d theads, %d ifaces %d bridge_ifaces')" % (uuid, nb_numas, nb_cores, nb_ifaces, nb_bridge_ifaces)
                    if self.debug: print cmd
                    self.cur.execute(cmd)                    

                    #inseted ok
                return 1, uuid 
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "new_instance DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def delete_instance(self, instance_id, tenant_id, net_list, logcause="requested by http"):
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    #get INSTANCE
                    cmd = "SELECT uuid FROM instances WHERE uuid='%s' AND tenant_id='%s'" % (instance_id, tenant_id)
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    if self.cur.rowcount == 0 : return 0, "instance %s not found in tenant %s" % (instance_id, tenant_id)

                    #delete bridged ifaces, instace_devices, resources_mem; done by database: FOREIGN KEY DELTETE CASCADE

                    #update resources port, first get nets afected
                    cmd = "SELECT DISTINCT net_id from ports WHERE instance_id = '%s' AND net_id is not Null AND type='instance:data'" % instance_id
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    net_list__ = self.cur.fetchall()
                    for net in net_list__:
                        net_list.append(net[0])

                    cmd = "UPDATE resources_port SET instance_id=Null, port_id=Null, Mbps_used='0' WHERE instance_id = '%s'" % instance_id
                    if self.debug: print cmd
                    self.cur.execute(cmd)

                    #update resources core
                    cmd = "UPDATE resources_core SET instance_id=Null, v_thread_id=Null, paired='N' WHERE instance_id = '%s'" % instance_id
                    if self.debug: print cmd
                    self.cur.execute(cmd)

                    #delete all related uuids
                    cmd = "DELETE FROM uuids WHERE root_uuid='%s'" % instance_id
                    if self.debug: print cmd
                    self.cur.execute(cmd)

                    #insert log
                    cmd = "INSERT INTO logs (related,level,uuid,description) VALUES ('instances','debug','%s','delete instance %s')" % (instance_id, logcause)
                    if self.debug: print cmd
                    self.cur.execute(cmd)                    

                    #delete instance
                    cmd = "DELETE FROM instances WHERE uuid='%s' AND tenant_id='%s'" % (instance_id, tenant_id)
                    self.cur.execute(cmd)
                    return 1, "instance %s from tenant %s DELETED" % (instance_id, tenant_id)

            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "delete_instance DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def get_ports(self, WHERE):
        ''' Obtain ports using the WHERE filtering.
        Attributes:
            'where_': dict of key:values, translated to key=value AND ... (Optional)
        Return: a list with dictionarys at each row
        '''
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:

                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    select_ = "SELECT uuid,'ACTIVE' as status,admin_state_up,name,net_id,\
                        tenant_id,type,mac,vlan,switch_port,instance_id,Mbps FROM ports "

                    if WHERE is None or len(WHERE) == 0:  where_ = ""
                    else:
                        where_ = "WHERE " + " AND ".join(map( lambda x: str(x) + (" is Null" if WHERE[x] is None else "='"+str(WHERE[x])+"'"),  WHERE.keys()) ) 
                    limit_ = "LIMIT 100"
                    cmd =  " ".join( (select_, where_, limit_) )
    #                print "SELECT multiple de instance_ifaces, iface_uuid, external_ports" #print cmd
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    ports = self.cur.fetchall()
                    if self.cur.rowcount>0:  af.DeleteNone(ports)
                    return self.cur.rowcount, ports
    #                return self.get_table(FROM=from_, SELECT=select_,WHERE=where_,LIMIT=100)
            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "get_ports DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
        
    def check_target_net(self, net_id, tenant_id, port_type):
        '''check if valid attachement of a port into a target net
        Attributes:
            net_id: target net uuid
            tenant_id: client where tenant belongs. Not used in this version
            port_type: string with the option 'instance:bridge', 'instance:data', 'external'
        Return: 
            (0,net_dict) if ok,   where net_dict contain 'uuid','type','vlan', ...
            (negative,string-error) if error
        '''
        for retry_ in range(0,2):
            cmd=""
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    cmd = "SELECT * FROM nets WHERE uuid='%s'" % net_id
                    if self.debug: print cmd
                    self.cur.execute(cmd)
                    if self.cur.rowcount == 0 : return -1, "network_id %s does not match any net" % net_id
                    net = self.cur.fetchone()

            except (mdb.Error, AttributeError), e:
                if not self.debug: print cmd
                print "check_target_net DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
        #check permissions
        if tenant_id is not None and tenant_id is not "admin":
            if net['tenant_id']==tenant_id and net['shared']=='false':
                return -1, "needed admin privileges to attach to the net %s" % net_id
        #check types
        if (net['type'] in ('p2p','data') and 'port_type' == 'instance:bridge') or \
            (net['type'] in ('bridge_data','bridge_man') and 'port_type' != 'instance:bridge') :
            return -1, "can not attach a port of type %s into a net of type %s" % (port_type, net['type'])
        if net['type'] == 'p2p':
            #look how many 
            nb_ports, data = self.get_ports( {'net_id':net_id} )
            if nb_ports<0: return -1, data
            elif nb_ports >=2: return -1, "net of type p2p already contain two ports attached. No room for another"
            
        return 0, net

if __name__ == "__main__":
    print "Hello World"

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
NFVO DB engine. It implements all the methods to interact with the Openmano Database
'''
__author__="Alfonso Tierno, Gerardo Garcia"
__date__ ="$28-aug-2014 10:05:01$"

import MySQLdb as mdb
import uuid as myUuid
from utils import auxiliary_functions as af
import json

HTTP_Bad_Request = 400
HTTP_Unauthorized = 401 
HTTP_Not_Found = 404 
HTTP_Method_Not_Allowed = 405 
HTTP_Request_Timeout = 408
HTTP_Conflict = 409
HTTP_Service_Unavailable = 503 
HTTP_Internal_Server_Error = 500 

class nfvo_db():
    def __init__(self):
        #initialization
        return

    def connect(self, host=None, user=None, passwd=None, database=None):
        '''Connect to specific data base. 
        The first time a valid host, user, passwd and database must be provided,
        Following calls can skip this parameters
        '''
        try:
            if host     is not None: self.host = host
            if user     is not None: self.user = user
            if passwd   is not None: self.passwd = passwd
            if database is not None: self.database = database

            self.con = mdb.connect(self.host, self.user, self.passwd, self.database)
            print "DB: connected to %s@%s -> %s" % (self.user, self.host, self.database)
            return 0
        except mdb.Error, e:
            print "nfvo_db.connect Error connecting to DB %s@%s -> %s Error %d: %s" % (self.user, self.host, self.database, e.args[0], e.args[1])
            return -1
        
    def get_db_version(self):
        ''' Obtain the database schema version.
        Return: (negative, text) if error or version 0.0 where schema_version table is missing
                (version_int, version_text) if ok
        '''
        cmd = "SELECT version_int,version,openmano_ver FROM schema_version"
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    #print cmd
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
                #print cmd
                print "get_db_version DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def disconnect(self):
        '''disconnect from specific data base'''
        try:
            self.con.close()
            del self.con
        except mdb.Error, e:
            print "Error disconnecting from DB: Error %d: %s" % (e.args[0], e.args[1])
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
            elif command=="delete":  return -HTTP_Bad_Request, "Resource is not free. There are %s that prevent deleting it." % extra
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

    def __remove_quotes(self, data):
        '''remove single quotes ' of any string content of data dictionary'''
        for k,v in data.items():
            if type(v) == str:
                if "'" in v: 
                    data[k] = data[k].replace("'","_")
    
    def __update_rows(self, table, UPDATE, WHERE, log=False):
        ''' Update one or several rows into a table.
        Atributes
            UPDATE: dictionary with the key: value to change
            table: table where to update
            WHERE: dictionary of elements to update
        Return: (result, descriptive text) where result indicates the number of updated files, negative if error
        '''
        self.__remove_quotes(UPDATE)
                #gettting uuid 
        uuid = WHERE['uuid'] if 'uuid' in WHERE else None

        cmd= "UPDATE " + table +" SET " + \
            ",".join(map(lambda x: str(x)+ ('=Null' if UPDATE[x] is None else "='"+ str(UPDATE[x]) +"'"  ),   UPDATE.keys() )) + \
            " WHERE " + " and ".join(map(lambda x: str(x)+ (' is Null' if WHERE[x] is None else"='"+str(WHERE[x])+"'" ),  WHERE.keys() ))
        print cmd
        self.cur.execute(cmd) 
        nb_rows = self.cur.rowcount
        if nb_rows > 0 and log:                
            #inserting new log
            if uuid is None: uuid_k = uuid_v = ""
            else: uuid_k=",uuid"; uuid_v=",'" + str(uuid) + "'"
            cmd = "INSERT INTO logs (related,level%s,description) VALUES ('%s','debug'%s,\"updating %d entry %s\")" \
                % (uuid_k, table, uuid_v, nb_rows, (str(UPDATE)).replace('"','-')  )
            print cmd
            self.cur.execute(cmd)                    
        return nb_rows, "%d updated from %s" % (nb_rows, table[:-1] )
    
    def _new_row_internal(self, table, INSERT, tenant_id=None, add_uuid=False, root_uuid=None, log=False):
        ''' Add one row into a table. It DOES NOT begin or end the transaction, so self.con.cursor must be created
        Attribute 
            INSERT: dictionary with the key: value to insert
            table: table where to insert
            tenant_id: only useful for logs. If provided, logs will use this tenant_id
            add_uuid: if True, it will create an uuid key entry at INSERT if not provided
        It checks presence of uuid and add one automatically otherwise
        Return: (result, uuid) where result can be 0 if error, or 1 if ok
        '''

        if add_uuid:
            #create uuid if not provided
            if 'uuid' not in INSERT:
                uuid = INSERT['uuid'] = str(myUuid.uuid1()) # create_uuid
            else: 
                uuid = str(INSERT['uuid'])
        else:
            uuid=None
        if add_uuid:
            #defining root_uuid if not provided
            if root_uuid is None:
                root_uuid = uuid
            #inserting new uuid
            cmd = "INSERT INTO uuids (uuid, root_uuid, used_at) VALUES ('%s','%s','%s')" % (uuid, root_uuid, table)
            print cmd
            self.cur.execute(cmd)
        #insertion
        cmd= "INSERT INTO " + table +" (" + \
            ",".join(map(str, INSERT.keys() ))   + ") VALUES(" + \
            ",".join(map(lambda x: 'Null' if x is None else "'"+str(x)+"'", INSERT.values() )) + ")"
        print cmd
        self.cur.execute(cmd)
        nb_rows = self.cur.rowcount
        #inserting new log
        if nb_rows > 0 and log:                
            if add_uuid: del INSERT['uuid']
            if uuid is None: uuid_k = uuid_v = ""
            else: uuid_k=",uuid"; uuid_v=",'" + str(uuid) + "'"
            if tenant_id is None: tenant_k = tenant_v = ""
            else: tenant_k=",nfvo_tenant_id"; tenant_v=",'" + str(tenant_id) + "'"
            cmd = "INSERT INTO logs (related,level%s%s,description) VALUES ('%s','debug'%s%s,\"new %s %s\")" \
                % (uuid_k, tenant_k, table, uuid_v, tenant_v, table[:-1], str(INSERT).replace('"','-'))
            print cmd
            self.cur.execute(cmd)                    
        return nb_rows, uuid

    def __get_rows(self,table,uuid):
        self.cur.execute("SELECT * FROM " + str(table) +" where uuid='" + str(uuid) + "'")
        rows = self.cur.fetchall()
        return self.cur.rowcount, rows
    
    def new_row(self, table, INSERT, tenant_id=None, add_uuid=False, log=False):
        ''' Add one row into a table.
        Attribute 
            INSERT: dictionary with the key: value to insert
            table: table where to insert
            tenant_id: only useful for logs. If provided, logs will use this tenant_id
            add_uuid: if True, it will create an uuid key entry at INSERT if not provided
        It checks presence of uuid and add one automatically otherwise
        Return: (result, uuid) where result can be 0 if error, or 1 if ok
        '''
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    return self._new_row_internal(table, INSERT, tenant_id, add_uuid, None, log)
                    
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.new_row DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def update_rows(self, table, UPDATE, WHERE, log=False):
        ''' Update one or several rows into a table.
        Atributes
            UPDATE: dictionary with the key: value to change
            table: table where to update
            WHERE: dictionary of elements to update
        Return: (result, descriptive text) where result indicates the number of updated files
        '''
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    return self.__update_rows(table, UPDATE, WHERE, log)
                    
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.update_rows DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def delete_row(self, table, uuid, tenant_id=None, log=True):
        for retry_ in range(0,2):
            try:
                with self.con:
                    #delete host
                    self.cur = self.con.cursor()
                    cmd = "DELETE FROM %s WHERE uuid = '%s'" % (table, uuid)
                    print cmd
                    self.cur.execute(cmd)
                    deleted = self.cur.rowcount
                    if deleted == 1:
                        #delete uuid
                        if table == 'tenants': tenant_str=uuid
                        elif tenant_id:
                            tenant_str = tenant_id
                        else: 
                            tenant_str = 'Null'
                        self.cur = self.con.cursor()
                        cmd = "DELETE FROM uuids WHERE root_uuid = '%s'" % uuid
                        print cmd
                        self.cur.execute(cmd)
                        #inserting new log
                        if log:
                            cmd = "INSERT INTO logs (related,level,uuid,nfvo_tenant_id,description) VALUES ('%s','debug','%s','%s','delete %s')" % (table, uuid, tenant_str, table[:-1])
                            print cmd
                            self.cur.execute(cmd)                    
                return deleted, table[:-1] + " '%s' %s" %(uuid, "deleted" if deleted==1 else "not found")
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.delete_row DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c =  self.format_error(e, "delete", 'instances' if table=='hosts' or table=='tenants' else 'dependencies')
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
        print cmd
        for retry_ in range(0,2):
            try:
                with self.con:
                    #delete host
                    self.cur = self.con.cursor()
                    self.cur.execute(cmd)
                    deleted = self.cur.rowcount
                return deleted, "%d deleted from %s" % (deleted, sql_dict['FROM'][:-1] )
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.delete_row DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c =  self.format_error(e, "delete", 'dependencies')
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def get_rows(self,table,uuid):
        '''get row from a table based on uuid'''
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    self.cur.execute("SELECT * FROM " + str(table) +" where uuid='" + str(uuid) + "'")
                    rows = self.cur.fetchall()
                    return self.cur.rowcount, rows
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.get_rows DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
    
    def get_table(self, **sql_dict):
        ''' Obtain rows from a table.
        Attribute sql_dir: dictionary with the following key: value
            'SELECT': (list or tuple of fields to retrieve) (by default all)
            'FROM': string of table name (Mandatory)
            'WHERE': dict of key:values, translated to key=value AND ... (Optional)
            'WHERE_NOT': dict of key:values, translated to key<>value AND ... (Optional)
            'WHERE_NOTNULL': (list or tuple of items that must not be null in a where ... (Optional)
            'LIMIT': limit of number of rows (Optional)
        Return: a list with dictionaries at each row
        '''
        #print sql_dict
        select_= "SELECT " + ("*" if 'SELECT' not in sql_dict else ",".join(map(str,sql_dict['SELECT'])) )
        #print 'select_', select_
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
        cmd =  " ".join( (select_, from_, where_, limit_) )
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    print cmd
                    self.cur.execute(cmd)
                    rows = self.cur.fetchall()
                    return self.cur.rowcount, rows
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.get_table DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def get_table_by_uuid_name(self, table, uuid_name, error_item_text=None, allow_serveral=False):
        ''' Obtain One row from a table based on name or uuid.
        Attribute:
            table: string of table name
            uuid_name: name or uuid. If not uuid format is found, it is considered a name
            allow_severeral: if False return ERROR if more than one row are founded 
            error_item_text: in case of error it identifies the 'item' name for a proper output text 
        Return: if allow_several==False, a dictionary with this row, or error if no item is found or more than one is found
                if allow_several==True, a list of dictionaries with the row or rows, error if no item is found
        '''

        if error_item_text==None:
            error_item_text = table
        what = 'uuid' if af.check_valid_uuid(uuid_name) else 'name'
        cmd =  " SELECT * FROM " + table + " WHERE " + what +" ='"+uuid_name+"'"
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    print cmd
                    self.cur.execute(cmd)
                    number = self.cur.rowcount
                    if number==0:
                        return -HTTP_Not_Found, "No %s found with %s '%s'" %(error_item_text, what, uuid_name)
                    elif number>1 and not allow_serveral: 
                        return -HTTP_Bad_Request, "More than one %s found with %s '%s'" %(error_item_text, what, uuid_name)
                    if allow_serveral:
                        rows = self.cur.fetchall()
                    else:
                        rows = self.cur.fetchone()
                    return number, rows
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.get_table_by_uuid_name DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def get_uuid(self, uuid):
        '''check in the database if this uuid is already present'''
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    self.cur.execute("SELECT * FROM uuids where uuid='" + str(uuid) + "'")
                    rows = self.cur.fetchall()
                    return self.cur.rowcount, rows
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.get_uuid DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
            
    def new_nfvo_tenant(self, tenant_dict):
        ''' Add one row into table 'nfvo_tenants'
        Attribute 
            tenant_dict: dictionary with the key: value to insert
        It checks presence of uuid and add one automatically otherwise
        Return: (result, uuid) where result can be 0 if error, or 1 if ok
        '''
        for retry_ in range(0,2):
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
                    cmd = "INSERT INTO uuids (uuid, root_uuid, used_at) VALUES ('%s','%s','nfvo_tenants')" % (uuid,uuid)
                    print cmd
                    self.cur.execute(cmd)
                    #insert tenant
                    cmd= "INSERT INTO nfvo_tenants (" + \
                        ",".join(map(str, tenant_dict.keys() ))   + ") VALUES(" + \
                        ",".join(map(lambda x: "Null" if x is None else "'"+str(x)+"'",tenant_dict.values() )) + ")"
                    print cmd
                    self.cur.execute(cmd)
                    inserted = self.cur.rowcount
                    #inserting new log
                    del tenant_dict['uuid'] # not interested for the log
                    cmd = "INSERT INTO logs (related,level,nfvo_tenant_id,uuid,description) VALUES ('nfvo_tenants','debug','%s','%s',\"new nfvo tenant %s\")" % (uuid, tenant_id, str(tenant_dict))
                    print cmd
                    self.cur.execute(cmd)
                    #commit transaction
                    self.cur.close()
                if inserted == 0: return 0, uuid
                else: return 1, uuid
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.new_nfvo_tenant DB Exception %d: %s" % (e.args[0], e.args[1])
                if inserted==1: return 1, uuid
                else: 
                    r,c = self.format_error(e)
                    if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def update_nfvo_tenant(self, tenant_dict):
        #TODO:
        return

    def delete_nfvo_tenant(self, tenant_dict):
        #TODO:
        return
    
    def new_datacenter(self, datacenter_dict):
        ''' Add one row into table 'datacenters'
        Attribute 
            datacenter_dict: dictionary with the key: value to insert
        It checks presence of uuid and add one automatically otherwise
        Return: (result, uuid) where result can be 0 if error, or 1 if ok
        '''
        for retry_ in range(0,2):
            inserted=-1
            try:
                #create uuid if not provided
                if 'uuid' not in datacenter_dict:
                    uuid = datacenter_dict['uuid'] = str(myUuid.uuid1()) # create_uuid
                else: 
                    uuid = str(datacenter_dict['uuid'])
                #obtain tenant_id for logs
                datacenter_id = uuid
                with self.con:
                    self.cur = self.con.cursor()
                    #inserting new uuid
                    cmd = "INSERT INTO uuids (uuid, root_uuid, used_at) VALUES ('%s','%s','datacenters')" % (uuid,uuid)
                    print cmd
                    self.cur.execute(cmd)
                    #insert tenant
                    cmd= "INSERT INTO datacenters (" + \
                        ",".join(map(str, datacenter_dict.keys() ))   + ") VALUES(" + \
                        ",".join(map(lambda x: "Null" if x is None else "'"+str(x)+"'",datacenter_dict.values() )) + ")"
                    print cmd
                    self.cur.execute(cmd)
                    inserted = self.cur.rowcount
                    #inserting new log
                    del datacenter_dict['uuid'] # not interested for the log
                    cmd = "INSERT INTO logs (related,level,uuid,description) VALUES ('datacenters','debug','%s',\"new datacenter %s\")" % (datacenter_id, str(datacenter_dict))
                    print cmd
                    self.cur.execute(cmd)
                    #commit transaction
                    self.cur.close()
                if inserted == 0:
                    return 0, uuid
                else:
                    return 1, uuid
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.new_datacenter DB Exception %d: %s" % (e.args[0], e.args[1])
                if inserted==1:
                    return 1, uuid
                else: 
                    r,c = self.format_error(e)
                    if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def udpate_datacenter(self, datacenter_dict):
        #TODO:
        return

    def delete_datacenter(self, datacenter_dict):
        #TODO:
        return

    def new_vim_tenant(self, vim_tenant_dict):
        ''' Add one row into table 'vim_tenants'
        Attribute 
            vim_tenant_dict: dictionary with the key: value to insert
        It checks presence of uuid and add one automatically otherwise
        Return: (result, uuid) where result can be 0 if error, or 1 if ok
        '''
        inserted=-1
        for retry_ in range(0,2):
            try:
                #create uuid if not provided
                if 'uuid' not in vim_tenant_dict:
                    uuid = vim_tenant_dict['uuid'] = str(myUuid.uuid1()) # create_uuid
                else: 
                    uuid = str(vim_tenant_dict['uuid'])
                #obtain tenant_id for logs
                vim_tenant_id = uuid
                with self.con:
                    self.cur = self.con.cursor()
                    #inserting new uuid
                    cmd = "INSERT INTO uuids (uuid, root_uuid, used_at) VALUES ('%s','%s','vim_tenants')" % (uuid,uuid)
                    print cmd
                    self.cur.execute(cmd)
                    #insert tenant
                    cmd= "INSERT INTO vim_tenants (" + \
                        ",".join(map(str, vim_tenant_dict.keys() ))   + ") VALUES(" + \
                        ",".join(map(lambda x: "Null" if x is None else "'"+str(x)+"'",vim_tenant_dict.values() )) + ")"
                    print cmd
                    self.cur.execute(cmd)
                    inserted = self.cur.rowcount
                    #inserting new log
                    del vim_tenant_dict['uuid'] # not interested for the log
                    cmd = "INSERT INTO logs (related,level,uuid,description) VALUES ('vim_tenants','debug','%s',\"new vim tenant %s\")" % (vim_tenant_id, str(vim_tenant_dict))
                    print cmd
                    self.cur.execute(cmd)
                    #commit transaction
                    self.cur.close()
                if inserted == 0: return 0, uuid
                else: return 1, uuid
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.new_vim_tenant DB Exception %d: %s" % (e.args[0], e.args[1])
                if inserted==1: return 1, uuid
                else: 
                    r,c = self.format_error(e)
                    if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def update_vim_tenant(self, vim_tenant_dict):
        #TODO:
        return

    def delete_vim_tenant(self, vim_tenant_dict):
        #TODO:
        return

    def new_association_tenants_datacenter(self, association_dict):
        ''' Add one row into table 'tenants_datacenters'
        Attribute 
            association_dict: dictionary with the key: value to insert
        Return: (result, id) where result can be 0 if error, or 1 if ok
        '''
        for retry_ in range(0,2):
            inserted=-1
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    #insert new association
                    cmd= "INSERT INTO tenants_datacenters (" + \
                        ",".join(map(str, association_dict.keys() ))   + ") VALUES(" + \
                        ",".join(map(lambda x: "Null" if x is None else "'"+str(x)+"'",association_dict.values() )) + ")"
                    print cmd
                    self.cur.execute(cmd)
                    inserted = self.cur.rowcount
                    #inserting new log
                    cmd = "INSERT INTO logs (related,level,nfvo_tenant_id,description) VALUES ('tenants_datacenters','debug','%s',\"new association %s\")" % (association_dict["nfvo_tenant_id"], str(association_dict))
                    print cmd
                    self.cur.execute(cmd)
                    #commit transaction
                    self.cur.close()
                if inserted == 0: return 0
                else: return 1
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.new_nfvo_tenant DB Exception %d: %s" % (e.args[0], e.args[1])
                if inserted==1: return 1
                else: 
                    r,c = self.format_error(e)
                    if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def delete_association_nfvotenant_datacenter(self, association_dict):
        #Delete association nfvo_tenant, datacenter, vim_tenant
        #TODO:
        return

    def get_vimURL(self,datacenter_uuid):
        '''Get the VIM URL of a datacenter'''
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    self.cur.execute("SELECT vim_url FROM datacenters where uuid='" + str(datacenter_uuid) + "'")
                    rows = self.cur.fetchall()
                    return self.cur.rowcount, rows
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.get_vimURL DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def get_vimURLadmin(self,datacenter_uuid):
        '''Get the admin VIM URL of a datacenter'''
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    self.cur.execute("SELECT vim_url_admin FROM datacenters where uuid='" + str(datacenter_uuid) + "'")
                    rows = self.cur.fetchall()
                    return self.cur.rowcount, rows
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.get_vimURL DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def new_vnf_as_a_whole(self,nfvo_tenant,vnf_name,vnf_descriptor_filename,vnf_descriptor,VNFCDict):
        print "Adding new vnf to the NFVO database"
        for retry_ in range(0,2):
            try:
                with self.con:
            
                    myVNFDict = {}
                    myVNFDict["name"] = vnf_name
                    myVNFDict["path"] = vnf_descriptor_filename
                    myVNFDict["physical"] = vnf_descriptor['vnf']['physical']
                    myVNFDict["public"] = vnf_descriptor['vnf']['public']
                    myVNFDict["description"] = vnf_descriptor['vnf']['description']
                    myVNFDict["class"] = vnf_descriptor['vnf'].get('class',"MISC")
                    
                    result, vnf_id = self.new_vnf(myVNFDict,nfvo_tenant)
                    if result < 0:
                        return result, "Error creating vnf in NFVO database: %s" %vnf_id
                        
                    print "VNF %s added to NFVO DB. VNF id: %s" % (vnf_name,vnf_id)
                    
                    print "Adding new vms to the NFVO database"
                    #For each vm, we must create the appropriate vm in the NFVO database.
                    vmDict = {}
                    for _,vm in VNFCDict.iteritems():
                        #This code could make the name of the vms grow and grow.
                        #If we agree to follow this convention, we should check with a regex that the vnfc name is not including yet the vnf name  
                        #vm['name'] = "%s-%s" % (vnf_name,vm['name'])
                        print "VM name: %s. Description: %s" % (vm['name'], vm['description'])
                        vm["vnf_id"] = vnf_id
                        result, vm_id = self.new_vm(vm,nfvo_tenant,vnf_id)
                        if result < 0:
                            return result, "Error creating vm in NFVO database: %s" %vm_id
                        
                        print "Internal vm id in NFVO DB: %s" % vm_id
                        vmDict[vm['name']] = vm_id
                
                    #Collect the data interfaces of each VM/VNFC under the 'numas' field
                    dataifacesDict = {}
                    for vm in vnf_descriptor['vnf']['VNFC']:
                        dataifacesDict[vm['name']] = {}
                        for numa in vm.get('numas', []):
                            for dataiface in numa.get('interfaces',[]):
                                af.convert_bandwidth(dataiface)
                                dataifacesDict[vm['name']][dataiface['name']] = {}
                                dataifacesDict[vm['name']][dataiface['name']]['vpci'] = dataiface['vpci']
                                dataifacesDict[vm['name']][dataiface['name']]['bw'] = dataiface['bandwidth']
    
                    #Collect the bridge interfaces of each VM/VNFC under the 'bridge-ifaces' field
                    bridgeInterfacesDict = {}
                    for vm in vnf_descriptor['vnf']['VNFC']:
                        if 'bridge-ifaces' in  vm:
                            bridgeInterfacesDict[vm['name']] = {}
                            for bridgeiface in vm['bridge-ifaces']:
                                af.convert_bandwidth(bridgeiface)
                                bridgeInterfacesDict[vm['name']][bridgeiface['name']] = {}
                                bridgeInterfacesDict[vm['name']][bridgeiface['name']]['vpci'] = bridgeiface.get('vpci',None)
                                bridgeInterfacesDict[vm['name']][bridgeiface['name']]['bw'] = bridgeiface.get('bandwidth', None)
                                bridgeInterfacesDict[vm['name']][bridgeiface['name']]['model'] = bridgeiface.get('model', None)
                    
                    #For each internal connection, we add it to the interfaceDict and we  create the appropriate net in the NFVO database.
                    print "Adding new nets (VNF internal nets) to the NFVO database (if any)"
                    internalconnList = []
                    if 'internal-connections' in vnf_descriptor['vnf']:
                        for net in vnf_descriptor['vnf']['internal-connections']:
                            print "CODE TO BE CHECKED"
                            print "Net name: %s. Description: %s" % (net['name'], net['description'])
                            
                            myNetDict = {}
                            myNetDict["name"] = net['name']
                            myNetDict["description"] = net['description']
                            myNetDict["type"] = net['type']
                            myNetDict["vnf_id"] = vnf_id
                            
                            result, net_id = self.new_net(myNetDict,nfvo_tenant,vnf_id)
                            if result < 0:
                                return result, "Error creating net in NFVO database: %s" %net_id
                                
                            for element in net['elements']:
                                ifaceItem = {}
                                #ifaceItem["internal_name"] = "%s-%s-%s" % (net['name'],element['VNFC'], element['local_iface_name'])  
                                ifaceItem["internal_name"] = element['local_iface_name']
                                #ifaceItem["vm_id"] = vmDict["%s-%s" % (vnf_name,element['VNFC'])]
                                ifaceItem["vm_id"] = vmDict[element['VNFC']]
                                ifaceItem["net_id"] = net_id
                                ifaceItem["type"] = net['type']
                                if ifaceItem ["type"] == "data":
                                    ifaceItem["vpci"] = dataifacesDict[element['VNFC']][element['local_iface_name']]['vpci'] 
                                    ifaceItem["bw"] = dataifacesDict[element['VNFC']][element['local_iface_name']]['bw']
                                else:
                                    ifaceItem["vpci"] = bridgeInterfacesDict[element['VNFC']][element['local_iface_name']]['vpci'] 
                                    ifaceItem["bw"] = bridgeInterfacesDict[element['VNFC']][element['local_iface_name']]['bw']
                                    ifaceItem["model"] = bridgeInterfacesDict[ element['VNFC'] ][ element['local_iface_name'] ]['model']
                                internalconnList.append(ifaceItem)
                            
                            print "Internal net id in NFVO DB: %s" % net_id
                    
                    print "Adding internal interfaces to the NFVO database (if any)"
                    for iface in internalconnList:
                        print "Iface name: %s" % iface['internal_name']
                        result, iface_id = self.new_interface(iface,nfvo_tenant,vnf_id)
                        if result < 0:
                            return result, "Error creating iface in NFVO database: %s" %iface_id
                        print "Iface id in NFVO DB: %s" % iface_id
                    
                    print "Adding external interfaces to the NFVO database"
                    for iface in vnf_descriptor['vnf']['external-connections']:
                        myIfaceDict = {}
                        #myIfaceDict["internal_name"] = "%s-%s-%s" % (vnf_name,iface['VNFC'], iface['local_iface_name'])  
                        myIfaceDict["internal_name"] = iface['local_iface_name']
                        #myIfaceDict["vm_id"] = vmDict["%s-%s" % (vnf_name,iface['VNFC'])]
                        myIfaceDict["vm_id"] = vmDict[iface['VNFC']]
                        myIfaceDict["external_name"] = iface['name']
                        myIfaceDict["type"] = iface['type']
                        if iface["type"] == "data":
                            myIfaceDict["vpci"] = dataifacesDict[iface['VNFC']][iface['local_iface_name']]['vpci']
                            myIfaceDict["bw"] = dataifacesDict[iface['VNFC']][iface['local_iface_name']]['bw']
                        else:
                            myIfaceDict["vpci"] = bridgeInterfacesDict[iface['VNFC']][iface['local_iface_name']]['vpci']
                            myIfaceDict["bw"] = bridgeInterfacesDict[iface['VNFC']][iface['local_iface_name']]['bw']
                            myIfaceDict["model"] = bridgeInterfacesDict[iface['VNFC']][iface['local_iface_name']]['model']
                        print "Iface name: %s" % iface['name']
                        result, iface_id = self.new_interface(myIfaceDict,nfvo_tenant,vnf_id)
                        if result < 0:
                            return result, "Error creating iface in NFVO database: %s" %iface_id
                        print "Iface id in NFVO DB: %s" % iface_id
                    
                    return 1,vnf_id
                
            except (mdb.Error, AttributeError), e:
                print "new_vnf_as_a_whole DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
        
    def new_vnf(self, vnf_dict, tenant_id):
        #return self.new_row('vnfs', vnf_dict, None, tenant_id, True, True)
        return self._new_row_internal('vnfs', vnf_dict, tenant_id, add_uuid=True, root_uuid=None, log=True)

    def update_vnf(self, vnf_dict):
        #TODO:
        return

    def new_vm(self, vm_dict, tenant_id, vnf_id = None):
        #return self.new_row('vms', vm_dict, tenant_id, True, True)
        return self._new_row_internal('vms', vm_dict, tenant_id, add_uuid=True, root_uuid=vnf_id, log=True)

    def update_vm(self, vm_dict):
        #TODO:
        return
    
    def delete_vm(self, vm_id):
        #TODO:
        return

    def new_net(self, net_dict, tenant_id, vnf_id = None):
        #return self.new_row('nets', net_dict, tenant_id, True, True)
        return self._new_row_internal('nets', net_dict, tenant_id, add_uuid=True, root_uuid=vnf_id, log=True)
    
    def update_net(self, net_dict):
        #TODO:
        return

    def delete_net(self, net_id):
        #TODO:
        return
    
    def new_interface(self, interface_dict, tenant_id, vnf_id = None):
        #return self.new_row('interfaces', interface_dict, tenant_id, True, True)
        return self._new_row_internal('interfaces', interface_dict, tenant_id, add_uuid=True, root_uuid=vnf_id, log=True)

    def update_interface(self, interface_dict):
        #TODO:
        return

    def delete_interface(self, interface_dict):
        #TODO:
        return

    def new_scenario(self, scenario_dict):
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    tenant_id = scenario_dict['nfvo_tenant_id']
                    #scenario
                    INSERT_={'nfvo_tenant_id': tenant_id,
                    'name': scenario_dict['name'],'description': scenario_dict['description']}
                    r,scenario_uuid =  self._new_row_internal('scenarios', INSERT_, tenant_id, True, None, True)
                    if r<0:
                        print 'nfvo_db.new_scenario Error inserting at table scenarios: ' + scenario_uuid
                        return r,scenario_uuid
                    #sce_nets
                    for net in scenario_dict['nets'].values():
                        #external=True if str(net['external'])=="True" else False
                        net.pop('model', None)
                        #net.pop('type', None)
                        net.pop('shared', None)
                        net.pop('uuid', None) #external_net_uuid = 
                        net.pop('net_id', None)
                        net['scenario_id']=scenario_uuid
                        if "graph" in net:
                            net["graph"]=json.dumps(net["graph"])
                        r,net_uuid =  self._new_row_internal('sce_nets', net, tenant_id, True, True)
                        if r<0:
                            print 'nfvo_db.new_scenario Error inserting at table sce_vnfs: ' + net_uuid
                            return r, net_uuid
                        net['uuid']=net_uuid
                    #sce_vnfs
                    for k,vnf in scenario_dict['vnfs'].items():
                        INSERT_={'scenario_id': scenario_uuid,
                                'name': k,
                                'vnf_id': vnf['uuid'],
                                #'description': scenario_dict['name']
                                'description': vnf['description']
                            }
                        if "graph" in vnf:
                            INSERT_["graph"]=json.dumps(vnf["graph"])
                        r,scn_vnf_uuid =  self._new_row_internal('sce_vnfs', INSERT_, tenant_id, True, scenario_uuid, True)
                        if r<0:
                            print 'nfvo_db.new_scenario Error inserting at table sce_vnfs: ' + scn_vnf_uuid
                            return r, scn_vnf_uuid
                        vnf['scn_vnf_uuid']=scn_vnf_uuid
                        #sce_interfaces
                        for iface in vnf['ifaces'].values():
                            print 'iface', iface
                            if 'net_key' not in iface:
                                continue
                            iface['net_id'] = scenario_dict['nets'][ iface['net_key'] ]['uuid']
                            INSERT_={'sce_vnf_id': scn_vnf_uuid,
                                'sce_net_id': iface['net_id'],
                                'interface_id':  iface[ 'uuid' ]
                            }
                            r,iface_uuid =  self._new_row_internal('sce_interfaces', INSERT_, tenant_id, True, scenario_uuid, True)
                            if r<0:
                                print 'nfvo_db.new_scenario Error inserting at table sce_vnfs: ' + iface_uuid
                                return r, iface_uuid
                            
                    return 1, scenario_uuid
                    
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.new_scenario DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def edit_scenario(self, scenario_dict):
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    #check that scenario exist
                    tenant_id = scenario_dict['nfvo_tenant_id']
                    scenario_uuid = scenario_dict['uuid']
                    r,c = self.__get_rows("scenarios", scenario_uuid)
                    if r==0:
                        return -HTTP_Not_Found, "scenario %s not found" % scenario_uuid
                    #scenario
                    nodes = {}
                    topology = scenario_dict.pop("topology", None)
                    if topology != None and "nodes" in topology:
                        nodes = topology.get("nodes",{})
                    UPDATE_ = {}
                    if "name" in scenario_dict:        UPDATE_["name"] = scenario_dict["name"]
                    if "description" in scenario_dict: UPDATE_["description"] = scenario_dict["description"]
                    if len(UPDATE_)>0:
                        WHERE_={'nfvo_tenant_id': tenant_id, 'uuid': scenario_uuid}
                        r,c =  self.__update_rows('scenarios', UPDATE_, WHERE_)
                        if r<0:
                            print 'nfvo_db.edit_scenario Error ' + c + ' updating table scenarios: ' + scenario_uuid
                            return r,scenario_uuid
                    #sce_nets
                    for node_id, node in nodes.items():
                        if "graph" in node:
                            node["graph"] = json.dumps(node["graph"])
                        WHERE_={'scenario_id': scenario_uuid, 'uuid': node_id}
                        r,c =  self.__update_rows('sce_nets', node, WHERE_)
                        if r<=0:
                            r,c =  self.__update_rows('sce_vnfs', node, WHERE_)
                            if r<0:
                                print 'nfvo_db.edit_scenario Error updating table sce_nets,sce_vnfs: ' + scenario_uuid
                                return r, scenario_uuid
                    return 1, scenario_uuid
                    
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.new_scenario DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

#     def get_instance_scenario(self, instance_scenario_id, nfvo_tenant_id=None):
#         '''Obtain the scenario instance information, filtering by one or serveral of the tenant, uuid or name
#         instance_scenario_id is the uuid or the name if it is not a valid uuid format
#         Only one scenario isntance must mutch the filtering or an error is returned
#         ''' 
#         print "1******************************************************************"
#         try:
#             with self.con:
#                 self.cur = self.con.cursor(mdb.cursors.DictCursor)
#                 #scenario table
#                 where_list=[]
#                 if nfvo_tenant_id is not None: where_list.append( "nfvo_tenant_id='" + nfvo_tenant_id +"'" )
#                 if af.check_valid_uuid(instance_scenario_id):
#                     where_list.append( "uuid='" + instance_scenario_id +"'" )
#                 else:
#                     where_list.append( "name='" + instance_scenario_id +"'" )
#                 where_text = " AND ".join(where_list)
#                 self.cur.execute("SELECT * FROM instance_scenarios WHERE "+ where_text)
#                 rows = self.cur.fetchall()
#                 if self.cur.rowcount==0:
#                     return -HTTP_Bad_Request, "No scenario instance found with this criteria " + where_text
#                 elif self.cur.rowcount>1:
#                     return -HTTP_Bad_Request, "More than one scenario instance found with this criteria " + where_text
#                 instance_scenario_dict = rows[0]
#                 
#                 #instance_vnfs
#                 self.cur.execute("SELECT uuid,vnf_id FROM instance_vnfs WHERE instance_scenario_id='"+ instance_scenario_dict['uuid'] + "'")
#                 instance_scenario_dict['instance_vnfs'] = self.cur.fetchall()
#                 for vnf in instance_scenario_dict['instance_vnfs']:
#                     #instance_vms
#                     self.cur.execute("SELECT uuid, vim_vm_id "+
#                                 "FROM instance_vms  "+
#                                 "WHERE instance_vnf_id='" + vnf['uuid'] +"'"  
#                                 )
#                     vnf['instance_vms'] = self.cur.fetchall()
#                 #instance_nets
#                 self.cur.execute("SELECT uuid, vim_net_id FROM instance_nets WHERE instance_scenario_id='"+ instance_scenario_dict['uuid'] + "'")
#                 instance_scenario_dict['instance_nets'] = self.cur.fetchall()
#                 
#                 #instance_interfaces
#                 self.cur.execute("SELECT uuid, vim_interface_id, instance_vm_id, instance_net_id FROM instance_interfaces WHERE instance_scenario_id='"+ instance_scenario_dict['uuid'] + "'")
#                 instance_scenario_dict['instance_interfaces'] = self.cur.fetchall()
#                 
#                 af.convert_datetime2str(instance_scenario_dict)
#                 af.convert_str2boolean(instance_scenario_dict, ('public','shared','external') )
#                 print "2******************************************************************"
#                 return 1, instance_scenario_dict
#         except (mdb.Error, AttributeError), e:
#             print "nfvo_db.get_instance_scenario DB Exception %d: %s" % (e.args[0], e.args[1])
#             return self.format_error(e)

    def get_scenario(self, scenario_id, nfvo_tenant_id=None, datacenter_id=None):
        '''Obtain the scenario information, filtering by one or serveral of the tenant, uuid or name
        scenario_id is the uuid or the name if it is not a valid uuid format
        if datacenter_id is provided, it supply aditional vim_id fields with the matching vim uuid 
        Only one scenario must mutch the filtering or an error is returned
        ''' 
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    #scenario table
                    where_list=[]
                    if nfvo_tenant_id is not None: where_list.append( "nfvo_tenant_id='" + nfvo_tenant_id +"'" )
                    if af.check_valid_uuid(scenario_id):
                        where_list.append( "uuid='" + scenario_id +"'" )
                    else:
                        where_list.append( "name='" + scenario_id +"'" )
                    where_text = " AND ".join(where_list)
                    self.cur.execute("SELECT * FROM scenarios WHERE "+ where_text)
                    rows = self.cur.fetchall()
                    if self.cur.rowcount==0:
                        return -HTTP_Bad_Request, "No scenario found with this criteria " + where_text
                    elif self.cur.rowcount>1:
                        return -HTTP_Bad_Request, "More than one scenario found with this criteria " + where_text
                    scenario_dict = rows[0]
                    
                    #sce_vnfs
                    self.cur.execute("SELECT uuid,name,vnf_id,description FROM sce_vnfs WHERE scenario_id='"+ scenario_dict['uuid'] + "'")
                    scenario_dict['vnfs'] = self.cur.fetchall()
                    for vnf in scenario_dict['vnfs']:
                        #sce_interfaces
                        self.cur.execute("SELECT uuid,sce_net_id,interface_id FROM sce_interfaces WHERE sce_vnf_id='"+ vnf['uuid'] + "'")
                        vnf['interfaces'] = self.cur.fetchall()
                        #vms
                        self.cur.execute("SELECT vms.uuid as uuid, flavor_id, image_id, vms.name as name, vms.description as description "+
                                    "FROM vnfs join vms on vnfs.uuid=vms.vnf_id "+
                                    "WHERE vnfs.uuid='" + vnf['vnf_id'] +"'"  
                                    )
                        vnf['vms'] = self.cur.fetchall()
                        for vm in vnf['vms']:
                            if datacenter_id!=None:
                                self.cur.execute("SELECT vim_id FROM datacenters_images WHERE image_id='%s' AND datacenter_id='%s'" %(vm['image_id'],datacenter_id)) 
                                if self.cur.rowcount==1:
                                    vim_image_dict = self.cur.fetchone()
                                    vm['vim_image_id']=vim_image_dict['vim_id']
                                self.cur.execute("SELECT vim_id FROM datacenters_flavors WHERE flavor_id='%s' AND datacenter_id='%s'" %(vm['flavor_id'],datacenter_id)) 
                                if self.cur.rowcount==1:
                                    vim_flavor_dict = self.cur.fetchone()
                                    vm['vim_flavor_id']=vim_flavor_dict['vim_id']
                                
                            #interfaces
                            self.cur.execute("SELECT uuid,internal_name,external_name,net_id,type,vpci,bw,model " +
                                    "FROM interfaces " +
                                    "WHERE vm_id='" + vm['uuid'] +"'"  )
                            vm['interfaces'] = self.cur.fetchall()
                        #nets    every net of a vms
                        self.cur.execute("SELECT uuid,name,type,description FROM nets WHERE vnf_id='" + vnf['vnf_id'] +"'"  )
                        vnf['nets'] = self.cur.fetchall()
                    #sce_nets
                    self.cur.execute("SELECT uuid,name,type,external,description FROM sce_nets  WHERE scenario_id='"+ scenario_dict['uuid'] + "'")
                    scenario_dict['nets'] = self.cur.fetchall()
                    #datacenter_nets
                    for net in scenario_dict['nets']:
                        if str(net['external']) == 'false':
                            continue
                        WHERE_=" WHERE name='%s'" % net['name']
                        if datacenter_id!=None:
                            WHERE_ += " AND datacenter_id='%s'" % datacenter_id 
                        self.cur.execute("SELECT vim_net_id FROM datacenter_nets" + WHERE_ ) 
                        d_net = self.cur.fetchone()
                        if d_net==None or datacenter_id==None:
                            #print "nfvo_db.get_scenario() WARNING external net %s not found"  % net['name']
                            net['vim_id']=None
                        else:
                            net['vim_id']=d_net['vim_net_id']
                    
                    af.convert_datetime2str(scenario_dict)
                    af.convert_str2boolean(scenario_dict, ('public','shared','external') )
                    return 1, scenario_dict
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.get_scenario DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def update_scenario(self, scenario_dict):
        #TODO:
        return

    def get_uuid_from_name(self, table, name):
        '''Searchs in table the name and returns the uuid
        ''' 
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    where_text = "name='" + name +"'"
                    self.cur.execute("SELECT * FROM " + table + " WHERE "+ where_text)
                    rows = self.cur.fetchall()
                    if self.cur.rowcount==0:
                        return 0, "Name %s not found in table %s" %(name, table)
                    elif self.cur.rowcount>1:
                        return self.cur.rowcount, "More than one VNF with name %s found in table %s" %(name, table)
                    return self.cur.rowcount, rows[0]["uuid"]
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.get_uuid_from_name DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def delete_scenario(self, scenario_id, nfvo_tenant_id=None):
        '''Deletes a scenario, filtering by one or several of the tenant, uuid or name
        scenario_id is the uuid or the name if it is not a valid uuid format
        Only one scenario must mutch the filtering or an error is returned
        ''' 
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
    
                    #scenario table
                    where_list=[]
                    if nfvo_tenant_id is not None: where_list.append( "nfvo_tenant_id='" + nfvo_tenant_id +"'" )
                    if af.check_valid_uuid(scenario_id):
                        where_list.append( "uuid='" + scenario_id +"'" )
                    else:
                        where_list.append( "name='" + scenario_id +"'" )
                    where_text = " AND ".join(where_list)
                    self.cur.execute("SELECT * FROM scenarios WHERE "+ where_text)
                    rows = self.cur.fetchall()
                    if self.cur.rowcount==0:
                        return -HTTP_Bad_Request, "No scenario found with this criteria " + where_text
                    elif self.cur.rowcount>1:
                        return -HTTP_Bad_Request, "More than one scenario found with this criteria " + where_text
                    scenario_uuid = rows[0]["uuid"]
                    scenario_name = rows[0]["name"]
                    
                    #sce_vnfs
                    self.cur.execute("DELETE FROM scenarios WHERE uuid='" + scenario_uuid + "'")
    
                    return 1, scenario_uuid + " " + scenario_name
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.delete_scenario DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c =  self.format_error(e, "delete", "instances running")
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def new_instance_scenario_as_a_whole(self,tenant_id,instance_scenario_name,instance_scenario_description,scenarioDict):
        print "Adding new instance scenario to the NFVO database"
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    #instance_scenarios
                    INSERT_={'nfvo_tenant_id': tenant_id,
                        'vim_tenant_id': scenarioDict['vim_tenants_uuid'],
                        'name': instance_scenario_name,
                        'description': instance_scenario_description,
                        'scenario_id' : scenarioDict['uuid'],
                        'datacenter_id': scenarioDict['datacenter_id']
                    }
                    r,instance_uuid =  self._new_row_internal('instance_scenarios', INSERT_, tenant_id, True, None, True)
                    if r<0:
                        print 'nfvo_db.new_instance_scenario_as_a_whole() Error inserting at table instance_scenarios: ' + instance_uuid
                        return r, instance_uuid                
                    
                    net_scene2instance={}
                    #instance_nets   #nets interVNF
                    for net in scenarioDict['nets']:
                        INSERT_={'vim_net_id': net['vim_id'], 'external': net['external'], 'instance_scenario_id':instance_uuid } #,  'type': net['type']
                        r,instance_net_uuid =  self._new_row_internal('instance_nets', INSERT_, tenant_id, True, instance_uuid, True)
                        if r<0:
                            print 'nfvo_db.new_instance_scenario_as_a_whole() Error inserting at table instance_nets: ' + instance_net_uuid
                            return r, instance_net_uuid                
                        net_scene2instance[ net['uuid'] ] = instance_net_uuid
                        net['uuid'] = instance_net_uuid  #overwrite scnario uuid by instance uuid
                    
                    #instance_vnfs
                    for vnf in scenarioDict['vnfs']:
                        INSERT_={'instance_scenario_id': instance_uuid,  'vnf_id': vnf['vnf_id']  }
                        r,instance_vnf_uuid =  self._new_row_internal('instance_vnfs', INSERT_, tenant_id, True, instance_uuid, True)
                        if r<0:
                            print 'nfvo_db.new_instance_scenario_as_a_whole() Error inserting at table instance_vnfs: ' + instance_vnf_uuid
                            return r, instance_vnf_uuid                
                        vnf['uuid'] = instance_vnf_uuid  #overwrite scnario uuid by instance uuid
                        
                        #instance_nets   #nets intraVNF
                        for net in vnf['nets']:
                            INSERT_={'vim_net_id': net['vim_id'], 'external': 'false', 'instance_scenario_id':instance_uuid  } #,  'type': net['type']
                            r,instance_net_uuid =  self._new_row_internal('instance_nets', INSERT_, tenant_id, True, instance_uuid, True)
                            if r<0:
                                print 'nfvo_db.new_instance_scenario_as_a_whole() Error inserting at table instance_nets: ' + instance_net_uuid
                                return r, instance_net_uuid                
                            net_scene2instance[ net['uuid'] ] = instance_net_uuid
                            net['uuid'] = instance_net_uuid  #overwrite scnario uuid by instance uuid
                        
                        #instance_vms
                        for vm in vnf['vms']:
                            INSERT_={'instance_vnf_id': instance_vnf_uuid,  'vm_id': vm['uuid'], 'vim_vm_id': vm['vim_id']  }
                            r,instance_vm_uuid =  self._new_row_internal('instance_vms', INSERT_, tenant_id, True, instance_uuid, True)
                            if r<0:
                                print 'nfvo_db.new_instance_scenario_as_a_whole() Error inserting at table instance_vms: ' + instance_vm_uuid
                                return r, instance_vm_uuid                
                            vm['uuid'] = instance_vm_uuid  #overwrite scnario uuid by instance uuid
                            
                            #instance_interfaces
                            for interface in vm['interfaces']:
                                net_id = interface.get('net_id', None)
                                if net_id is None:
                                    #check if is connected to a inter VNFs net
                                    for iface in vnf['interfaces']:
                                        if iface['interface_id'] == interface['uuid']:
                                            net_id = iface.get('sce_net_id', None)
                                            break
                                if net_id is None:
                                    continue
                                interface_type='external' if interface['external_name'] is not None else 'internal'
                                INSERT_={'instance_vm_id': instance_vm_uuid,  'instance_net_id': net_scene2instance[net_id],
                                    'interface_id': interface['uuid'], 'vim_interface_id': interface.get('vim_id'), 'type':  interface_type  }
                                r,interface_uuid =  self._new_row_internal('instance_interfaces', INSERT_, tenant_id, True, instance_uuid, True)
                                if r<0:
                                    print 'nfvo_db.new_instance_scenario_as_a_whole() Error inserting at table instance_interfaces: ' + interface_uuid
                                    return r, interface_uuid                
                                interface['uuid'] = interface_uuid  #overwrite scnario uuid by instance uuid
                        
    
                
                return 1, instance_uuid
                
            except (mdb.Error, AttributeError), e:
                print "new_instance_scenario_as_a_whole DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c

    def get_instance_scenario(self, instance_id, nfvo_tenant_id=None):
        '''Obtain the instance information, filtering by one or several of the tenant, uuid or name
        instance_id is the uuid or the name if it is not a valid uuid format
        Only one instance must mutch the filtering or an error is returned
        ''' 
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    #instance table
                    where_list=[]
                    if nfvo_tenant_id is not None: where_list.append( "inst.nfvo_tenant_id='" + nfvo_tenant_id +"'" )
                    if af.check_valid_uuid(instance_id):
                        where_list.append( "inst.uuid='" + instance_id +"'" )
                    else:
                        where_list.append( "inst.name='" + instance_id +"'" )
                    where_text = " AND ".join(where_list)
                    select_text = "inst.uuid as uuid,inst.name as name,inst.scenario_id as scenario_id, datacenter_id, "\
                                "s.name as scenario_name,inst.nfvo_tenant_id as nfvo_tenant_id," + \
                                "inst.description as description,inst.created_at as created_at"
                    from_text = "instance_scenarios as inst join scenarios as s on inst.scenario_id=s.uuid"
                    self.cur.execute("SELECT " + select_text + " FROM " + from_text + " WHERE "+ where_text)
                    rows = self.cur.fetchall()
                    if self.cur.rowcount==0:
                        return -HTTP_Bad_Request, "No instance found with this criteria " + where_text
                    elif self.cur.rowcount>1:
                        return -HTTP_Bad_Request, "More than one instance found with this criteria " + where_text
                    instance_dict = rows[0]
                    
                    #instance_vnfs
                    select_text = "instance_vnfs.uuid as uuid,instance_vnfs.vnf_id as vnf_id,vnfs.name as vnf_name"
                    from_text = "instance_vnfs join vnfs on instance_vnfs.vnf_id=vnfs.uuid"
                    self.cur.execute("SELECT " + select_text + " FROM " + from_text + " WHERE instance_vnfs.instance_scenario_id='"+ instance_dict['uuid'] + "'")
                    instance_dict['vnfs'] = self.cur.fetchall()
                    for vnf in instance_dict['vnfs']:
                        #instance vms
                        self.cur.execute("SELECT iv.uuid as uuid, vim_vm_id, status, iv.created_at as created_at, name "+
                                    "FROM instance_vms as iv join vms on iv.vm_id=vms.uuid "+
                                    "WHERE instance_vnf_id='" + vnf['uuid'] +"'"  
                                    )
                        vnf['vms'] = self.cur.fetchall()
                        for vm in vnf['vms']:
                            #instance_interfaces
                            self.cur.execute("SELECT vim_interface_id, instance_net_id, internal_name,external_name " +
                                    "FROM instance_interfaces as ii join interfaces as i on ii.interface_id=i.uuid " +
                                    "WHERE instance_vm_id='" + vm['uuid'] +"'"  )
                            vm['interfaces'] = self.cur.fetchall()
                    #instance_nets
                    #select_text = "instance_nets.uuid as uuid,sce_nets.name as net_name,instance_nets.vim_net_id as net_id,instance_nets.status as status,instance_nets.external as external" 
                    #from_text = "instance_nets join instance_scenarios on instance_nets.instance_scenario_id=instance_scenarios.uuid " + \
                    #            "join sce_nets on instance_scenarios.scenario_id=sce_nets.scenario_id"
                    #where_text = "instance_nets.instance_scenario_id='"+ instance_dict['uuid'] + "'"
                    select_text = "uuid,vim_net_id,status,external"
                    from_text = "instance_nets"
                    where_text = "instance_scenario_id='"+ instance_dict['uuid'] + "'"
    
                    self.cur.execute("SELECT " + select_text + " FROM " + from_text + " WHERE " + where_text)
                    instance_dict['nets'] = self.cur.fetchall()
                    
                    af.convert_datetime2str(instance_dict)
                    af.convert_str2boolean(instance_dict, ('public','shared','external') )
                    return 1, instance_dict
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.get_instance_scenario DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
        
    def delete_instance_scenario(self, instance_id, nfvo_tenant_id=None):
        '''Deletes a instance_Scenario, filtering by one or serveral of the tenant, uuid or name
        instance_id is the uuid or the name if it is not a valid uuid format
        Only one instance_scenario must mutch the filtering or an error is returned
        ''' 
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
    
                    #instance table
                    where_list=[]
                    if nfvo_tenant_id is not None: where_list.append( "nfvo_tenant_id='" + nfvo_tenant_id +"'" )
                    if af.check_valid_uuid(instance_id):
                        where_list.append( "uuid='" + instance_id +"'" )
                    else:
                        where_list.append( "name='" + instance_id +"'" )
                    where_text = " AND ".join(where_list)
                    self.cur.execute("SELECT * FROM instance_scenarios WHERE "+ where_text)
                    rows = self.cur.fetchall()
                    if self.cur.rowcount==0:
                        return -HTTP_Bad_Request, "No instance scenario found with this criteria " + where_text
                    elif self.cur.rowcount>1:
                        return -HTTP_Bad_Request, "More than one instance scenario found with this criteria " + where_text
                    instance_uuid = rows[0]["uuid"]
                    instance_name = rows[0]["name"]
                    
                    #sce_vnfs
                    self.cur.execute("DELETE FROM instance_scenarios WHERE uuid='" + instance_uuid + "'")
    
                    return 1, instance_uuid + " " + instance_name
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.delete_instance_scenario DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e, "delete", "No dependences can avoid deleting!!!!")
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
    
    def new_instance_scenario(self, instance_scenario_dict, tenant_id):
        #return self.new_row('vnfs', vnf_dict, None, tenant_id, True, True)
        return self._new_row_internal('instance_scenarios', instance_scenario_dict, tenant_id, add_uuid=True, root_uuid=None, log=True)

    def update_instance_scenario(self, instance_scenario_dict):
        #TODO:
        return

    def new_instance_vnf(self, instance_vnf_dict, tenant_id, instance_scenario_id = None):
        #return self.new_row('vms', vm_dict, tenant_id, True, True)
        return self._new_row_internal('instance_vnfs', instance_vnf_dict, tenant_id, add_uuid=True, root_uuid=instance_scenario_id, log=True)

    def update_instance_vnf(self, instance_vnf_dict):
        #TODO:
        return
    
    def delete_instance_vnf(self, instance_vnf_id):
        #TODO:
        return

    def new_instance_vm(self, instance_vm_dict, tenant_id, instance_scenario_id = None):
        #return self.new_row('vms', vm_dict, tenant_id, True, True)
        return self._new_row_internal('instance_vms', instance_vm_dict, tenant_id, add_uuid=True, root_uuid=instance_scenario_id, log=True)

    def update_instance_vm(self, instance_vm_dict):
        #TODO:
        return
    
    def delete_instance_vm(self, instance_vm_id):
        #TODO:
        return

    def new_instance_net(self, instance_net_dict, tenant_id, instance_scenario_id = None):
        return self._new_row_internal('instance_nets', instance_net_dict, tenant_id, add_uuid=True, root_uuid=instance_scenario_id, log=True)
    
    def update_instance_net(self, instance_net_dict):
        #TODO:
        return

    def delete_instance_net(self, instance_net_id):
        #TODO:
        return
    
    def new_instance_interface(self, instance_interface_dict, tenant_id, instance_scenario_id = None):
        return self._new_row_internal('instance_interfaces', instance_interface_dict, tenant_id, add_uuid=True, root_uuid=instance_scenario_id, log=True)

    def update_instance_interface(self, instance_interface_dict):
        #TODO:
        return

    def delete_instance_interface(self, instance_interface_dict):
        #TODO:
        return


    def update_datacenter_nets(self, datacenter_id, new_net_list=[]):
        ''' Removes the old and adds the new net list at datacenter list for one datacenter.
        Attribute 
            datacenter_id: uuid of the datacenter to act upon
            table: table where to insert
            new_net_list: the new values to be inserted. If empty it only deletes the existing nets
        Return: (Inserted items, Deleted items) if OK, (-Error, text) if error
        '''
        for retry_ in range(0,2):
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    cmd="DELETE FROM datacenter_nets WHERE datacenter_id='%s'" % datacenter_id
                    print cmd
                    self.cur.execute(cmd)
                    deleted = self.cur.rowcount
                    for new_net in new_net_list:
                        self._new_row_internal('datacenter_nets', new_net, tenant_id=None, add_uuid=True)
                    return len (new_net_list), deleted
            except (mdb.Error, AttributeError), e:
                print "nfvo_db.update_datacenter_nets DB Exception %d: %s" % (e.args[0], e.args[1])
                r,c = self.format_error(e)
                if r!=-HTTP_Request_Timeout or retry_==1: return r,c
        

#!/bin/bash

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

#
#Upgrade/Downgrade openmano database preserving the content
#

DBUSER="mano"
DBPASS=""
DBHOST="localhost"
DBPORT="3306"
DBNAME="mano_db"
 
# Detect paths
MYSQL=$(which mysql)
AWK=$(which awk)
GREP=$(which grep)
DIRNAME=`dirname $0`

function usage(){
    echo -e "Usage: $0 OPTIONS  [{openmano_version}]"
    echo -e "  Upgrades/Downgrades openmano database preserving the content"
    echo -e "   if openmano_version is not provided it tries to get from openmanod.py using relative path"
    echo -e "  OPTIONS"
    echo -e "     -u USER  database user. '$DBUSER' by default. Prompts if DB access fails"
    echo -e "     -p PASS  database password. 'No password' by default. Prompts if DB access fails"
    echo -e "     -P PORT  database port. '$DBPORT' by default"
    echo -e "     -h HOST  database host. '$DBHOST' by default"
    echo -e "     -d NAME  database name. '$DBNAME' by default.  Prompts if DB access fails"
    echo -e "     --help   shows this help"
}

while getopts ":u:p:P:h:d:-:" o; do
    case "${o}" in
        u)
            DBUSER="$OPTARG"
            ;;
        p)
            DBPASS="$OPTARG"
            ;;
        P)
            DBPORT="$OPTARG"
            ;;
        d)
            DBNAME="$OPTARG"
            ;;
        h)
            DBHOST="$OPTARG"
            ;;
        -)
            [ "${OPTARG}" == "help" ] && usage && exit 0
            echo "Invalid option: --$OPTARG" >&2 && usage  >&2
            exit 1
            ;; 
        \?)
            echo "Invalid option: -$OPTARG" >&2 && usage  >&2
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2 && usage  >&2
            exit 1
            ;;
        *)
            usage >&2
            exit -1
            ;;
    esac
done
shift $((OPTIND-1))


#GET OPENMANO VERSION
OPENMANO_VER="$1"
if [ -z "$OPENMANO_VER" ]
then 
    OPENMANO_VER=`${DIRNAME}/../openmanod.py -v`
    OPENMANO_VER=${OPENMANO_VER%%-r*}
    OPENMANO_VER=${OPENMANO_VER##*version }
    echo "    Detected openmano version $OPENMANO_VER"
fi
VERSION_1=`echo $OPENMANO_VER | cut -f 1 -d"."`
VERSION_2=`echo $OPENMANO_VER | cut -f 2 -d"."`
VERSION_3=`echo $OPENMANO_VER | cut -f 3 -d"."`
if ! [ "$VERSION_1" -ge 0 -a "$VERSION_2" -ge 0 -a "$VERSION_3" -ge 0 ] 2>/dev/null
then 
    [ -n "$1" ] && echo "Invalid openmano version '$1', expected 'X.X.X'" >&2
    [ -z "$1" ] && echo "Can not get openmano version" >&2
    exit -1
fi
OPENMANO_VER_NUM=`printf "%d%03d%03d" ${VERSION_1} ${VERSION_2} ${VERSION_3}`

#check and ask for database user password
DBUSER_="-u$DBUSER"
[ -n "$DBPASS" ] && DBPASS_="-p$DBPASS"
DBHOST_="-h$DBHOST"
DBPORT_="-P$DBPORT"
while !  echo ";" | mysql $DBHOST_ $DBPORT_ $DBUSER_ $DBPASS_ $DBNAME >/dev/null 2>&1
do
        [ -n "$logintry" ] &&  echo -e "\nInvalid database credentials!!!. Try again (Ctrl+c to abort)"
        [ -z "$logintry" ] &&  echo -e "\nProvide database name and credentials"
        read -e -p "mysql database name($DBNAME): " KK
        [ -n "$KK" ] && DBNAME="$KK"
        read -e -p "mysql user($DBUSER): " KK
        [ -n "$KK" ] && DBUSER="$KK" && DBUSER_="-u$DBUSER"
        read -e -s -p "mysql password: " DBPASS
        [ -n "$DBPASS" ] && DBPASS_="-p$DBPASS"
        [ -z "$DBPASS" ] && DBPASS_=""
        logintry="yes"
        echo
done

DBCMD="mysql $DBHOST_ $DBPORT_ $DBUSER_ $DBPASS_ $DBNAME"
#echo DBCMD $DBCMD

#GET DATABASE VERSION
#check that the database seems a openmano database
if ! echo -e "show create table vnfs;\nshow create table scenarios" | $DBCMD >/dev/null 2>&1
then
    echo "    database $DBNAME does not seem to be an openmano database" >&2
    exit -1;
fi

if ! echo 'show create table schema_version;' | $DBCMD >/dev/null 2>&1
then
    DATABASE_VER="0.0"
    DATABASE_VER_NUM=0
else 
    DATABASE_VER_NUM=`echo "select max(version_int) from schema_version;" | $DBCMD | tail -n+2` 
    DATABASE_VER=`echo "select version from schema_version where version_int='$DATABASE_VER_NUM';" | $DBCMD | tail -n+2` 
    [ "$DATABASE_VER_NUM" -lt 0 -o "$DATABASE_VER_NUM" -gt 100 ] && echo "    Error can not get database version ($DATABASE_VER?)" >&2 && exit -1
    #echo "_${DATABASE_VER_NUM}_${DATABASE_VER}"
fi


#GET DATABASE TARGET VERSION
DATABASE_TARGET_VER_NUM=0
[ $OPENMANO_VER_NUM -ge 2002 ] && DATABASE_TARGET_VER_NUM=1   #0.2.2 =>  1
[ $OPENMANO_VER_NUM -ge 2005 ] && DATABASE_TARGET_VER_NUM=2   #0.2.5 =>  2
[ $OPENMANO_VER_NUM -ge 3003 ] && DATABASE_TARGET_VER_NUM=3   #0.3.3 =>  3
[ $OPENMANO_VER_NUM -ge 3005 ] && DATABASE_TARGET_VER_NUM=4   #0.3.5 =>  4
[ $OPENMANO_VER_NUM -ge 4001 ] && DATABASE_TARGET_VER_NUM=5   #0.4.1 =>  5
[ $OPENMANO_VER_NUM -ge 4002 ] && DATABASE_TARGET_VER_NUM=6   #0.4.2 =>  6
[ $OPENMANO_VER_NUM -ge 4003 ] && DATABASE_TARGET_VER_NUM=7   #0.4.3 =>  7
[ $OPENMANO_VER_NUM -ge 4032 ] && DATABASE_TARGET_VER_NUM=8   #0.4.32=>  8
[ $OPENMANO_VER_NUM -ge 4033 ] && DATABASE_TARGET_VER_NUM=9   #0.4.33=>  9
[ $OPENMANO_VER_NUM -ge 4036 ] && DATABASE_TARGET_VER_NUM=10  #0.4.36=>  10
#TODO ... put next versions here


function upgrade_to_1(){
    echo "    upgrade database from version 0.0 to version 0.1"
    echo "      CREATE TABLE \`schema_version\`"
    echo "CREATE TABLE \`schema_version\` (
	\`version_int\` INT NOT NULL COMMENT 'version as a number. Must not contain gaps',
	\`version\` VARCHAR(20) NOT NULL COMMENT 'version as a text',
	\`openmano_ver\` VARCHAR(20) NOT NULL COMMENT 'openmano version',
	\`comments\` VARCHAR(2000) NULL COMMENT 'changes to database',
	\`date\` DATE NULL,
	PRIMARY KEY (\`version_int\`)
	)
	COMMENT='database schema control version'
	COLLATE='utf8_general_ci'
	ENGINE=InnoDB;" | $DBCMD  || ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO \`schema_version\` (\`version_int\`, \`version\`, \`openmano_ver\`, \`comments\`, \`date\`)
	 VALUES (1, '0.1', '0.2.2', 'insert schema_version', '2015-05-08');" | $DBCMD
}
function downgrade_from_1(){
    echo "    downgrade database from version 0.1 to version 0.0"
    echo "      DROP TABLE \`schema_version\`"
    echo "DROP TABLE \`schema_version\`;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function upgrade_to_2(){
    echo "    upgrade database from version 0.1 to version 0.2"
    echo "      Add columns user/passwd to table 'vim_tenants'"
    echo "ALTER TABLE vim_tenants ADD COLUMN user VARCHAR(36) NULL COMMENT 'Credentials for vim' AFTER created,
	ADD COLUMN passwd VARCHAR(50) NULL COMMENT 'Credentials for vim' AFTER user;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Add table 'images' and 'datacenters_images'"
    echo "CREATE TABLE images (
	uuid VARCHAR(36) NOT NULL,
	name VARCHAR(50) NOT NULL,
	location VARCHAR(200) NOT NULL,
	description VARCHAR(100) NULL,
	metadata VARCHAR(400) NULL,
	PRIMARY KEY (uuid),
	UNIQUE INDEX location (location)  )
        COLLATE='utf8_general_ci'
        ENGINE=InnoDB;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "CREATE TABLE datacenters_images (
	id INT NOT NULL AUTO_INCREMENT,
	image_id VARCHAR(36) NOT NULL,
	datacenter_id VARCHAR(36) NOT NULL,
	vim_id VARCHAR(36) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT FK__images FOREIGN KEY (image_id) REFERENCES images (uuid) ON UPDATE CASCADE ON DELETE CASCADE,
	CONSTRAINT FK__datacenters_i FOREIGN KEY (datacenter_id) REFERENCES datacenters (uuid) ON UPDATE CASCADE ON DELETE CASCADE  )
        COLLATE='utf8_general_ci'
        ENGINE=InnoDB;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      migrate data from table 'vms' into 'images'"
    echo "INSERT INTO images (uuid, name, location) SELECT DISTINCT vim_image_id, vim_image_id, image_path FROM vms;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO datacenters_images (image_id, datacenter_id, vim_id)
          SELECT DISTINCT vim_image_id, datacenters.uuid, vim_image_id FROM vms JOIN datacenters;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Add table 'flavors' and 'datacenter_flavors'"
    echo "CREATE TABLE flavors (
	uuid VARCHAR(36) NOT NULL,
	name VARCHAR(50) NOT NULL,
	description VARCHAR(100) NULL,
	disk SMALLINT(5) UNSIGNED NULL DEFAULT NULL,
	ram SMALLINT(5) UNSIGNED NULL DEFAULT NULL,
	vcpus SMALLINT(5) UNSIGNED NULL DEFAULT NULL,
	extended VARCHAR(2000) NULL DEFAULT NULL COMMENT 'Extra description json format of needed resources and pining, orginized in sets per numa',
	PRIMARY KEY (uuid)  )
        COLLATE='utf8_general_ci'
        ENGINE=InnoDB;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "CREATE TABLE datacenters_flavors (
	id INT NOT NULL AUTO_INCREMENT,
	flavor_id VARCHAR(36) NOT NULL,
	datacenter_id VARCHAR(36) NOT NULL,
	vim_id VARCHAR(36) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT FK__flavors FOREIGN KEY (flavor_id) REFERENCES flavors (uuid) ON UPDATE CASCADE ON DELETE CASCADE,
	CONSTRAINT FK__datacenters_f FOREIGN KEY (datacenter_id) REFERENCES datacenters (uuid) ON UPDATE CASCADE ON DELETE CASCADE  )
        COLLATE='utf8_general_ci'
        ENGINE=InnoDB;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      migrate data from table 'vms' into 'flavors'"
    echo "INSERT INTO flavors (uuid, name) SELECT DISTINCT vim_flavor_id, vim_flavor_id FROM vms;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO datacenters_flavors (flavor_id, datacenter_id, vim_id)
          SELECT DISTINCT vim_flavor_id, datacenters.uuid, vim_flavor_id FROM vms JOIN datacenters;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE vms ALTER vim_flavor_id DROP DEFAULT, ALTER vim_image_id DROP DEFAULT;
          ALTER TABLE vms CHANGE COLUMN vim_flavor_id flavor_id VARCHAR(36) NOT NULL COMMENT 'Link to flavor table' AFTER vnf_id,
          CHANGE COLUMN vim_image_id image_id VARCHAR(36) NOT NULL COMMENT 'Link to image table' AFTER flavor_id, 
          ADD CONSTRAINT FK_vms_images  FOREIGN KEY (image_id) REFERENCES  images (uuid),
          ADD CONSTRAINT FK_vms_flavors FOREIGN KEY (flavor_id) REFERENCES flavors (uuid);
         " | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO schema_version (version_int, version, openmano_ver, comments, date) VALUES (2, '0.2', '0.2.5', 'new tables images,flavors', '2015-07-13');" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1

}   
     
function downgrade_from_2(){
    echo "    downgrade database from version 0.2 to version 0.1"
    echo "       migrate back data from 'datacenters_images' 'datacenters_flavors' into 'vms'"
    echo "ALTER TABLE vms ALTER image_id DROP DEFAULT, ALTER flavor_id DROP DEFAULT;
          ALTER TABLE vms CHANGE COLUMN flavor_id vim_flavor_id VARCHAR(36) NOT NULL COMMENT 'Flavor ID in the VIM DB' AFTER vnf_id,
          CHANGE COLUMN image_id vim_image_id VARCHAR(36) NOT NULL COMMENT 'Image ID in the VIM DB' AFTER vim_flavor_id,
          DROP FOREIGN KEY FK_vms_flavors, DROP INDEX FK_vms_flavors,
          DROP FOREIGN KEY FK_vms_images, DROP INDEX FK_vms_images;
         " | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
#    echo "UPDATE v SET v.vim_image_id=di.vim_id
#          FROM  vms as v INNER JOIN images as i ON v.vim_image_id=i.uuid 
#          INNER JOIN datacenters_images as di ON i.uuid=di.image_id;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Delete columns 'user/passwd' from 'vim_tenants'"
    echo "ALTER TABLE vim_tenants DROP COLUMN user, DROP COLUMN passwd; " | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "        delete tables 'datacenter_images', 'images'"
    echo "DROP TABLE \`datacenters_images\`;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "DROP TABLE \`images\`;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "        delete tables 'datacenter_flavors', 'flavors'"
    echo "DROP TABLE \`datacenters_flavors\`;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "DROP TABLE \`flavors\`;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "DELETE FROM schema_version WHERE version_int='2';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}

function upgrade_to_3(){
    echo "    upgrade database from version 0.2 to version 0.3"
    echo "      Change table 'logs', 'uuids"
    echo "ALTER TABLE logs CHANGE COLUMN related related VARCHAR(36) NOT NULL COMMENT 'Relevant element for the log' AFTER nfvo_tenant_id;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE uuids CHANGE COLUMN used_at used_at VARCHAR(36) NULL DEFAULT NULL COMMENT 'Table that uses this UUID' AFTER created_at;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Add column created to table 'datacenters_images' and 'datacenters_flavors'"
    for table in datacenters_images datacenters_flavors
    do
        echo "ALTER TABLE $table ADD COLUMN created ENUM('true','false') NOT NULL DEFAULT 'false' 
            COMMENT 'Indicates if it has been created by openmano, or already existed' AFTER vim_id;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    done
    echo "ALTER TABLE images CHANGE COLUMN metadata metadata VARCHAR(2000) NULL DEFAULT NULL AFTER description;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Allow null to column 'vim_interface_id' in 'instance_interfaces'"
    echo "ALTER TABLE instance_interfaces CHANGE COLUMN vim_interface_id vim_interface_id VARCHAR(36) NULL DEFAULT NULL COMMENT 'vim identity for that interface' AFTER interface_id; " | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Add column config to table 'datacenters'"
    echo "ALTER TABLE datacenters ADD COLUMN config VARCHAR(4000) NULL DEFAULT NULL COMMENT 'extra config information in json' AFTER vim_url_admin;
	" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Add column datacenter_id to table 'vim_tenants'"
    echo "ALTER TABLE vim_tenants ADD COLUMN datacenter_id VARCHAR(36) NULL COMMENT 'Datacenter of this tenant' AFTER uuid,
	DROP INDEX name, DROP INDEX vim_tenant_id;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE vim_tenants CHANGE COLUMN name vim_tenant_name VARCHAR(36) NULL DEFAULT NULL COMMENT 'tenant name at VIM' AFTER datacenter_id,
	CHANGE COLUMN vim_tenant_id vim_tenant_id VARCHAR(36) NULL DEFAULT NULL COMMENT 'Tenant ID at VIM' AFTER vim_tenant_name;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "UPDATE vim_tenants as vt LEFT JOIN tenants_datacenters as td ON vt.uuid=td.vim_tenant_id
	SET vt.datacenter_id=td.datacenter_id;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "DELETE FROM vim_tenants WHERE datacenter_id is NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE vim_tenants ALTER datacenter_id DROP DEFAULT;
	ALTER TABLE vim_tenants
	CHANGE COLUMN datacenter_id datacenter_id VARCHAR(36) NOT NULL COMMENT 'Datacenter of this tenant' AFTER uuid;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE vim_tenants ADD CONSTRAINT FK_vim_tenants_datacenters FOREIGN KEY (datacenter_id) REFERENCES datacenters (uuid)
	ON UPDATE CASCADE ON DELETE CASCADE;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1

    echo "INSERT INTO schema_version (version_int, version, openmano_ver, comments, date) VALUES (3, '0.3', '0.3.3', 'alter vim_tenant tables', '2015-07-28');" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}


function downgrade_from_3(){
    echo "    downgrade database from version 0.3 to version 0.2"
    echo "      Change back table 'logs', 'uuids'"
    echo "ALTER TABLE logs CHANGE COLUMN related related ENUM('nfvo_tenants','datacenters','vim_tenants','tenants_datacenters','vnfs','vms','interfaces','nets','scenarios','sce_vnfs','sce_interfaces','sce_nets','instance_scenarios','instance_vnfs','instance_vms','instance_nets','instance_interfaces') NOT NULL COMMENT 'Relevant element for the log' AFTER nfvo_tenant_id;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE uuids CHANGE COLUMN used_at used_at ENUM('nfvo_tenants','datacenters','vim_tenants','vnfs','vms','interfaces','nets','scenarios','sce_vnfs','sce_interfaces','sce_nets','instance_scenarios','instance_vnfs','instance_vms','instance_nets','instance_interfaces') NULL DEFAULT NULL COMMENT 'Table that uses this UUID' AFTER created_at;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Delete column created from table 'datacenters_images' and 'datacenters_flavors'"
    for table in datacenters_images datacenters_flavors
    do
        echo "ALTER TABLE $table DROP COLUMN created;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    done
    echo "ALTER TABLE images CHANGE COLUMN metadata metadata VARCHAR(400) NULL DEFAULT NULL AFTER description;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Deny back null to column 'vim_interface_id' in 'instance_interfaces'"
    echo "ALTER TABLE instance_interfaces CHANGE COLUMN vim_interface_id vim_interface_id VARCHAR(36) NOT NULL COMMENT 'vim identity for that interface' AFTER interface_id; " | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "       Delete column config to table 'datacenters'"
    echo "ALTER TABLE datacenters DROP COLUMN config;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "       Delete column datacenter_id to table 'vim_tenants'"
    echo "ALTER TABLE vim_tenants DROP COLUMN datacenter_id, DROP FOREIGN KEY FK_vim_tenants_datacenters;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE vim_tenants CHANGE COLUMN vim_tenant_name name VARCHAR(36) NULL DEFAULT NULL COMMENT '' AFTER uuid"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE vim_tenants ALTER name DROP DEFAULT;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE vim_tenants CHANGE COLUMN name name VARCHAR(36) NOT NULL AFTER uuid"| $DBCMD || ! echo "Warning changing column name at vim_tenants!"
    echo "ALTER TABLE vim_tenants ADD UNIQUE INDEX name (name);" | $DBCMD || ! echo "Warning add unique index name at vim_tenants!"
    echo "ALTER TABLE vim_tenants ALTER vim_tenant_id DROP DEFAULT;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE vim_tenants CHANGE COLUMN vim_tenant_id vim_tenant_id VARCHAR(36) NOT NULL COMMENT 'Tenant ID in the VIM DB' AFTER name;"| $DBCMD || ! echo "Warning changing column vim_tenant_id at vim_tenants!"
    echo "ALTER TABLE vim_tenants ADD UNIQUE INDEX vim_tenant_id (vim_tenant_id);" | $DBCMD || ! echo "Warning add unique index vim_tenant_id at vim_tenants!"
    echo "DELETE FROM schema_version WHERE version_int='3';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}

function upgrade_to_4(){
    echo "    upgrade database from version 0.3 to version 0.4"
    echo "      Enlarge graph field at tables 'sce_vnfs', 'sce_nets'"
    for table in sce_vnfs sce_nets
    do
        echo "ALTER TABLE $table CHANGE COLUMN graph graph VARCHAR(2000) NULL DEFAULT NULL AFTER modified_at;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    done
    echo "ALTER TABLE datacenters CHANGE COLUMN type type VARCHAR(36) NOT NULL DEFAULT 'openvim' AFTER description;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO schema_version (version_int, version, openmano_ver, comments, date) VALUES (4, '0.4', '0.3.5', 'enlarge graph field at sce_vnfs/nets', '2015-10-20');" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}

function downgrade_from_4(){
    echo "    downgrade database from version 0.4 to version 0.3"
    echo "      Shorten back graph field at tables 'sce_vnfs', 'sce_nets'"
    for table in sce_vnfs sce_nets
    do
        echo "ALTER TABLE $table CHANGE COLUMN graph graph VARCHAR(2000) NULL DEFAULT NULL AFTER modified_at;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    done
    echo "ALTER TABLE datacenters CHANGE COLUMN type type ENUM('openvim','openstack') NOT NULL DEFAULT 'openvim' AFTER description;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "DELETE FROM schema_version WHERE version_int='4';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}

function upgrade_to_5(){
    echo "    upgrade database from version 0.4 to version 0.5"
    echo "      Add 'mac' field for bridge interfaces in table 'interfaces'"
    echo "ALTER TABLE interfaces ADD COLUMN mac CHAR(18) NULL DEFAULT NULL AFTER model;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO schema_version (version_int, version, openmano_ver, comments, date) VALUES (5, '0.5', '0.4.1', 'Add mac address for bridge interfaces', '2015-12-14');" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function downgrade_from_5(){
    echo "    downgrade database from version 0.5 to version 0.4"
    echo "      Remove 'mac' field for bridge interfaces in table 'interfaces'"
    echo "ALTER TABLE interfaces DROP COLUMN mac;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "DELETE FROM schema_version WHERE version_int='5';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}

function upgrade_to_6(){
    echo "    upgrade database from version 0.5 to version 0.6"
    echo "      Add 'descriptor' field text to 'vnfd', 'scenarios'"
    echo "ALTER TABLE vnfs ADD COLUMN descriptor TEXT NULL DEFAULT NULL COMMENT 'Original text descriptor used for create the VNF' AFTER class;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE scenarios ADD COLUMN descriptor TEXT NULL DEFAULT NULL COMMENT 'Original text descriptor used for create the scenario' AFTER modified_at;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Add 'last_error', 'vim_info' to 'instance_vms', 'instance_nets'"
    echo "ALTER TABLE instance_vms  ADD COLUMN error_msg VARCHAR(1024) NULL DEFAULT NULL AFTER status;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_vms  ADD COLUMN vim_info TEXT NULL DEFAULT NULL AFTER error_msg;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_vms  CHANGE COLUMN status status ENUM('ACTIVE','INACTIVE','BUILD','ERROR','VIM_ERROR','PAUSED','SUSPENDED','DELETED') NOT NULL DEFAULT 'BUILD' AFTER vim_vm_id;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_nets ADD COLUMN error_msg VARCHAR(1024) NULL DEFAULT NULL AFTER status;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_nets ADD COLUMN vim_info TEXT NULL DEFAULT NULL AFTER error_msg;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_nets CHANGE COLUMN status status ENUM('ACTIVE','DOWN','BUILD','ERROR','VIM_ERROR','INACTIVE','DELETED') NOT NULL DEFAULT 'BUILD' AFTER instance_scenario_id;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Add 'mac_address', 'ip_address', 'vim_info' to 'instance_interfaces'"
    echo "ALTER TABLE instance_interfaces ADD COLUMN mac_address VARCHAR(32) NULL DEFAULT NULL AFTER vim_interface_id, ADD COLUMN ip_address VARCHAR(64) NULL DEFAULT NULL AFTER mac_address, ADD COLUMN vim_info TEXT NULL DEFAULT NULL AFTER ip_address;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Add 'sce_vnf_id','datacenter_id','vim_tenant_id' field to 'instance_vnfs'"
    echo "ALTER TABLE instance_vnfs ADD COLUMN sce_vnf_id VARCHAR(36) NULL DEFAULT NULL AFTER vnf_id, ADD CONSTRAINT FK_instance_vnfs_sce_vnfs FOREIGN KEY (sce_vnf_id) REFERENCES sce_vnfs (uuid) ON UPDATE CASCADE ON DELETE SET NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_vnfs ADD COLUMN vim_tenant_id VARCHAR(36) NULL DEFAULT NULL AFTER sce_vnf_id, ADD CONSTRAINT FK_instance_vnfs_vim_tenants FOREIGN KEY (vim_tenant_id) REFERENCES vim_tenants (uuid) ON UPDATE RESTRICT ON DELETE RESTRICT;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_vnfs ADD COLUMN datacenter_id VARCHAR(36) NULL DEFAULT NULL AFTER vim_tenant_id, ADD CONSTRAINT FK_instance_vnfs_datacenters FOREIGN KEY (datacenter_id) REFERENCES datacenters (uuid) ON UPDATE RESTRICT ON DELETE RESTRICT;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Add 'sce_net_id','net_id','datacenter_id','vim_tenant_id' field to 'instance_nets'"
    echo "ALTER TABLE instance_nets ADD COLUMN sce_net_id VARCHAR(36) NULL DEFAULT NULL AFTER instance_scenario_id, ADD CONSTRAINT FK_instance_nets_sce_nets FOREIGN KEY (sce_net_id) REFERENCES sce_nets (uuid) ON UPDATE CASCADE ON DELETE SET NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_nets ADD COLUMN net_id VARCHAR(36) NULL DEFAULT NULL AFTER sce_net_id, ADD CONSTRAINT FK_instance_nets_nets FOREIGN KEY (net_id) REFERENCES nets (uuid) ON UPDATE CASCADE ON DELETE SET NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_nets ADD COLUMN vim_tenant_id VARCHAR(36) NULL DEFAULT NULL AFTER net_id, ADD CONSTRAINT FK_instance_nets_vim_tenants FOREIGN KEY (vim_tenant_id) REFERENCES vim_tenants (uuid) ON UPDATE RESTRICT ON DELETE RESTRICT;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_nets ADD COLUMN datacenter_id VARCHAR(36) NULL DEFAULT NULL AFTER vim_tenant_id, ADD CONSTRAINT FK_instance_nets_datacenters FOREIGN KEY (datacenter_id) REFERENCES datacenters (uuid) ON UPDATE RESTRICT ON DELETE RESTRICT;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO schema_version (version_int, version, openmano_ver, comments, date) VALUES (6, '0.6', '0.4.2', 'Adding VIM status info', '2015-12-22');" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function downgrade_from_6(){
    echo "    downgrade database from version 0.6 to version 0.5"
    echo "      Remove 'descriptor' field from 'vnfd', 'scenarios' tables"
    echo "ALTER TABLE vnfs      DROP COLUMN descriptor;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE scenarios DROP COLUMN descriptor;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Remove 'last_error', 'vim_info' from 'instance_vms', 'instance_nets'"
    echo "ALTER TABLE instance_vms  DROP COLUMN error_msg, DROP COLUMN vim_info;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_vms  CHANGE COLUMN status status ENUM('ACTIVE','PAUSED','INACTIVE','CREATING','ERROR','DELETING') NOT NULL DEFAULT 'CREATING' AFTER vim_vm_id;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_nets DROP COLUMN error_msg, DROP COLUMN vim_info;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_nets CHANGE COLUMN status status ENUM('ACTIVE','DOWN','BUILD','ERROR') NOT NULL DEFAULT 'BUILD' AFTER instance_scenario_id;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Remove 'mac_address', 'ip_address', 'vim_info' from 'instance_interfaces'"
    echo "ALTER TABLE instance_interfaces DROP COLUMN mac_address, DROP COLUMN ip_address, DROP COLUMN vim_info;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Remove 'sce_vnf_id','datacenter_id','vim_tenant_id' field from 'instance_vnfs'"
    echo "ALTER TABLE instance_vnfs DROP COLUMN sce_vnf_id, DROP FOREIGN KEY FK_instance_vnfs_sce_vnfs;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_vnfs DROP COLUMN vim_tenant_id, DROP FOREIGN KEY FK_instance_vnfs_vim_tenants;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_vnfs DROP COLUMN datacenter_id, DROP FOREIGN KEY FK_instance_vnfs_datacenters;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      Remove 'sce_net_id','net_id','datacenter_id','vim_tenant_id' field from 'instance_nets'"
    echo "ALTER TABLE instance_nets DROP COLUMN sce_net_id, DROP FOREIGN KEY FK_instance_nets_sce_nets;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_nets DROP COLUMN net_id, DROP FOREIGN KEY FK_instance_nets_nets;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_nets DROP COLUMN vim_tenant_id, DROP FOREIGN KEY FK_instance_nets_vim_tenants;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_nets DROP COLUMN datacenter_id, DROP FOREIGN KEY FK_instance_nets_datacenters;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "DELETE FROM schema_version WHERE version_int='6';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}

function upgrade_to_7(){
    echo "    upgrade database from version 0.6 to version 0.7"
    echo "      Change created_at, modified_at from timestamp to unix float at all database"
    for table in datacenters datacenter_nets instance_nets instance_scenarios instance_vms instance_vnfs interfaces nets nfvo_tenants scenarios sce_interfaces sce_nets sce_vnfs tenants_datacenters vim_tenants vms vnfs uuids
    do
         echo -en "        $table               \r"
         echo "ALTER TABLE $table ADD COLUMN created_at_ DOUBLE NOT NULL after created_at;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
         echo "UPDATE $table SET created_at_=unix_timestamp(created_at);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
         echo "ALTER TABLE $table DROP COLUMN created_at, CHANGE COLUMN created_at_ created_at DOUBLE NOT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
         [[ $table == uuids ]] || echo "ALTER TABLE $table CHANGE COLUMN modified_at modified_at DOUBLE NULL DEFAULT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    done
    
    echo "      Add 'descriptor' field text to 'vnfd', 'scenarios'"
    echo "INSERT INTO schema_version (version_int, version, openmano_ver, comments, date) VALUES (7, '0.7', '0.4.3', 'Changing created_at time at database', '2016-01-25');" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function downgrade_from_7(){
    echo "    downgrade database from version 0.7 to version 0.6"
    echo "      Change back created_at, modified_at from unix float to timestamp at all database"
    for table in datacenters datacenter_nets instance_nets instance_scenarios instance_vms instance_vnfs interfaces nets nfvo_tenants scenarios sce_interfaces sce_nets sce_vnfs tenants_datacenters vim_tenants vms vnfs uuids
    do
         echo -en "        $table               \r"
         echo "ALTER TABLE $table ADD COLUMN created_at_ TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP after created_at;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
         echo "UPDATE $table SET created_at_=from_unixtime(created_at);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
         echo "ALTER TABLE $table DROP COLUMN created_at, CHANGE COLUMN created_at_ created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
         [[ $table == uuids ]] || echo "ALTER TABLE $table CHANGE COLUMN modified_at modified_at TIMESTAMP NULL DEFAULT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    done
    echo "      Remove 'descriptor' field from 'vnfd', 'scenarios' tables"
    echo "DELETE FROM schema_version WHERE version_int='7';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}

function upgrade_to_8(){
    echo "    upgrade database from version 0.7 to version 0.8"
    echo "      Change enalarge name, description to 255 at all database"
    for table in datacenters datacenter_nets flavors images instance_scenarios nets nfvo_tenants scenarios sce_nets sce_vnfs vms vnfs
    do
         echo -en "        $table               \r"
         echo "ALTER TABLE $table CHANGE COLUMN name name VARCHAR(255) NOT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
         echo "ALTER TABLE $table CHANGE COLUMN description description VARCHAR(255) NULL DEFAULT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    done
    echo -en "        interfaces           \r"
    echo "ALTER TABLE interfaces CHANGE COLUMN internal_name internal_name VARCHAR(255) NOT NULL, CHANGE COLUMN external_name external_name VARCHAR(255) NULL DEFAULT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE vim_tenants CHANGE COLUMN vim_tenant_name vim_tenant_name VARCHAR(64) NULL DEFAULT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo -en "        vim_tenants          \r"
    echo "ALTER TABLE vim_tenants CHANGE COLUMN user user VARCHAR(64) NULL DEFAULT NULL, CHANGE COLUMN passwd passwd VARCHAR(64) NULL DEFAULT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO schema_version (version_int, version, openmano_ver, comments, date) VALUES (8, '0.8', '0.4.32', 'Enlarging name at database', '2016-02-01');" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function downgrade_from_8(){
    echo "    downgrade database from version 0.8 to version 0.7"
    echo "      Change back name,description to shorter length at all database"
    for table in datacenters datacenter_nets flavors images instance_scenarios nets nfvo_tenants scenarios sce_nets sce_vnfs vms vnfs
    do
         name_length=50
         [[ $table == flavors ]] || [[ $table == images ]] || name_length=36 
         echo -en "        $table               \r"
         echo "ALTER TABLE $table CHANGE COLUMN name name VARCHAR($name_length) NOT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
         echo "ALTER TABLE $table CHANGE COLUMN description description VARCHAR(100) NULL DEFAULT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    done
    echo -en "        interfaces           \r"
    echo "ALTER TABLE interfaces CHANGE COLUMN internal_name internal_name VARCHAR(25) NOT NULL, CHANGE COLUMN external_name external_name VARCHAR(25) NULL DEFAULT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo -en "        vim_tenants          \r"
    echo "ALTER TABLE vim_tenants CHANGE COLUMN vim_tenant_name vim_tenant_name VARCHAR(36) NULL DEFAULT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE vim_tenants CHANGE COLUMN user user VARCHAR(36) NULL DEFAULT NULL, CHANGE COLUMN passwd passwd VARCHAR(50) NULL DEFAULT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "DELETE FROM schema_version WHERE version_int='8';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function upgrade_to_9(){
    echo "    upgrade database from version 0.8 to version 0.9"
    echo "      Add more status to 'instance_vms'"
    echo "ALTER TABLE instance_vms CHANGE COLUMN status status ENUM('ACTIVE:NoMgmtIP','ACTIVE','INACTIVE','BUILD','ERROR','VIM_ERROR','PAUSED','SUSPENDED','DELETED') NOT NULL DEFAULT 'BUILD';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO schema_version (version_int, version, openmano_ver, comments, date) VALUES (9, '0.9', '0.4.33', 'Add ACTIVE:NoMgmtIP to instance_vms table', '2016-02-05');" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function downgrade_from_9(){
    echo "    downgrade database from version 0.9 to version 0.8"
    echo "      Add more status to 'instance_vms'"
    echo "ALTER TABLE instance_vms CHANGE COLUMN status status ENUM('ACTIVE','INACTIVE','BUILD','ERROR','VIM_ERROR','PAUSED','SUSPENDED','DELETED') NOT NULL DEFAULT 'BUILD';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "DELETE FROM schema_version WHERE version_int='9';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function upgrade_to_10(){
    echo "    upgrade database from version 0.9 to version 0.10"
    echo "      add tenant to 'vnfs'"
    echo "ALTER TABLE vnfs ADD COLUMN tenant_id VARCHAR(36) NULL DEFAULT NULL AFTER name, ADD CONSTRAINT FK_vnfs_nfvo_tenants FOREIGN KEY (tenant_id) REFERENCES nfvo_tenants (uuid) ON UPDATE CASCADE ON DELETE SET NULL, CHANGE COLUMN public public ENUM('true','false') NOT NULL DEFAULT 'false' AFTER physical, DROP INDEX name, DROP INDEX path, DROP COLUMN path;"  | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE scenarios DROP FOREIGN KEY FK_scenarios_nfvo_tenants;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE scenarios CHANGE COLUMN nfvo_tenant_id tenant_id VARCHAR(36) NULL DEFAULT NULL after name, ADD CONSTRAINT FK_scenarios_nfvo_tenants FOREIGN KEY (tenant_id) REFERENCES nfvo_tenants (uuid);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_scenarios DROP FOREIGN KEY FK_instance_scenarios_nfvo_tenants;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_scenarios CHANGE COLUMN nfvo_tenant_id tenant_id VARCHAR(36) NULL DEFAULT NULL after name, ADD CONSTRAINT FK_instance_scenarios_nfvo_tenants FOREIGN KEY (tenant_id) REFERENCES nfvo_tenants (uuid);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      rename 'vim_tenants' table to 'datacenter_tenants'"
    echo "RENAME TABLE vim_tenants TO datacenter_tenants;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    for table in tenants_datacenters instance_scenarios instance_vnfs instance_nets
    do
        NULL="NOT NULL"
        [[ $table == instance_vnfs ]] && NULL="NULL DEFAULT NULL"
        echo "ALTER TABLE ${table} DROP FOREIGN KEY FK_${table}_vim_tenants;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
        echo "ALTER TABLE ${table} ALTER vim_tenant_id DROP DEFAULT;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
        echo "ALTER TABLE ${table} CHANGE COLUMN vim_tenant_id datacenter_tenant_id VARCHAR(36)  ${NULL} AFTER datacenter_id, ADD CONSTRAINT FK_${table}_datacenter_tenants FOREIGN KEY (datacenter_tenant_id) REFERENCES datacenter_tenants (uuid); " | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    done    
    echo "INSERT INTO schema_version (version_int, version, openmano_ver, comments, date) VALUES (10, '0.10', '0.4.36', 'tenant management of vnfs,scenarios', '2016-03-08');" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}

function downgrade_from_10(){
    echo "    downgrade database from version 0.10 to version 0.9"
    echo "      remove tenant from 'vnfs'"
    echo "ALTER TABLE vnfs DROP COLUMN tenant_id, DROP FOREIGN KEY FK_vnfs_nfvo_tenants, ADD UNIQUE INDEX name (name), ADD COLUMN path VARCHAR(100) NULL DEFAULT NULL COMMENT 'Path where the YAML descriptor of the VNF can be found. NULL if it is a physical network function.' AFTER name, ADD UNIQUE INDEX path (path), CHANGE COLUMN public public ENUM('true','false') NOT NULL DEFAULT 'true' AFTER physical;"  | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE scenarios DROP FOREIGN KEY FK_scenarios_nfvo_tenants;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE scenarios CHANGE COLUMN tenant_id nfvo_tenant_id VARCHAR(36) NULL DEFAULT NULL after name, ADD CONSTRAINT FK_scenarios_nfvo_tenants FOREIGN KEY (nfvo_tenant_id) REFERENCES nfvo_tenants (uuid);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_scenarios DROP FOREIGN KEY FK_instance_scenarios_nfvo_tenants;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE instance_scenarios CHANGE COLUMN tenant_id nfvo_tenant_id VARCHAR(36) NULL DEFAULT NULL after name, ADD CONSTRAINT FK_instance_scenarios_nfvo_tenants FOREIGN KEY (nfvo_tenant_id) REFERENCES nfvo_tenants (uuid);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      rename back 'datacenter_tenants' table to 'vim_tenants'"
    echo "RENAME TABLE datacenter_tenants TO vim_tenants;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    for table in tenants_datacenters instance_scenarios instance_vnfs instance_nets
    do
        echo "ALTER TABLE ${table} DROP FOREIGN KEY FK_${table}_datacenter_tenants;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
        NULL="NOT NULL"
        [[ $table == instance_vnfs ]] && NULL="NULL DEFAULT NULL"
        echo "ALTER TABLE ${table} ALTER datacenter_tenant_id DROP DEFAULT;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
        echo "ALTER TABLE ${table} CHANGE COLUMN datacenter_tenant_id vim_tenant_id VARCHAR(36) $NULL AFTER datacenter_id, ADD CONSTRAINT FK_${table}_vim_tenants FOREIGN KEY (vim_tenant_id) REFERENCES vim_tenants (uuid); " | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    done    
    echo "DELETE FROM schema_version WHERE version_int='10';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}

function upgrade_to_X(){
    echo "      change 'datacenter_nets'"
    echo "ALTER TABLE datacenter_nets ADD COLUMN vim_tenant_id VARCHAR(36) NOT NULL AFTER datacenter_id, DROP INDEX name_datacenter_id, ADD UNIQUE INDEX name_datacenter_id (name, datacenter_id, vim_tenant_id);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function downgrade_from_X(){
    echo "      Change back 'datacenter_nets'"
    echo "ALTER TABLE datacenter_nets DROP COLUMN vim_tenant_id, DROP INDEX name_datacenter_id, ADD UNIQUE INDEX name_datacenter_id (name, datacenter_id);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
#TODO ... put funtions here


[ $DATABASE_TARGET_VER_NUM -eq $DATABASE_VER_NUM ] && echo "    current database version $DATABASE_VER is ok"
#UPGRADE DATABASE step by step
while [ $DATABASE_TARGET_VER_NUM -gt $DATABASE_VER_NUM ]
do
    DATABASE_VER_NUM=$((DATABASE_VER_NUM+1))
    upgrade_to_${DATABASE_VER_NUM}
    #FILE_="${DIRNAME}/upgrade_to_${DATABASE_VER_NUM}.sh"
    #[ ! -x "$FILE_" ] && echo "Error, can not find script '$FILE_' to upgrade" >&2 && exit -1
    #$FILE_ || exit -1  # if fail return
done

#DOWNGRADE DATABASE step by step
while [ $DATABASE_TARGET_VER_NUM -lt $DATABASE_VER_NUM ]
do
    #FILE_="${DIRNAME}/downgrade_from_${DATABASE_VER_NUM}.sh"
    #[ ! -x "$FILE_" ] && echo "Error, can not find script '$FILE_' to downgrade" >&2 && exit -1
    #$FILE_ || exit -1  # if fail return
    downgrade_from_${DATABASE_VER_NUM}
    DATABASE_VER_NUM=$((DATABASE_VER_NUM-1))
done

#echo done


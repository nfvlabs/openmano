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


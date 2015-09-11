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
#Upgrade/Downgrade openvim database preserving the content
#

DBUSER="vim"
DBPASS=""
DBHOST="localhost"
DBPORT="3306"
DBNAME="vim_db"
 
# Detect paths
MYSQL=$(which mysql)
AWK=$(which awk)
GREP=$(which grep)
DIRNAME=`dirname $0`

function usage(){
    echo -e "Usage: $0 OPTIONS  [{openvim_version}]"
    echo -e "  Upgrades/Downgrades openvim database preserving the content"
    echo -e "   if openvim_version is not provided it tries to get from openvimd.py using relative path"
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


#GET OPENVIM VERSION
OPENVIM_VER="$1"
if [ -z "$OPENVIM_VER" ]
then 
    OPENVIM_VER=`${DIRNAME}/../openvimd.py -v`
    OPENVIM_VER=${OPENVIM_VER%%-r*}
    OPENVIM_VER=${OPENVIM_VER##*version }
    echo "    Detected openvim version $OPENVIM_VER"
fi
VERSION_1=`echo $OPENVIM_VER | cut -f 1 -d"."`
VERSION_2=`echo $OPENVIM_VER | cut -f 2 -d"."`
VERSION_3=`echo $OPENVIM_VER | cut -f 3 -d"."`
if ! [ "$VERSION_1" -ge 0 -a "$VERSION_2" -ge 0 -a "$VERSION_3" -ge 0 ] 2>/dev/null
then 
    [ -n "$1" ] && echo "Invalid openvim version '$1', expected 'X.X.X'" >&2
    [ -z "$1" ] && echo "Can not get openvim version" >&2
    exit -1
fi
OPENVIM_VER_NUM=`printf "%d%03d%03d" ${VERSION_1} ${VERSION_2} ${VERSION_3}`

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
#check that the database seems a openvim database
if ! echo -e "show create table instances;\nshow create table numas" | $DBCMD >/dev/null 2>&1
then
    echo "    database $DBNAME does not seem to be an openvim database" >&2
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
[ $OPENVIM_VER_NUM -gt 1091 ] && DATABASE_TARGET_VER_NUM=1   #>0.1.91 =>  1
[ $OPENVIM_VER_NUM -ge 2003 ] && DATABASE_TARGET_VER_NUM=2   #0.2.03  =>  2
[ $OPENVIM_VER_NUM -ge 2005 ] && DATABASE_TARGET_VER_NUM=3   #0.2.5   =>  3
[ $OPENVIM_VER_NUM -ge 3001 ] && DATABASE_TARGET_VER_NUM=4   #0.3.1   =>  4
#TODO ... put next versions here


function upgrade_to_1(){
    echo "    upgrade database from version 0.0 to version 0.1"
    echo "      CREATE TABLE \`schema_version\`"
    echo "CREATE TABLE \`schema_version\` (
	\`version_int\` INT NOT NULL COMMENT 'version as a number. Must not contain gaps',
	\`version\` VARCHAR(20) NOT NULL COMMENT 'version as a text',
	\`openvim_ver\` VARCHAR(20) NOT NULL COMMENT 'openvim version',
	\`comments\` VARCHAR(2000) NULL COMMENT 'changes to database',
	\`date\` DATE NULL,
	PRIMARY KEY (\`version_int\`)
	)
	COMMENT='database schema control version'
	COLLATE='utf8_general_ci'
	ENGINE=InnoDB;" | $DBCMD  || ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO \`schema_version\` (\`version_int\`, \`version\`, \`openvim_ver\`, \`comments\`, \`date\`)
	 VALUES (1, '0.1', '0.2.00', 'insert schema_version; alter nets with last_error column', '2015-05-05');" | $DBCMD
    echo "      ALTER TABLE \`nets\`, ADD COLUMN \`last_error\`"
    echo "ALTER TABLE \`nets\` 
         ADD COLUMN \`last_error\` VARCHAR(200) NULL AFTER \`status\`;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function downgrade_from_1(){
    echo "    downgrade database from version 0.1 to version 0.0"
    echo "      ALTER TABLE \`nets\` DROP COLUMN \`last_error\`"
    echo "ALTER TABLE \`nets\` DROP COLUMN \`last_error\`;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      DROP TABLE \`schema_version\`"
    echo "DROP TABLE \`schema_version\`;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function upgrade_to_2(){
    echo "    upgrade database from version 0.1 to version 0.2"
    echo "      ALTER TABLE \`of_ports_pci_correspondence\` \`resources_port\` \`ports\` ADD COLUMN \`switch_dpid\`"
    for table in of_ports_pci_correspondence resources_port ports
    do
        echo "ALTER TABLE \`${table}\`
            ADD COLUMN \`switch_dpid\` CHAR(23) NULL DEFAULT NULL AFTER \`switch_port\`; " | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
        echo "ALTER TABLE ${table} CHANGE COLUMN switch_port switch_port VARCHAR(24) NULL DEFAULT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
        [ $table == of_ports_pci_correspondence ] ||
            echo "ALTER TABLE ${table} DROP INDEX vlan_switch_port, ADD UNIQUE INDEX vlan_switch_port (vlan, switch_port, switch_dpid);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    done
    echo "      UPDATE procedure UpdateSwitchPort"
    echo "DROP PROCEDURE IF EXISTS UpdateSwitchPort;
    delimiter //
    CREATE PROCEDURE UpdateSwitchPort() MODIFIES SQL DATA SQL SECURITY INVOKER
    COMMENT 'Load the openflow switch ports from of_ports_pci_correspondece into resoureces_port and ports'
    BEGIN
        #DELETES switch_port entry before writing, because if not it fails for key constrains
        UPDATE ports
        RIGHT JOIN resources_port as RP on ports.uuid=RP.port_id
        INNER JOIN resources_port as RP2 on RP2.id=RP.root_id
        INNER JOIN numas on RP.numa_id=numas.id
        INNER JOIN hosts on numas.host_id=hosts.uuid
        INNER JOIN of_ports_pci_correspondence as PC on hosts.ip_name=PC.ip_name and RP2.pci=PC.pci
        SET ports.switch_port=null, ports.switch_dpid=null, RP.switch_port=null, RP.switch_dpid=null;
        #write switch_port into resources_port and ports
        UPDATE ports
        RIGHT JOIN resources_port as RP on ports.uuid=RP.port_id
        INNER JOIN resources_port as RP2 on RP2.id=RP.root_id
        INNER JOIN numas on RP.numa_id=numas.id
        INNER JOIN hosts on numas.host_id=hosts.uuid
        INNER JOIN of_ports_pci_correspondence as PC on hosts.ip_name=PC.ip_name and RP2.pci=PC.pci
        SET ports.switch_port=PC.switch_port, ports.switch_dpid=PC.switch_dpid, RP.switch_port=PC.switch_port, RP.switch_dpid=PC.switch_dpid;
    END//
    delimiter ;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO \`schema_version\` (\`version_int\`, \`version\`, \`openvim_ver\`, \`comments\`, \`date\`)
	 VALUES (2, '0.2', '0.2.03', 'update Procedure UpdateSwitchPort', '2015-05-06');" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function upgrade_to_3(){
    echo "    upgrade database from version 0.2 to version 0.3"
    echo "     change size of source_name at table resources_port"
    echo "ALTER TABLE resources_port CHANGE COLUMN source_name source_name VARCHAR(24) NULL DEFAULT NULL AFTER port_id;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "     CREATE PROCEDURE GetAllAvailablePorts"
    echo "delimiter //
    CREATE PROCEDURE GetAllAvailablePorts(IN Numa INT) CONTAINS SQL SQL SECURITY INVOKER
    COMMENT 'Obtain all -including those not connected to switch port- ports available for a numa'
    BEGIN
	SELECT port_id, pci, Mbps, Mbps - Mbps_consumed as Mbps_free, totalSRIOV - coalesce(usedSRIOV,0) as availableSRIOV, switch_port, mac
	FROM
	(
	   SELECT id as port_id, Mbps, pci, switch_port, mac
	   FROM resources_port  
		WHERE numa_id = Numa AND id=root_id AND status = 'ok' AND instance_id IS NULL
	) as A
	INNER JOIN
	(
	   SELECT root_id, sum(Mbps_used) as Mbps_consumed, COUNT(id)-1 as totalSRIOV
		FROM resources_port  
		WHERE numa_id = Numa AND status = 'ok'
		GROUP BY root_id
	) as B
	ON A.port_id = B.root_id
	LEFT JOIN
	(
	   SELECT root_id,  COUNT(id) as usedSRIOV
		FROM resources_port  
		WHERE numa_id = Numa AND status = 'ok' AND instance_id IS NOT NULL
		GROUP BY root_id
	) as C
	ON A.port_id = C.root_id
	ORDER BY Mbps_free, availableSRIOV, pci;
    END//
    delimiter ;"| $DBCMD || !  ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) VALUES (3, '0.3', '0.2.5', 'New Procedure GetAllAvailablePorts', '2015-07-09');"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}

function upgrade_to_4(){
    echo "    upgrade database from version 0.3 to version 0.4"
    echo "     remove unique VLAN index at 'resources_port', 'ports'"
    echo "ALTER TABLE resources_port DROP INDEX vlan_switch_port;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE ports          DROP INDEX vlan_switch_port;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "     change table 'ports'"
    echo "ALTER TABLE ports CHANGE COLUMN model model VARCHAR(12) NULL DEFAULT NULL COMMENT 'driver model for bridge ifaces; PF,VF,VFnotShared for data ifaces' AFTER mac;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE ports DROP COLUMN vlan_changed;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE resources_port DROP COLUMN vlan;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) VALUES (4, '0.4', '0.3.1', 'Remove unique index VLAN at resources_port', '2015-09-04');"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}

function upgrade_to_X(){
    #TODO, this change of foreign key does not work
    echo "    upgrade database from version 0.X to version 0.X"
    echo "ALTER TABLE instances DROP FOREIGN KEY FK_instances_flavors, DROP INDEX FK_instances_flavors,
          DROP FOREIGN KEY FK_instances_images, DROP INDEX FK_instances_flavors,;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1 
    echo "ALTER TABLE instances
	ADD CONSTRAINT FK_instances_flavors FOREIGN KEY (flavor_id, tenant_id) REFERENCES tenants_flavors (flavor_id, tenant_id),
	ADD CONSTRAINT FK_instances_images FOREIGN KEY (image_id, tenant_id) REFERENCES tenants_images (image_id, tenant_id);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}

function downgrade_from_2(){
    echo "    downgrade database from version 0.2 to version 0.1"
    echo "      UPDATE procedure UpdateSwitchPort"
    echo "DROP PROCEDURE IF EXISTS UpdateSwitchPort;
    delimiter //
    CREATE PROCEDURE UpdateSwitchPort() MODIFIES SQL DATA SQL SECURITY INVOKER
    BEGIN
    UPDATE
        resources_port INNER JOIN (
            SELECT resources_port.id,KK.switch_port
            FROM resources_port INNER JOIN numas on resources_port.numa_id=numas.id
                INNER JOIN hosts on numas.host_id=hosts.uuid
                INNER JOIN of_ports_pci_correspondence as KK on hosts.ip_name=KK.ip_name and resources_port.pci=KK.pci
            ) as TABLA
        ON  resources_port.root_id=TABLA.id
    SET resources_port.switch_port=TABLA.switch_port
    WHERE resources_port.root_id=TABLA.id;
    END//
    delimiter ;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      ALTER TABLE \`of_ports_pci_correspondence\` \`resources_port\` \`ports\` DROP COLUMN \`switch_dpid\`"
    for table in of_ports_pci_correspondence resources_port ports
    do
        [ $table == of_ports_pci_correspondence ] ||
            echo "ALTER TABLE ${table} DROP INDEX vlan_switch_port, ADD UNIQUE INDEX vlan_switch_port (vlan, switch_port);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
        echo "ALTER TABLE \`${table}\` DROP COLUMN \`switch_dpid\`;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
        switch_port_size=12
        [ $table == of_ports_pci_correspondence ] && switch_port_size=50
        echo "ALTER TABLE ${table} CHANGE COLUMN switch_port switch_port VARCHAR(${switch_port_size}) NULL DEFAULT NULL;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    done
    echo "DELETE FROM \`schema_version\` WHERE \`version_int\` = '2';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function downgrade_from_3(){
    echo "    downgrade database from version 0.3 to version 0.2"
    echo "     change back size of source_name at table resources_port"
    echo "ALTER TABLE resources_port CHANGE COLUMN source_name source_name VARCHAR(20) NULL DEFAULT NULL AFTER port_id;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "      DROP PROCEDURE GetAllAvailablePorts"
    echo "DROP PROCEDURE GetAllAvailablePorts;" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "DELETE FROM schema_version WHERE version_int = '3';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
}
function downgrade_from_4(){
    echo "    downgrade database from version 0.4 to version 0.3"
    echo "     adding back unique index VLAN at 'resources_port','ports'"
    echo "ALTER TABLE resources_port ADD COLUMN vlan SMALLINT(5) UNSIGNED NULL DEFAULT NULL  AFTER Mbps_used;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "UPDATE resources_port SET vlan= 99+id-root_id WHERE id != root_id;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE resources_port ADD UNIQUE INDEX vlan_switch_port (vlan, switch_port, switch_dpid);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE    ports ADD UNIQUE INDEX vlan_switch_port (vlan, switch_port, switch_dpid);" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "     change back table 'ports'"
    echo "ALTER TABLE ports CHANGE COLUMN model model VARCHAR(12) NULL DEFAULT NULL AFTER mac;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "ALTER TABLE ports ADD COLUMN vlan_changed SMALLINT(5) NULL DEFAULT NULL COMMENT '!=NULL when original vlan have been changed to match a pmp net with all ports in the same vlan' AFTER switch_port;"| $DBCMD || ! echo "ERROR. Aborted!" || exit -1
    echo "DELETE FROM schema_version WHERE version_int = '4';" | $DBCMD || ! echo "ERROR. Aborted!" || exit -1
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


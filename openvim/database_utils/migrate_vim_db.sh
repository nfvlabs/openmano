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
    echo -e "  Upgrade/Downgrade openvim database preserving the content"
    echo -e "  if openvim_version is not provided it tries to get from openvimd.py using relative path"
    echo -e "  OPTIONS"
    echo -e "     -u USER  database user (it tries '$DBUSER' by default, asks if fail)"
    echo -e "     -p PASS  database password. Asks if fail"
    echo -e "     -P PORT  database port ($DBPORT by default)"
    echo -e "     -h HOST  database host ($DBHOST by default)"
    echo -e "     -d NAME  database name (it tries '$DBNAME' by default, asks if fail)"
    echo -e "     --help   show this help"
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
OPENVIM_VER_NUM="${VERSION_1}${VERSION_2}${VERSION_3}"
echo "Migrating to openvim version $OPENVIM_VER"

#check and ask for database user password
DBUSER_="-u$DBUSER"
[ -n "$DBPASS" ] && DBPASS_="-p$DBPASS"
DBHOST_="-h$DBHOST"
DBPORT_="-P$DBPORT"
while !  echo ";" | mysql $DBHOST_ $DBPORT_ $DBUSER_ $DBPASS_ $DBNAME >/dev/null
do
        [ -n "$logintry" ] &&  echo -e "\nInvalid database credentials!!!. Try again (Ctrl+c to abort)"
        [ -z "$logintry" ] &&  echo -e "\nProvide database name and credentials"
        read -p "mysql database name($DBNAME): " KK
        [ -n "$KK" ] && DBNAME="$KK"
        read -p "mysql user($DBUSER): " KK
        [ -n "$KK" ] && DBUSER="$KK" && DBUSER_="-u$DBUSER"
        read -s -p "mysql password: " DBPASS
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
    echo "database $DBNAME does not seem to be an openvim database" >&2
    exit -1;
fi

if ! echo 'show create table schema_version;' | $DBCMD >/dev/null 2>&1
then
    DATABASE_VER="0.0"
    DATABASE_VER_NUM=0
else 
    DATABASE_VER_NUM=`echo "select max(version_int) from schema_version;" | $DBCMD | tail -n+2` 
    DATABASE_VER=`echo "select version from schema_version where version_int='$DATABASE_VER_NUM';" | $DBCMD | tail -n+2` 
    [ "$DATABASE_VER_NUM" -lt 0 -o "$DATABASE_VER_NUM" -gt 100 ] && echo "Error can not get database version ($DATABASE_VER?)" >&2 && exit -1
    #echo "_${DATABASE_VER_NUM}_${DATABASE_VER}"
fi


#GET DATABASE TARGET VERSION
DATABASE_TARGET_VER_NUM=0
[ $OPENVIM_VER_NUM -gt 0191 ] && DATABASE_TARGET_VER_NUM=1   #0.1.90 =>  1
#TODO ... put next versions here


function upgrade_to_1(){
    echo "upgrade database from version 0.0 to version 0.1"
    echo "  CREATE TABLE \`schema_version\`"
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
	ENGINE=InnoDB;" | $DBCMD
    echo "INSERT INTO \`vim_db\`.\`schema_version\` (\`version_int\`, \`version\`, \`openvim_ver\`, \`comments\`, \`date\`)
	 VALUES (1, '0.1', '0.2.00', 'insert schema_version; alter nets with last_error column', '2015-05-05');" | $DBCMD
    echo "  ALTER TABLE \`nets\`, ADD COLUMN \`last_error\`"
    echo "ALTER TABLE \`nets\`
	ADD COLUMN \`last_error\` VARCHAR(200) NULL AFTER \`status\`;" | $DBCMD
}
function downgrade_from_1(){
    echo "downgrade database from version 0.1 to version 0.0"
    echo "  ALTER TABLE \`nets\` DROP COLUMN \`last_error\`"
    echo "ALTER TABLE \`nets\` DROP COLUMN \`last_error\`;" | $DBCMD
    echo "  DROP TABLE \`schema_version\`"
    echo "DROP TABLE \`schema_version\`;" | $DBCMD
}
#TODO ... put funtions here


[ $DATABASE_TARGET_VER_NUM -eq $DATABASE_VER_NUM ] && echo "current database version $DATABASE_VER is ok"
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


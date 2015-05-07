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
    echo -e "Usage: $0 OPTIONS"
    echo -e "  Dumps openvim database content"
    echo -e "  OPTIONS"
    echo -e "     -u USER  database user. '$DBUSER' by default. Prompts if DB access fails"
    echo -e "     -p PASS  database password. 'No password' by default. Prompts if DB access fails"
    echo -e "     -P PORT  database port. '$DBPORT' by default"
    echo -e "     -h HOST  database host. '$DBHOST' by default"
    echo -e "     -d NAME  database name. '$DBNAME' by default.  Prompts if DB access fails"
    echo -e "     --help   shows this help"
}

while getopts ":u:p:P:h:-:" o; do
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

#check and ask for database user password
DBUSER_="-u$DBUSER"
DBPASS_=""
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

 
#echo structure, including the content of schema_version
mysqldump $DBHOST_ $DBPORT_ $DBUSER_ $DBPASS_ --no-data --add-drop-table --add-drop-database --routines --databases $DBNAME > ${DIRNAME}/${DBNAME}_structure.sql
echo -e "\n\n\n\n" >> ${DIRNAME}/${DBNAME}_structure.sql
mysqldump $DBHOST_ $DBPORT_ $DBUSER_ $DBPASS_ --no-create-info $DBNAME --tables schema_version 2>/dev/null  >> ${DIRNAME}/${DBNAME}_structure.sql
echo "    ${DIRNAME}/${DBNAME}_structure.sql"

#echo only data
mysqldump $DBHOST_ $DBPORT_ $DBUSER_ $DBPASS_ --no-create-info $DBNAME > ${DIRNAME}/${DBNAME}_data.sql
echo "    ${DIRNAME}/${DBNAME}_data.sql"

#echo all
mysqldump $DBHOST_ $DBPORT_ $DBUSER_ $DBPASS_ --add-drop-table --add-drop-database --routines --databases $DBNAME > ${DIRNAME}/${DBNAME}_all.sql
echo "    ${DIRNAME}/${DBNAME}_all.sql"


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


MUSER="$1"
MPASS="$2"
MDB="$3"
HOST=localhost
PORT=3306
 
# Detect paths
MYSQL=$(which mysql)
AWK=$(which awk)
GREP=$(which grep)
DIRNAME=`dirname $0`
 
if [ $# -lt 3 ]
then
        echo "Usage: $0 {MySQL-User-Name} {MySQL-User-Password} {MySQL-Database-Name}"
        echo "Dump DB"
        exit 1
fi
if [ $# -ge 4 ]
then
        HOST=$4
elif [ $# -ge 5 ]
then
        PORT=$5
fi
 
#mysqldump -h $HOST -P $PORT -u $MUSER -p$MPASS --no-data $MDB > "$MDB"_structure.sql
mysqldump -h $HOST -P $PORT -u $MUSER -p$MPASS --no-data --add-drop-table --add-drop-database --routines --databases $MDB > ${DIRNAME}/${MDB}_structure.sql
echo "    ${DIRNAME}/${MDB}_structure.sql"

mysqldump -h $HOST -P $PORT -u $MUSER -p$MPASS --no-create-info $MDB > ${DIRNAME}/${MDB}_data.sql
echo "    ${DIRNAME}/${MDB}_data.sql"

mysqldump -h $HOST -P $PORT -u $MUSER -p$MPASS --add-drop-table --add-drop-database --routines --databases $MDB > ${DIRNAME}/${MDB}_all.sql
echo "    ${DIRNAME}/${MDB}_all.sql"

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

#launch openmano components inside a screen. It assumes a relative path ../openvim ../openmano ../../floodlight-0.90

DIRNAME=`dirname $0`
FLD=${DIRNAME}/../../floodlight-0.90

function usage(){
    echo -e "Usage: $0 [floodlight] [openvim] [openmano] start|stop|restart|status"
    echo -e "  Launch|Removes|Restart openmano components (by default all) on a screen"
}

function kill_pid(){
    #send TERM signal and wait 5 seconds and send KILL signal ir still running
    #PARAMS: $1: PID of process to terminate
    kill $1 #send TERM signal
    WAIT=5
    while [ $WAIT -gt 0 ] && ps -o pid -U $USER -u $USER | grep -q $1
    do
        sleep 1
        WAIT=$((WAIT-1))
        [ $WAIT -eq 0 ] && echo -n "sending SIGKILL...  " &&  kill -9 $1  #kill when count reach 0
    done
    echo "done"
   
}

#obtain parameters
openmano_list=""
#openmano_action="start"  #uncoment to get a default action
for param in $*
do
    [ "$param" == "start" -o "$param" == "stop"  -o "$param" == "restart" -o "$param" == "status" ] && openmano_action=$param  && continue
    [ "$param" == "openvim" -o "$param" == "vim"  ]    && openmano_list="$openmano_list vim"              && continue
    [ "$param" == "openmano" -o "$param" == "mano" ]   && openmano_list="$openmano_list mano"             && continue
    [ "$param" == "openflow" -o "$param" == "flow" -o "$param" == "floodlight" ] && openmano_list="flow $openmano_list" && continue
    [ "$param" == "-h" -o "$param" == "--help" ] && usage && exit 0
    #note flow that it must be the first element, because openvim relay on this
    
    #if none of above, reach this line because a param is incorrect
    echo "Unknown param '$param'" >&2
    usage >&2
    exit -1
done

#check action is provided
[ -z "$openmano_action" ] && usage >&2 && exit -1

#if no componenets supplied assume all
[ -z "$openmano_list" ] && openmano_list="flow vim mano"
 
for openmano_component in $openmano_list
do
    [ "${openmano_component}" == "flow" ] && openmano_cmd="floodlight.jar"  && openmano_name="floodlight"
    [ "${openmano_component}" == "vim" ]  && openmano_cmd="openvimd.py"     && openmano_name="openvim"
    [ "${openmano_component}" == "mano" ] && openmano_cmd="openmanod.py"    && openmano_name="openmano"
    #obtain PID of program
    component_id=`ps -o pid,cmd -U $USER -u $USER | grep -v grep | grep ${openmano_cmd} | awk '{print $1}'`

    #status
    if [ "$openmano_action" == "status" ]
    then
        #terminates program
        [ -n "$component_id" ] && echo "    $openmano_name running, pid $component_id"
        [ -z "$component_id" ] && echo "    $openmano_name stopped"
    fi

    #stop
    if [ "$openmano_action" == "stop" -o "$openmano_action" == "restart" ]
    then
        #terminates program
        [ -n "$component_id" ] && echo -n "    stopping $openmano_name ... " && kill_pid $component_id 
        component_id=""
        #terminates screen
        if screen -wipe | grep -q .$openmano_component
        then
            screen -S $openmano_component -p 0 -X stuff "exit\n"
            sleep 1
        fi
    fi

    #start
    if [ "$openmano_action" == "start" -o "$openmano_action" == "restart" ]
    then
        #check already running
        [ -n "$component_id" ] && echo "    $openmano_name is already running. Skipping" && continue
        #create screen if not created
        echo -n "    starting $openmano_name ... "
        if ! screen -wipe | grep -q .${openmano_component}
        then
            screen -dmS ${openmano_component}  bash
            sleep 1
        else
            echo -n " using existing screen '${openmano_component}' ... "
        fi
        #launch command to screen
        [ "${openmano_component}" != "flow" ] && screen -S ${openmano_component} -p 0 -X stuff "cd ${DIRNAME}/../open${openmano_component}\n" && sleep 1
        [ "${openmano_component}" == "flow" ] && screen -S flow -p 0 -X stuff "java  -Dlogback.configurationFile=${DIRNAME}/flow-logback.xml -jar ${FLD}/target/floodlight.jar -cf ${DIRNAME}/flow.properties\n"
        [ "${openmano_component}" != "flow" ] && screen -S ${openmano_component} -p 0 -X stuff "./${openmano_cmd}\n"
        sleep 10

        #check if is running
        if !  ps -f -U $USER -u $USER | grep -v grep | grep -q ${openmano_cmd}
        then
            echo "ERROR, it has exited. Run 'screen -x ${openmano_component}' to see the error"
            #exit 0
        else
            echo "running, execute 'screen -x ${openmano_component}' and Ctrl+c to terminate"
        fi
    fi
done





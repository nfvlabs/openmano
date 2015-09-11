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


DIRNAME=$(readlink -f ${BASH_SOURCE[0]})
DIRNAME=$(dirname $DIRNAME )
DIR_OM=$(dirname $DIRNAME )
FLD=$(dirname ${DIR_OM})/floodlight-0.90

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
om_list=""
#om_action="start"  #uncoment to get a default action
for param in $*
do
    [ "$param" == "start" -o "$param" == "stop"  -o "$param" == "restart" -o "$param" == "status" ] && om_action=$param  && continue
    [ "$param" == "openvim" -o "$param" == "vim"  ]    && om_list="$om_list vim"              && continue
    [ "$param" == "openmano" -o "$param" == "mano" ]   && om_list="$om_list mano"             && continue
    [ "$param" == "openflow" -o "$param" == "flow" -o "$param" == "floodlight" ] && om_list="flow $om_list" && continue
    [ "$param" == "-h" -o "$param" == "--help" ] && usage && exit 0
    #note flow that it must be the first element, because openvim relay on this
    
    #if none of above, reach this line because a param is incorrect
    echo "Unknown param '$param'" >&2
    usage >&2
    exit -1
done

#check action is provided
[ -z "$om_action" ] && usage >&2 && exit -1

#if no componenets supplied assume all
[ -z "$om_list" ] && om_list="flow vim mano"
 
for om_component in $om_list
do
    [ "${om_component}" == "flow" ] && om_cmd="floodlight.jar" && om_name="floodlight" && om_dir=$FLD
    [ "${om_component}" == "vim" ]  && om_cmd="openvimd.py"    && om_name="openvim   " && om_dir=$(readlink -f ${DIR_OM}/openvim)
    [ "${om_component}" == "mano" ] && om_cmd="openmanod.py"   && om_name="openmano  " && om_dir=$(readlink -f ${DIR_OM}/openmano)
    #obtain PID of program
    component_id=`ps -o pid,cmd -U $USER -u $USER | grep -v grep | grep ${om_cmd} | awk '{print $1}'`

    #status
    if [ "$om_action" == "status" ]
    then
        [ -n "$component_id" ] && echo "    $om_name running, pid $component_id"
        [ -z "$component_id" ] && echo "    $om_name stopped"
    fi

    #stop
    if [ "$om_action" == "stop" -o "$om_action" == "restart" ]
    then
        #terminates program
        [ -n "$component_id" ] && echo -n "    stopping $om_name ... " && kill_pid $component_id 
        component_id=""
        #terminates screen
        if screen -wipe | grep -Fq .$om_component
        then
            screen -S $om_component -p 0 -X stuff "exit\n"
            sleep 1
        fi
    fi

    #start
    if [ "$om_action" == "start" -o "$om_action" == "restart" ]
    then
        #calculates log file name
        logfile=""
        mkdir -p $DIR_OM/logs && logfile=$DIR_OM/logs/open${om_component} || echo "can not create logs directory  $DIR_OM/logs"
        #check already running
        [ -n "$component_id" ] && echo "    $om_name is already running. Skipping" && continue
        #create screen if not created
        echo -n "    starting $om_name ... "
        if ! screen -wipe | grep -Fq .${om_component}
        then
            pushd ${om_dir} > /dev/null
            screen -dmS ${om_component}  bash
            sleep 1
            popd > /dev/null
        else
            echo -n " using existing screen '${om_component}' ... "
            screen -S ${om_component} -p 0 -X log off
            screen -S ${om_component} -p 0 -X stuff "cd ${om_dir}\n"
            sleep 1
        fi
        #move old log file index one number up and log again in index 0
        if [[ -n $logfile ]]
        then
            for index in 8 7 6 5 4 3 2 1 0
            do
                [[ -f ${logfile}.${index} ]] && mv ${logfile}.${index} ${logfile}.$((index+1))
            done
            screen -S ${om_component} -p 0 -X logfile ${logfile}.0
            screen -S ${om_component} -p 0 -X log on
        fi
        #launch command to screen
        #[ "${om_component}" != "flow" ] && screen -S ${om_component} -p 0 -X stuff "cd ${DIR_OM}/open${om_component}\n" && sleep 1
        [ "${om_component}" == "flow" ] && screen -S flow -p 0 -X stuff "java  -Dlogback.configurationFile=${DIRNAME}/flow-logback.xml -jar ./target/floodlight.jar -cf ${DIRNAME}/flow.properties\n" && sleep 5
        [ "${om_component}" != "flow" ] && screen -S ${om_component} -p 0 -X stuff "./${om_cmd}\n"
        #check if is running
        [[ -n $logfile ]] && timeout=120 #2 minute
        [[ -z $logfile ]] && timeout=20
        while [[ $timeout -gt 0 ]]
        do
           #check if is running
           #echo timeout $timeout
           #if !  ps -f -U $USER -u $USER | grep -v grep | grep -q ${om_cmd}
           component_id=`ps -o pid,cmd -U $USER -u $USER | grep -v grep | grep ${om_cmd} | awk '{print $1}'`
           if [[ -z $component_id ]]
           then
               echo -n "ERROR, it has exited."
               break
           fi
           [[ -n $logfile ]] && [[ ${om_component} == flow ]] && grep -q "Listening for switch connections" ${logfile}.0 && sleep 1 && break
           [[ -n $logfile ]] && [[ ${om_component} != flow ]] && grep -q "open${om_component}d ready" ${logfile}.0 && break
           sleep 1
           timeout=$((timeout -1))
        done
        if [[ -n $logfile ]] && [[ $timeout == 0 ]] 
        then 
           echo -n "timeout!"
        else
           echo -n "running on 'screen -x ${om_component}'."
        fi
        [[ -n $logfile ]] && echo "  Logging at '${logfile}.0'" || echo
    fi
done





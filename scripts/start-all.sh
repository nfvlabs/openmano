#!/bin/bash

DIRNAME=`dirname $0`

#launch openmano and openvim
$DIRNAME/start-openvim.sh
sleep 1
$DIRNAME/start-openmano.sh






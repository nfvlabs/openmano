#!/bin/bash

DIRNAME=`dirname $0`

#launch openvim inside a screen
screen -dmS vim  bash
sleep 1
screen -S vim -p 0 -X stuff "cd $DIRNAME\n"
sleep 1
screen -S vim -p 0 -X stuff "./openvimd.py\n"

echo "openvim running. Execute 'screen -x vim' and 'Ctrl+c' to terminte"






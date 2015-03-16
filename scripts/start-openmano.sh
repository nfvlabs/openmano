#!/bin/bash

DIRNAME=`dirname $0`

#launch openmano inside a screen
screen -dmS mano  bash
sleep 1
screen -S mano -p 0 -X stuff "cd $DIRNAME\n"
sleep 1
screen -S mano -p 0 -X stuff "./openmanod.py\n"

echo "openmano running. Execute 'screen -x mano' and 'Ctrl+c' to terminte"





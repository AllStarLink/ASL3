#!/usr/bin/env bash

# N4IRS 07/26/2017
# WD6AWP 09/09/2020

#################################################
#                                               #
#                                               #
#                                               #
#################################################

systemctl is-active --quiet asl-asterisk.service
err=$?
if [ $err -eq 0 ]; then
   echo "Asterisk is currently running!"
else
   echo "Starting asterisk..."
   echo "systemctl start asl-asterisk.service"
   systemctl start asl-asterisk.service
fi

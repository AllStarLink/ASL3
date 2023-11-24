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
	echo "Restarting Asterisk"
    echo "systemctl restart asl-asterisk.service"
	systemctl restart asl-asterisk.service
else
	echo "Asterisk is not running!"
fi

#!/usr/bin/env bash

# N4IRS 07/26/2017
# WD6AWP 09/09/2020
# KK9ROB 03/03/2021

#################################################
#                                               #
#                                               #
#                                               #
#################################################

systemctl is-active --quiet asterisk.service
err=$?
if [ $err -eq 0 ]; then
	echo "Stopping Asterisk..."
    echo "systemctl stop asterisk.service"
	systemctl stop asterisk.service

else
	echo "Asterisk is not running!"
fi

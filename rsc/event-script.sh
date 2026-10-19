#!/bin/sh

##################################################################### 
# rsc/event-script.sh                                               #
#                                                                   #
# Called by hostapd_cli whenever it receives events from hostapd.   #
# Forwards those events to the AP host daemon's EventScriptCallback #
# method.                                                           #
##################################################################### 

INTERFACE="$1"
EVENT="$2"
MAC_ADDR="${3:-}"

dbus-send --system \
    --dest=com.aphostd.APHost \
    /com/aphostd/APHost \
    com.aphostd.APHost.EventScriptCallback \
    string:"$INTERFACE" string:"$EVENT" string:"$MAC_ADDR"

"""
lib/api.py

Contains the DBus interface
"""

import os
import sys
import logging
import configparser
from pydbus import SystemBus
from pydbus.generic import signal
from gi.repository import GLib
from . import (
    datatypes,
    exceptions
)

BUS_NAME = "com.aphostd.APHost"
OBJECT_PATH = "/com/aphostd/APHost"
INTERFACE_XML = """
<node>
    <interface name="com.aphostd.APHost">
        <!-- Methods -->
        <method name="Start"/>
        <method name="Stop"/>
        <method name="Restart"/>
        <method name="ApplyConfiguration"/>
        <method name="BlockStation">
            <arg type="s" name="mac_addr" direction="in"/>
        </method>
        <method name="UnblockStation">
            <arg type="s" name="mac_addr" direction="in"/>
        </method>
        <method name="EventScriptCallback">
            <arg type="s" name="interface" direction="in"/>
            <arg type="s" name="payload" direction="in"/>
        </method>

        <!-- Properties -->
        <!-- Read Only -->
        <property name="State" type="s" access="read"/>
        <property name="Stations" type="as" access="read"/>
        <property name="ConnectedStations" type="as" access="read"/>
        <property name="DisconnectedStations" type="as" access="read"/>
        <property name="Blocklist" type="as" access="read"/>
        <!-- Read/Write -->
        <property name="SSID" type="s" access="readwrite"/>
        <property name="Band" type="s" access="readwrite"/>
        <property name="Channel" type="i" access="readwrite"/>
        <property name="Security" type="s" access="readwrite"/>
        <property name="Passphrase" type="s" access="readwrite"/>
        <property name="Hidden" type="b" access="readwrite"/>

        <!-- Signals -->
        <signal name="StateChanged">
            <arg type="s" name="old_state"/>
            <arg type="s" name="new_state"/>
        </signal>
        <signal name="ConfigurationChanged">
            <arg type="s" name="property"/>
            <arg type="s" name="old_value"/>
            <arg type="s" name="new_value"/>
        </signal>
        <signal name="ConfigurationApplied">
            <arg type="a{sv}" name="old_configuration"/>
            <arg type="a{sv}" name="new_configuration"/>
        </signal>
        <signal name="StationEvent">
            <arg type="s" name="event_type"/>
            <arg type="s" name="mac_addr"/>
        </signal>
        <signal name="SubsystemEvent">
            <arg type="s" name="event_type"/>
        </signal>
    </interface>
</node>
"""

def dict_to_dbus_asv(d):
    """ Sanatizes a dictionary for use as an array of string variants in DBus
    """
    for k in d.keys():
        s = str(d[k])
        d[k] = s
    return d

class APHostService(datatypes.APHost):
    """ DBus interface object
    """

    # Signals
    StateChanged = signal()
    ConfigurationChanged = signal()
    ConfigurationApplied = signal()
    StationEvent = signal()
    SubsystemEvent = signal()

    def __init__(self):
        self.version = "0.1"
        config = configparser.ConfigParser()
        config.read(sys.argv[1:])
        logger = logging.getLogger()
        super().__init__(config=config, logger=logger)

    # Methods
    def Start(self):
        """ Start endpoint
        """
        self.logger.info(f"DBus API got call to Start")
        try:
            _old = self.state
            self._Start()
            self.StateChanged(_old, self.state)
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception during call to Start: {err_msg}")
            raise exceptions.StateChangeError(f"An error has prevented the AP host from starting") from err_msg
        return None

    def Stop(self):
        """ Stop endpoint
        """
        self.logger.info(f"DBus API got call to Stop")
        try:
            _old = self.state
            self._Stop()
            self.StateChanged(_old, self.state)
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception during call to Stop: {err_msg}")
            raise exceptions.StateChangeError(f"An error has prevented the AP host from stopping") from err_msg
        return None

    def Restart(self):
        """ Restart endpoint
        """
        self.logger.info(f"DBus API got call to Restart")
        try:
            _old = self.state
            self._Restart()
            self.StateChanged(_old, self.state)
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception during call to Restart: {err_msg}")
            raise exceptions.StateChangeError(f"An error has prevented the AP host from restarting") from err_msg
        return None

    def ApplyConfiguration(self):
        """ Apply endpoint
        """
        self.logger.info(f"DBus API got call to ApplyConfiguration")
        try:
            _old = dict_to_dbus_asv(self.settings)
            self._ApplyConfiguration()
            self.ConfigurationApplied(_old, dict_to_dbus_asv(self.settings))
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception during call to ApplyConfiguration: {err_msg}")
            raise exceptions.ConfigurationError(f"An error has occurred while applying the new configuration settings") from err_msg
        return None

    def BlockStation(self, mac_addr):
        """ Block a station
        """
        self.logger.info(f"DBus API got call to BlockStation with arguments: {mac_addr}")
        try:
            self._BlockStation(mac_addr)
            self.StationEvent("station-blocked", mac_addr)
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception during call to BlockStation: {err_msg}")
            raise exceptions.AccessControlError(f"Encountered an error while blocking station with MAC address {mac_addr}") from err_msg

    def UnblockStation(self, mac_addr):
        """ Unblock a station
        """
        self.logger.info(f"DBus API got call to UnblockStation with arguments: {mac_addr}")
        try:
            self._UnblockStation(mac_addr)
            self.StationEvent("station-unblocked", mac_addr)
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception during call to UnblockStation: {err_msg}")
            raise exceptions.AccessControlError(f"Encountered an error while unblocking station with MAC address {mac_addr}") from err_msg

    def EventScriptCallback(self, interface, event, mac_addr):
        """ Callback method for receiving hostapd events from hostapd_cli via the
        event script
        """
        self.logger.info(f"DBus API got call to EventScriptPipe with arguments: {interface}, {event}, {mac_addr}")
        try:
            is_noteworthy, event_info = self._EventScriptCallback(interface, event, mac_addr)
            if is_noteworthy:
                if event_info[0] in (
                    "new-station-connected",
                    "known-station-connected",
                    "new-station-disconnected",
                    "known-station-disconnected"
                ):
                    self.StationEvent(event_info[0], event_info[1])
                elif event_info[0] in (
                    "hostapd-reloaded"
                ):
                    self.SubsystemEvent(event_info[0])
                    
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception during call to EventScriptCallback: {err_msg}")
            raise exceptions.EventScriptError(f"The event script callback method has encountered an error") from err_msg
        return None
        

    # Properties
    # Read Only
    @property
    def State(self):
        return self.state

    @property
    def Stations(self):
        return self.stations

    @property
    def ConnectedStations(self):
        return self.connected_stations

    @property
    def DisconnectedStations(self):
        return self.disconnected_stations

    @property
    def Blocklist(self):
        return self.blocklist

    # Read/Write
    @property
    def SSID(self):
        return self.settings["SSID"]
    @SSID.setter
    def SSID(self, value):
        self.logger.info(f"Readwrite property SSID set to {value} from {self._settings["SSID"]}")
        _old = self._settings["SSID"]
        try:
            self._settings["SSID"] = value
            self.ConfigurationChanged("SSID", _old, self._settings["SSID"])
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception while setting value of readwrite property SSID from: {_old} to: {value}")

    @property
    def Band(self):
        return self.settings["Band"]
    @Band.setter
    def Band(self, value):
        self.logger.info(f"Readwrite property Band set to {value} from {self._settings["Band"]}")
        _old = self._settings["Band"]
        try:
            self._settings["Band"] = value
            self.ConfigurationChanged("Band", _old, self._settings["Band"])
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception while setting value of readwrite property Band from: {_old} to: {value}")

    @property
    def Channel(self):
        return self.settings["Channel"]
    @Channel.setter
    def Channel(self, value):
        self.logger.info(f"Readwrite property Channel set to {value} from {self._settings["Channel"]}")
        _old = str(self._settings["Channel"])
        try:
            self._settings["Channel"] = int(value)
            self.ConfigurationChanged("Channel", _old, str(self._settings["Channel"]))
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception while setting value of readwrite property Channel from: {_old} to: {value}")

    @property
    def Security(self):
        return self.settings["Security"]
    @Security.setter
    def Security(self, value):
        self.logger.info(f"Readwrite property Security set to {value} from {self._settings["Security"]}")
        _old = self._settings["Security"]
        try:
            self._settings["Security"] = value
            self.ConfigurationChanged("Security", _old, self._settings["Security"])
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception while setting value of readwrite property Security from: {_old} to: {value}")

    @property
    def Passphrase(self):
        return self.settings["Passphrase"]
    @Passphrase.setter
    def Passphrase(self, value):
        self.logger.info(f"Readwrite property Passphrase set to {value} from {self._settings["Passphrase"]}")
        _old = self._settings["Passphrase"]
        try:
            self._settings["Passphrase"] = value
            self.ConfigurationChanged("Passphrase", _old, self._settings["Passphrase"])
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception while setting value of readwrite property Passphrase from: {_old} to: {value}")

    @property
    def Hidden(self):
        return self.settings["Hidden"]
    @Hidden.setter
    def Hidden(self, value):
        self.logger.info(f"Readwrite property Hidden set to {value} from {self._settings["Hidden"]}")
        _old = str(self._settings["Hidden"])
        try:
            self._settings["Hidden"] = value
            self.ConfigurationChanged("Hidden", _old, str(self._settings["Hidden"]))
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception while setting value of readwrite property Hidden from: {_old} to: {value}")


def init_dbus_api(name=BUS_NAME, path=OBJECT_PATH, xml=INTERFACE_XML, logger=None):
    """ Launch the DBus interface
    """
    if logger:
        logger.info(f"Bringing up DBus API. Interface: {name} Path: {path}")
    bus = SystemBus()
    bus.publish(name, (path, APHostService(), xml))
    GLib.MainLoop().run()
    return None

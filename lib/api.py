"""
lib/api.py

Contains the DBus interface
"""

import os
import sys
import subprocess
import threading
import logging
import configparser
from pydbus import SystemBus
from pydbus.generic import signal
from gi.repository import GLib
from . import datatypes
from . import exceptions

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

        <!-- Properties -->
        <!-- Read Only -->
        <property name="State" type="s" access="read"/>
        <property name="Stations" type="a" access="read"/>
        <!-- Read/Write -->
        <property name="SSID" type="s" access="readwrite"/>
        <property name="Band" type="s" access="readwrite"/>
        <property name="Channel" type="i" access="readwrite"/>
        <property name="Security" type="s" access="readwrite"/>
        <property name="Passphrase" type="s" access="readwrite"/>

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
            <arg type="s" name="type"/>
            <arg type="s" name="mac_addr"/>
        </signal>
    </interface>
</node>
"""

class APHostService(datatypes.Template):
    """ DBus interface object
    """

    # Signals
    StateChanged = signal()
    ConfigurationChanged = signal()
    ConfigurationApplied = signal()
    StationEvent = signal()

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
        return None

    def ApplyConfiguration(self):
        """ Apply endpoint
        """
        self.logger.info(f"DBus API got call to ApplyConfiguration")
        try:
            _old = self.settings
            self._ApplyConfiguration()
            self.ConfigurationApplied(_old, self.settings)
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception during call to ApplyConfiguration: {err_msg}")
        return None

    def BlockStation(self, mac_addr):
        """ Block a station
        """
        self.logger.info(f"DBus API got call to BlockStation with arguments: {mac_addr}")
        try:
            self._BlockStation(mac_addr)
            self.StationEvent("station_blocked", mac_addr)
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception during call to BlockStation: {err_msg}")

    def UnblockStation(self, mac_addr):
        """ Unblock a station
        """
        self.logger.info(f"DBus API got call to UnblockStation with arguments: {mac_addr}")
        try:
            self._UnblockStation(mac_addr)
            self.StationEvent("station_unblocked", mac_addr)
        except Exception as err_msg:
            self.logger.error(f"DBus API encountered an exception during call to UnblockStation: {err_msg}")

    # Properties
    # Read Only
    @property
    def State(self):
        return self.state

    @property
    def Stations(self):
        return self.stations

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
        _old = self._settings["Channel"]
        try:
            self._settings["Channel"] = int(value)
            self.ConfigurationChanged("Channel", _old, self._settings["Channel"])
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

def init_dbus_api(name=BUS_NAME, path=OBJECT_PATH, xml=INTERFACE_XML):
    """ Launch the DBus interface
    """
    bus = SystemBus()
    bus.publish(name, (path, TemplateService(), xml))
    GLib.MainLoop().run()
    return None

"""
lib/api.py

Contains the DBus API for the AP host
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

BUS_NAME = "com.aphost.APHost"
OBJECT_PATH = "/com/aphost/APHost"
INTERFACE_XML = """
<node>
    <interface name="com.aphost.APHost">
        <method name="Start"/>
        <method name="Stop"/>
        <method name="Restart"/>
        <method name="ApplyConfiguration"/>
        <method name="GetStation">
            <arg type="s" name="mac_address" direction="in"/>
            <arg type="a{sv}" name="station_data" direction="out"/>
        </method>
        <method name="BlockStation">
            <arg type="s" name="mac_address" direction="in"/>
        </method>
        <method name="UnblockStation">
            <arg type="s" name="mac_address" direction="in"/>
        </method>
        <method name="DeauthenticateStation">
            <arg type="s" name="mac_address" direction="in"/>
        </method>
        <property name="State" type="s" access="read"/>
        <property name="Stations" type="l" access="read"/>
        <property name="BlockedStations" type="l" access="read"/>
        <property name="ESSID" type="s" access="readwrite"/>
        <property name="Band" type="s" access="readwrite"/>
        <property name="Channel" type="s" access="readwrite"/>
        <property name="Security" type="s" access="readwrite"/>
        <property name="Passphrase" type="s" access="readwrite"/>
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
            <arg type="a{sv}" name="applied_config"/>
        </signal>
        <signal name="StationConnected">
            <arg type="s" name="mac_address"/>
        </signal>
        <signal name="StationDisconnected">
            <arg type="s" name="mac_address"/>
        </signal>
    </interface>
</node>
"""

class APHostService(datatypes.APHost):
    """ System-level DBus API service
    """
    # Signals
    StateChanged = signal()
    ConfigurationChanged = signal()
    ConfigurationApplied = signal()
    StationConnected = signal()
    StationDisconnected = signal()

    def __init__(self):
        """ Initialize the object
        """
        self.version = "0.1"
        config = configparser.ConfigParser()
        config.read(sys.argv[1])
        logger = logging.getLogger()
        super().__init__(config=config, logger=logger)
        self.station_table = datatypes.StationTable(config=config, logger=logger)
        self.station_monitoring_thread = threading.Thread(target=self.station_activity_monitor, daemon=True)
        self.station_monitoring_thread.start()

    ############################
    # EVENT MONITORS / HELPERS #
    ############################
    def station_activity_monitor(self):
        """ Monitor hostapd for station connections/disconnections
        """
        p = subprocess.Popen(
            ["hostapd_cli", "-i", self.config["AP"]["broadcast_iface"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in p.stdout:
            if "AP-STA-CONNECTED" in line:
                m = line.split()[-1]
                if not self.station_table.get_station(m):
                    s = self.station_table.new_station(m)
                else:
                    s = self.station_table.get_station(m)
                s.set_status("connected")
                self.StationConnected(m)

            elif "AP-STA-DISCONNECTED" in line:
                m = line.split()[-1]
                if not self.station_table.get_station(m):
                    s = self.station_table.new_station(m)
                else:
                    s = self.station_table.get_station(m)
                s.set_status("disconnected")
                self.StationDisconnected(m)

    ####################
    # DBUS API METHODS #
    ####################
    # Standard methods
    def Start(self):
        """ Start the AP host
        """
        self.logger.info(f"Got call on DBus API to Start")
        try:
            old_state = self.state
            self.start()
            self.StateChanged(old_state, self.state)
        except exceptions.StateChangeError as err_msg:
            self.logger.error(f"DBus API encoutered a StateChangeError handling call to Start! Error message:  {err_msg}")
        return None


    def Stop(self):
        """ Stop the AP host
        """
        self.logger.info(f"Got call on DBus API to Stop")
        try:
            old_state = self.state
            self.stop()
            self.StateChanged(old_state, self.state)
        except exceptions.StateChangeError as err_msg:
            self.logger.error(f"DBus API encoutered a StateChangeError handling call to Stop! Error message:  {err_msg}")
        return None

    def Restart(self):
        """ Restart the AP host
        """
        self.logger.info(f"Got call on DBus API to Restart")
        try:
            old_state = self.state
            self.restart()
            self.StateChanged(old_state, self.state)
        except exceptions.StateChangeError as err_msg:
            self.logger.error(f"DBus API encoutered a StateChangeError handling call to Restart! Error message:  {err_msg}")
        return None

    def ApplyConfiguration(self):
        """ Apply configuration changes from current property values
        """
        self.logger.info(f"Got call on DBus API to ApplyConfiguration")
        try:
            self.apply_configuration()
            GLib.idle_add(self.ConfigurationApplied, {
                "ESSID": self.essid,
                "Band": self.band,
                "Channel": self.channel,
                "Security": self.security,
                "Passphrase": self.passphrase
            })
        except exceptions.ConfigurationError as err_msg:
            self.logger.error(f"DBus API encoutered a ConfigurationError handling call to ApplyConfiguration! Error message: {err_msg}")
        return None

    # Component-specific methods
    def GetStation(self, mac_address):
        """ Return station data
        """
        self.logger.info(f"Got call on DBus API to GetStation (Arguments: {mac_address})")
        try:
            if not self.station_table.get_station(mac_address):
                self.logger.warning(f"Cannot do GetStation! No such station: {mac_address}")
                return {}
            station = self.station_table.get_station(mac_address)
            station.update_data()
            station_data = station.data
        except exceptions.StationError as err_msg:
            self.logger.error(f"DBus API encountered a StationError handling call to GetStation! Error message: {err_msg}")
        except exceptions.StationTableError as err_msg:
            self.logger.error(f"DBus API encountered a StationTableError handling call to GetStation! Error message: {err_msg}")
        return station_data

    def BlockStation(self, mac_address):
        """ Block a station from the network
        """
        self.logger.info(f"Got call on DBus API to BlockStation (Arguments: {mac_address})")
        try:
            if not self.station_table.get_station(mac_address):
                self.logger.warning(f"Cannot do GetStation! No such station: {mac_address}")
                return None
            station = self.station_table.get_station(mac_address)
            station.block()
        except exceptions.StationError as err_msg:
            self.logger.error(f"DBus API encountered a StationError handling call to BlockStation! Error message: {err_msg}")
        except exceptions.StationTableError as err_msg:
            self.logger.error(f"DBus API encountered a StationTableError handling call to BlockStation! Error message: {err_msg}")
        return None

    def UnblockStation(self, mac_address):
        """ Unblock a blocked station
        """
        self.logger.info(f"Got call on DBus API to UnblockStation (Arguments: {mac_address})")
        try:
            if not self.station_table.get_station(mac_address):
                self.logger.warning(f"Cannot do GetStation! No such station: {mac_address}")
                return None
            station = self.station_table.get_station(mac_address)
            station.unblock()
        except exceptions.StationError as err_msg:
            self.logger.error(f"DBus API encountered a StationError handling call to UnblockStation! Error message: {err_msg}")
        except exceptions.StationTableError as err_msg:
            self.logger.error(f"DBus API encountered a StationTableError handling call to UnblockStation! Error message: {err_msg}")
        return None

    def DeauthenticateStation(self, mac_address):
        """ Force a connected station to deauthenticate
        """
        self.logger.info(f"Got call on DBus API to DeauthenticateStation (Arguments: {mac_address})")
        try:
            if not self.station_table.get_station(mac_address):
                self.logger.warning(f"Cannot do GetStation! No such station: {mac_address}")
                return None
            station = self.station_table.get_station(mac_address)
            station.deauthenticate()
        except exceptions.StationError as err_msg:
            self.logger.error(f"DBus API encountered a StationError handling call to DeauthenticateStation! Error message: {err_msg}")
        except exceptions.StationTableError as err_msg:
            self.logger.error(f"DBus API encountered a StationTableError handling call to DeauthenticateStation! Error message: {err_msg}")
        return None

    #######################
    # DBUS API PROPERTIES #
    #######################
    @property
    def State(self):
        return self.state

    @property
    def Stations(self):
        return self.station_table.stations

    @property
    def BlockedStations(self):
        return self.station_table.blocked_stations

    @property
    def ESSID(self):
        return self.essid
    @ESSID.setter
    def ESSID(self, value):
        old_value = self.essid
        self._essid = value
        self.logger.info(f"Value of property ESSID changed from '{old_value}' to '{self._essid}'")
        self.ConfigurationChanged("ESSID", old_value, self._essid)

    @property
    def Band(self):
        return self.band
    @Band.setter
    def Band(self, value):
        old_value = self.band
        self._band = value
        self.logger.info(f"Value of property Band changed from '{old_value}' to '{self._band}'")
        self.ConfigurationChanged("Band", old_value, self._band)

    @property
    def Channel(self):
        return self.channel
    @Channel.setter
    def Channel(self, value):
        old_value = self.channel
        self._channel = value
        self.logger.info(f"Value of property Channel changed from '{old_value}' to '{self._channel}'")
        self.ConfigurationChanged("Channel", old_value, self._channel)

    @property
    def Security(self):
        return self.security
    @Security.setter
    def Security(self, value):
        old_value = self.security
        self._security = value
        self.logger.info(f"Value of property Security changed from '{old_value}' to '{self._security}'")
        self.ConfigurationChanged("Security", old_value, self._security)

    @property
    def Passphrase(self):
        return self.passphrase
    @Passphrase.setter
    def Passphrase(self, value):
        old_value = self.passphrase
        self._passphrase = value
        self.logger.info(f"Value of property Passphrase changed from '{old_value}' to '{self._passphrase}'")
        self.ConfigurationChanged("Passphrase", old_value, self._passphrase)

def init_dbus_api(name=BUS_NAME, path=OBJECT_PATH, xml=INTERFACE_XML):
    """ Start the DBus API
    """
    bus = SystemBus()
    bus.publish(name, (path, APHostService(), xml))
    GLib.MainLoop().run()
    return None


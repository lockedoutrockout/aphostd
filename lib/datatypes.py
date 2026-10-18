"""
lib/datatypes.py

Custom datatype definitions
"""

import os
import sys
import subprocess
from . import exceptions

class APHost(object):
    """ APHost backend
    """
    def __init__(self, config=None, logger=None):
        self.config = config
        self.logger = logger
        self.cmd = []
        self.process = None
        self.state = "not running"
        self.stations = []
        self.blocklist = []
        self.settings = self._settings = {
            "SSID": self.config["AP"]["ssid"],
            "Band": self.config["AP"]["band"],
            "Channel": int(self.config["AP"]["channel"]),
            "Security": self.config["AP"]["security"],
            "Passphrase": self.config["AP"]["passphrase"],
        }

    def _Start(self):
        """ Start the process
        """
        if self.state == "running":
            raise exceptions.StateChangeError(f"Process is already running")
        try:
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        except Exception as err_msg:
            raise err_msg
        self.state = "running"
        return None

    def _Stop(self):
        """ Stop the process
        """
        if self.state == "not running":
            raise exceptions.StateChangeError(f"Process is not running")
        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        except Exception as err_msg:
            raise err_msg
        self.state = "not running"
        return None

    def _Restart(self):
        """ Restart the process
        """
        if self.state == "not running":
            raise exceptions.StateChangeError(f"Process is not running")
        try:
            self._Stop()
            self._Start()
        except Exception as err_msg:
            raise err_msg
        return None

    def _ApplyConfiguration(self):
        """ Apply new configuration settings
        """
        self.settings = self._settings
        return None

    def _BlockStation(self, mac_addr):
        """ Block a station
        """
        pass

    def _UnblockStation(self, mac_addr):
        """ Unblock a station
        """
        pass

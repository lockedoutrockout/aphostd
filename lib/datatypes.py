"""
lib/datatypes.py

Custom datatype definitions
"""

import os
import sys
import subprocess
import threading
from . import (
    exceptions
)

class APHost(object):
    """ APHost backend
    """
    def __init__(self, config=None, logger=None):
        def _event_monitor(self):
            """ Event monitor thread
            """
            subprocess.call([
                "hostapd_cli",
                "-a",
                self.config["HOSTAPD"]["event_script"]
            ])
            return None
            
        self.config = config
        self.logger = logger
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
            "Hidden": bool(self.config["AP"]["hidden"])
        }
        threading.Thread(target=self._event_monitor, daemon=True).start()

    def _gen_hostapd_config(self, outfile):
        """ Generate the hostapd configuration file
        """
        settings = []
        hw_mode = "bg" if self.settings["Band"] == "2.4g" else "a"
        ignore_broadcast_ssid = 1 if self.settings["Hidden"] == True else 0
        for setting in [
            f"interface={self.config['HARDWARE']['interface']}",
            f"driver={self.config['HARDWARE']['driver']}",
            f"ssid={self.settings['SSID']}",
            f"hw_mode={hw_mode}",
            f"channel={str(self.settings['Channel'])}",
            f"ieee80211n=1",
            f"wmm_enabled=1",
            f"auth_algs=1",
            f"ignore_broadcast_ssid={ignore_broadcast_ssid}",
            f"ctrl_interface=/var/run/hostapd",
            f"ctrl_interface_group=0",
            f"macaddr_acl=1",
            f"deny_mac_file={self.config['HOSTAPD']['acl_file']}"
        ]:
            settings.append(setting)
        if self.settings["Security"] == "wpa2-psk":
            for setting in [
                f"wpa=2",
                f"wpa_key_mgmt=WPA-PSK",
                f"rsn_pairwise=CCMP",
                f"wpa_passphrase={self.settings['Passphrase']}"
            ]:
                settings.append(setting)
        elif self.settings["Security"] == "wpa2/wpa3":
            for setting in [
                f"ieee80211w=1",
                f"wpa=2",
                f"wpa_key_mgmt=WPA-PSK SAE",
                f"rsn_pairwise=CCMP",
                f"wpa_passphrase={self.settings['Passphrase']}"
            ]:
        elif self.settings["Security"] == "wpa3-personal":
            for setting in [
                f"ieee80211w=2",
                f"wpa=2",
                f"wpa_key_mgmt=SAE",
                f"rsn_pairwise=CCMP",
                f"sae_require_mfp=1",
                f"wpa_passphrase={self.settings['Passphrase']}"
            ]:
                settings.append(setting)

        with open(outfile, "w") as fd:
            for setting in settings:
                fd.write(setting + "\n")

        return None

    def _gen_acl_file(self, outfile):
        """ Generate the access control list
        """
        with open(outfile, "w") as fd:
            for station in self.blocklist:
                fd.write(station + "\n")
        return None

    def _reload_hostapd(self):
        """ Reload hostapd
        """
        subprocess.call([
            "hostapd_cli",
            "-i",
            self.config["HARDWARE"]["interface"],
            "reload"
        ])
        return None

    def _Start(self):
        """ Start the process
        """
        if self.state == "running":
            raise exceptions.StateChangeError(f"Process is already running")
        try:
            self._gen_hostapd_config(self.config["HOSTAPD"]["config_file"])
            self.process = subprocess.Popen(
                [
                    self.config["HOSTAPD"]["executable"],
                    self.config["HOSTAPD"]["config_file"]
                ],
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
        if mac_addr in self.blocklist:
            raise Exception(f"Station {mac_addr} is already in blocklist")
        try:
            self.blocklist.append(mac_addr)
            self._gen_acl_file(self.config["HOSTAPD"]["acl_file"])
            self._reload_hostapd()
        except Exception as err_msg:
            raise err_msg
        return None

    def _UnblockStation(self, mac_addr):
        """ Unblock a station
        """
        if mac_addr not in self.blocklist:
            raise Exception(f"Station {mac_addr} is not in blocklist")
        try:
            self.blocklist.remove(mac_addr)
            self._gen_acl_file(self.config["HOSTAPD"]["acl_file"])
            self._reload_hostapd()
        except Exception as err_msg:
            raise err_msg
        return None

    def _EventScriptCallback(self, event_type, mac_addr):
        """ Process hostapd events received through the event script
        """
        if 

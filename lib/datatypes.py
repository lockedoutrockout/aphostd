"""
lib/datatypes.py

Custom datatype definitions
"""

import os
import sys
import time
import logging
import subprocess
import threading
from . import (
    exceptions
)

class APHost(object):
    """ APHost backend
    """
    def __init__(self, config=None, logger=None):
        self.config = config
        self.logger = logger
        self.processes = {}
        self.state = "not running"
        self.stations = []
        self.connected_stations = []
        self.disconnected_stations = []
        self.blocklist = []
        self.settings = {
            "SSID": self.config["AP"]["ssid"],
            "Band": self.config["AP"]["band"],
            "Channel": self.config.getint("AP", "channel"),
            "Security": self.config["AP"]["security"],
            "Passphrase": self.config["AP"]["passphrase"],
            "Hidden": self.config.getboolean("AP", "hidden")
        }
        self._settings = {
            "SSID": self.config["AP"]["ssid"],
            "Band": self.config["AP"]["band"],
            "Channel": self.config.getint("AP", "channel"),
            "Security": self.config["AP"]["security"],
            "Passphrase": self.config["AP"]["passphrase"],
            "Hidden": self.config.getboolean("AP", "hidden")
        }
        
        if not os.path.isfile(self.config["HOSTAPD"]["acl_file"]):
            with open(self.config["HOSTAPD"]["acl_file"], "w"):
                pass
            

    def _gen_hostapd_config(self, outfile):
        """ Generate the hostapd configuration file
        """
        settings = []
        hw_mode = "g" if self.settings["Band"] == "2.4g" else "a"
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
            f"macaddr_acl=0",
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
                settings.append(setting)
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
        p = subprocess.Popen([
            "hostapd_cli",
            "-p",
            "/var/run/hostapd",
            "-i",
            self.config["HARDWARE"]["interface"],
            "reload"
        ])
        retcode = p.wait()
        if retcode != 0:
            raise exceptions.SyscallNonZeroRetcodeError(f"Call to hostapd_cli to reload hostapd returned non-zero retcode: {retcode}")
        return None

    def _Start(self):
        """ Start the process
        """
        def _hostapd_runner(logger, config):
            """ Runner thread for hostapd
            """
            logger.info(f"Started hostapd runner thread")
            sublogger = logging.getLogger("hostapd_runner")
            slch = logging.StreamHandler()
            log_level = int(config["LOGGING"]["log_level"])
            if log_level == -1:
                log_level = logging.DEBUG
            elif log_level == 0:
                log_level = logging.INFO
            elif log_level == 1:
                log_level = logging.ERROR
            slch.setLevel(log_level)
            slch.setFormatter(logging.Formatter("%(name)s - %(message)s"))
            sublogger.addHandler(slch)
            sublogger.info(f"Sublogger initialized for hostapd subprocess")
            p = subprocess.Popen(
                [
                    self.config["HOSTAPD"]["executable"],
                    "-d",
                    self.config["HOSTAPD"]["config_file"]
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            self.processes["hostapd"] = p
            for line in p.stdout:
                sublogger.info(line.rstrip())
            retcode = p.wait()
            if retcode != 0:
                logger.error(f"The hostapd subprocess has exited with a non-zero return code of: {retcode}")
            else:
                logger.info(f"The hostapd subprocess has exited")
            return None
            
        def _hostapd_cli_runner(logger, config):
            """ Runner thread for hostapd_cli
            """
            logger.info(f"Started hostapd_cli runner thread")
            sublogger = logging.getLogger("hostapd_cli_runner")
            slch = logging.StreamHandler()
            log_level = int(config["LOGGING"]["log_level"])
            if log_level == -1:
                log_level = logging.DEBUG
            elif log_level == 0:
                log_level = logging.INFO
            elif log_level == 1:
                log_level = logging.ERROR
            slch.setLevel(log_level)
            slch.setFormatter(logging.Formatter("%(name)s - %(message)s"))
            sublogger.addHandler(slch)
            sublogger.info(f"Sublogger initialized for hostapd_cli subprocess")
            p = subprocess.Popen(
                [
                    "hostapd_cli",
                    "-p",
                    "/var/run/hostapd",
                    "-i",
                    config["HARDWARE"]["interface"],
                    "-a",
                    config["HOSTAPD"]["event_script"]
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            self.processes["hostapd_cli"] = p
            for line in p.stdout:
                sublogger.info(line.rstrip())
            retcode = p.wait()
            if retcode != 0:
                logger.error(f"The hostapd_cli subprocess has exited with a non-zero return code of: {retcode}")
            else:
                logger.info(f"The hostapd_cli subprocess has exited")
            return None
        
        if self.state == "running":
            raise exceptions.StateChangeError(f"AP host is already running")
        try:
            self.state = "starting"
            self._gen_hostapd_config(self.config["HOSTAPD"]["config_file"])
            threading.Thread(target=_hostapd_runner, args=(self.logger, self.config), daemon=True).start()
            time.sleep(0.5)
            if self.processes["hostapd"].returncode:
                raise exceptions.ChildProcessExitedError(f"hostapd exited with return code of: {self.processes['hostapd'].returncode}")
            threading.Thread(target=_hostapd_cli_runner, args=(self.logger, self.config), daemon=True).start()
            time.sleep(0.5)
            if self.processes["hostapd_cli"].returncode:
                raise exceptions.ChildProcessExitedError(f"hostapd_cli exited prematurely with return code of: {self.processes['hostapd_cli'].returncode}")
        except Exception as err_msg:
            raise err_msg
        self.state = "running"
        return None

    def _Stop(self):
        """ Stop the process
        """
        if self.state == "not running":
            raise exceptions.StateChangeError(f"AP host is not running")
        try:
            for process_name in self.processes.keys():
                self.logger.debug(f"Stopping subprocess: {process_name}")
                process = self.processes[process_name]
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                self.processes[process_name] = None
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
        try:
            self._gen_hostapd_config(self.config["HOSTAPD"]["config_file"])
            self._reload_hostapd()
        except Exception as err_msg:
            raise err_msg
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

    def _EventScriptCallback(self, interface, event, mac_addr):
        """ Process hostapd events received through the event script
        """
        if event == "AP-STA-CONNECTED":
            if mac_addr not in self.stations:
                self.stations.append(mac_addr)
                return (True, ("new-station-connected", mac_addr))
            else:
                return (True, ("known-station-connected", mac_addr))
            if mac_addr in self.disconnected_stations:
                self.disconnected_stations.remove(mac_addr)
            if mac_addr not in self.connected_stations:
                self.connected_stations.append(mac_addr)
        elif event == "AP-STA-DISCONNECTED":
            if mac_addr not in self.stations:
                self.stations.append(mac_addr)
                return (True, ("new-station-disconnected", mac_addr))
            else:
                return (True, ("known-station-disconnected", mac_addr))
            if mac_addr in self.connected_stations:
                self.connected_stations.remove(mac_addr)
            if mac_addr not in self.disconnected_stations:
                self.disconnected_stations.append(mac_addr)
        elif event == "SIGHUP":
            return (True, ("hostapd-reloaded", None))
        else:
            return (False, (None, None))

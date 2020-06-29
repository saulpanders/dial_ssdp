# dial_fingerprint.py
# @saulpanders
# Last update: 6/28/20

#inspired by https://github.com/crquan/work-on-sony-apis/blob/master/search-nex.py
#http://www.dial-multiscreen.org/dial-protocol-specification 

import sys
import socket
import argparse
import requests
import json
from bs4 import BeautifulSoup
import lxml

#app list (global variable)
#gets updated each time apps are enumerated
g_apps = []

## DIAL DEVICE
'''
    {
            "SSDP-Headers": {
            "CACHE-CONTROL": "max-age=1800",
            "DATE": "Mon, 29 Jun 2020 01:22:17 GMT",
            "EXT": "",
            "LOCATION": "http://192.168.1.10:8008/ssdp/device-desc.xml",
            "OPT": "\"http://schemas.upnp.org/upnp/1/0/\"; ns=01",
            "01-NLS": "c36d74b8-1dd1-11b2-9f5a-f65670c123f7",
            "SERVER": "Linux/3.18.25, UPnP/1.0, Portable SDK for UPnP devices/1.6.18",
            "X-User-Agent": "redsonic",
            "ST": "urn:dial-multiscreen-org:service:dial:1",
            "USN": "uuid:2260d814-7c75-20f1-1ff1-4b95955ad3cc::urn:dial-multiscreen-org:service:dial:1",
            "BOOTID.UPNP.ORG": "0",
            "CONFIGID.UPNP.ORG": "4"
        },
        "Device-Description": "<?xml version=\"1.0\"?><html><body><root xmlns=\"urn:schemas-upnp-org:device-1-0\">\n<specversion>\n<major>1</major>\n<minor>0</minor>\n</specversion>\n<urlbase>http://192.168.1.10:8008</urlbase>\n<device>\n<devicetype>urn:dial-multiscreen-org:device:dial:1</devicetype>\n<friendlyname>Family Room TV</friendlyname>\n<manufacturer>Vizio</manufacturer>\n<modelname>V405-G9</modelname>\n<udn>uuid:2260d814-7c75-20f1-1ff1-4b95955ad3cc</udn>\n<iconlist>\n<icon>\n<mimetype>image/png</mimetype>\n<width>98</width>\n<height>55</height>\n<depth>32</depth>\n<url>/setup/icon.png</url>\n</icon>\n</iconlist>\n<servicelist>\n<service>\n<servicetype>urn:dial-multiscreen-org:service:dial:1</servicetype>\n<serviceid>urn:dial-multiscreen-org:serviceId:dial</serviceid>\n<controlurl>/ssdp/notfound</controlurl>\n<eventsuburl>/ssdp/notfound</eventsuburl>\n<scpdurl>/ssdp/notfound</scpdurl>\n</service>\n</servicelist>\n</device>\n</root>\n</body></html>",
        "UUID": "2260d814-7c75-20f1-1ff1-4b95955ad3cc",
        "Location": "http://192.168.1.10:8008/ssdp/device-desc.xml",
        "ST": "urn:dial-multiscreen-org:service:dial:1",
        "Friendly-Name": null,
        "Application-URL": "http://192.168.1.10:8008/apps/",
        "Apps": {
            "PlayMovies": "http://192.168.1.10:8008/apps/PlayMovies"
        }
    }
'''

class DIAL_device:
    def __init__(self):

        #dict of key info from initial SSDP discovery request
        self.discovery_headers = None

        #parsed device description XML document as a string
        self.device_description = None

        ##special values
        #unique ID for device (DIAL protocol, useful to keep seperate for ID)
        self.uuid = None

        #location of device description XML file 
        self.location= None

        self.ST = None

        #from device description (if it exists)
        self.friendly_name = None

        #URL for interacting with apps
        self.apps_url = None
        #DIAL apps discovered stored as App Name/App URL key-value pairs
        self.apps_enabled = {}


    def set_headers(self, headers):
        self.discovery_headers = headers
        self.ST = headers['ST']
        self.location = headers['LOCATION']
        self.uuid = headers['USN'].split(":")[1]

    #pulls device description file 
    def get_device_description(self):
        if self.location:
            try:
                dd_request = requests.get(self.location)
                soup = BeautifulSoup(dd_request.text, "lxml")
                self.apps_url = dd_request.headers['Application-URL']
                self.device_description = str(soup)

                #set some important values aside
                self.friendly_name = soup.find("friendlyName")
            except:
                raise

        else:
            print("[-] Error: device needs location set")

    # Serializes as JSON outputting device info to a file
    def parse_to_json(self):
        obj = {}
        obj["SSDP-Headers"] = self.discovery_headers
        obj["Device-Description"] = self.device_description
        obj["UUID"] = self.uuid
        obj["Location"] = self.location
        obj["ST"] = self.ST
        obj["Friendly-Name"] = self.friendly_name
        obj["Application-URL"] = self.apps_url
        obj["Apps"] = self.apps_enabled
        return obj




### GLOBAL FUNCTIONS / HELPERS ========================================================

#TODO add arguments for SSDP
# i.e. setting SSDP_ST to other strings would allow for other SSDP-discoverable devices
def discover_devices():

    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    SSDP_MX = 1
    SSDP_ST = "urn:dial-multiscreen-org:service:dial:1"
    device_list = []

    ssdpRequest = "M-SEARCH * HTTP/1.1\r\n" + \
        "HOST: %s:%d\r\n" % (SSDP_ADDR, SSDP_PORT) + \
                "MAN: \"ssdp:discover\"\r\n" + \
                "MX: %d\r\n" % (SSDP_MX, ) + \
                "ST: %s\r\n" % (SSDP_ST, ) + "\r\n"

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(ssdpRequest.encode('utf-8'), (SSDP_ADDR, SSDP_PORT))
    sock.settimeout(10)

    while True:
        try:
            data = sock.recv(1024)
            parse = data.decode('utf-8').split('\r\n')
            if parse[0].find("200 OK"):
               device_list.append(parse_discovery(parse))
        except:
            break

    return device_list

#utility function for discover_devices()
#takes in decoded bytes from SSDP request socket, returns dictionary of header, response values
def parse_discovery(data):
    print("[+] parsing SSDP response...")
    headers = list(filter(None, [x.split(":")[0] for x in data]))[1:]
    values = [':'.join(x.split(":")[1:]).lstrip(' ') for x in data ][1:-2]
    parsed_data = dict(zip(headers, values))
    return parsed_data


#enumerates available apps from discoverable device using the app location header
def enum_apps(device):
    print("[+] enumerating apps...")
    device_app_url = device.apps_url
    for app in g_apps:
        try:
            u = requests.get("%s%s" % (device_app_url, app))
            if u.status_code != 404:
                print("[+] %s:%s" % (app, repr(str(u.headers) + str(u.content))))
                device.apps_enabled[app] = device_app_url + app
        except:
            raise
            pass

#dynamically updates app list from DIAL website -- still needs work (BUT CURRENTLY WORKS)
def update_app_list():
    r = requests.get("http://www.dial-multiscreen.org/dial-registry/namespace-database")
    soup = BeautifulSoup(r.text, features='html.parser')

    #grab google doc embedded IFRAME
    embedded_sheet = soup.find("iframe", {"title": "DIAL Namespace Registration ‎‎‎‎(Public)‎‎‎‎"})
    
    #strip widget from source
    s = embedded_sheet.attrs['src']
    if "&widget=true" in s:
        s = s[:-12]
    r2 = requests.get(s)

    soup2 = BeautifulSoup(r2.text, features='html.parser')
    app_list = list(filter(None, [x.string for x in soup2.findAll("td",{"class": "s2"})]))
    for x in app_list:
        #add app to global applist
        g_apps.append(x) if x not in g_apps else g_apps

    print("[+] updated app listing from registry (%s)" % s)


#write device info to file
def export_device(device):
    print("[+] Exporting device %s to .json.." % device.uuid)
    with open(device.uuid+'.json', 'w') as f:
        json.dump(device.parse_to_json(), f)

 #=================================================================================================

#Actual Main Code
def main():



    devices = discover_devices()
    d = DIAL_device()
    d.set_headers(devices[0])
    d.get_device_description()
    print(d.apps_url)

    print("Enumerating apps on device: ", d.uuid)
    update_app_list()
    enum_apps(d)

    print(d.apps_enabled)

    export_device(d)

main()
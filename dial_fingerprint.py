# dial_fingerprint.py
# @saulpanders
# Last update: 4/26/20

#inspired by https://github.com/crquan/work-on-sony-apis/blob/master/search-nex.py
#http://www.dial-multiscreen.org/dial-protocol-specification 

import sys
import socket
import argparse
import requests
from bs4 import BeautifulSoup

g_apps = []

## DIAL DEVICE
'''
    USN
    SSID
    WAKEUP INFO (if present)
    LOCATION
    OTHER HTTP HEADERS?
'''

class DIAL_device:
    def __init__(self):

        #dict of key info from initial SSDP discovery request
        self.discovery_headers = None

        #parsed device description XML document
        self.device_description = None

        ##special values
        #unique ID for device (DIAL protocol, useful to keep seperate for ID)
        self.uuid = None
        self.location= None
        self.ST = None

        #for interacting with apps
        self.apps_url = None
        self.apps_enabled = []

    def set_headers(self, headers):
        self.discovery_headers = headers
        self.ST = headers['ST']
        self.location = headers['LOCATION']
        self.uuid = headers['USN'].split(":")[1]

    def get_device_description():
        print("todo")


### GLOBAL FUNCTIONS / HELPERS ========================================================

#TODO add arguments for SSDP
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
    sock.settimeout(5)

    while True:
        try:
            data = sock.recv(1024)
            parse = data.decode('utf-8').split('\r\n')
            if parse[0].find("200 OK"):
               device_list.append(parse_discovery(parse))
        except:
            break

    return device_list


#takes in decoded bytes from SSDP request socket, returns dictionary of header, response values
def parse_discovery(data):
    print("parsing...")
    headers = list(filter(None, [x.split(":")[0] for x in data]))[1:]
    values = [':'.join(x.split(":")[1:]).lstrip(' ') for x in data ][1:-2]
    parsed_data = dict(zip(headers, values))
    return parsed_data


#enumerates available apps from discoverable device using the app location header
def enum_apps(device_app_url):
    for app in g_apps:
        try:
            u = requests.get("%s/%s" % (device_app_url, app))
            if u.status_code != 404:
                print(u.status_code)
                print("++++++++++++++++++++++")
                print("%s:%s" % (app, repr(str(u.headers) + str(u.content))))
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

    print(s)
    r2 = requests.get(s)

    soup2 = BeautifulSoup(r2.text, features='html.parser')
    app_list = list(filter(None, [x.string for x in soup2.findAll("td",{"class": "s2"})]))
    for x in app_list:
        g_apps.append(x)

    print("[+] updated app listing from registry")

 #=================================================================================================

#Actual Main Code
devices = discover_devices()
#print(devices)
d = DIAL_device()
d.set_headers(devices[0])




update_app_list()


#x = "http://192.168.1.11:8008/apps"

enum_apps(x) 




#main()
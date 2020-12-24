#!/usr/bin/env python3

import os
import json
import paho.mqtt.client as mqtt
import time
import threading
import logging
from datetime import datetime

logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s: %(message)s')

# -----------------------------
# --- CONFIGURATION OPTIONS ---
# -----------------------------

discoveryTopicPrefix = 'homeassistant/sensor/'
topicPrefix = 'home/nodes/vpnclients/'              # suffix (state /state, attributes /attr, availability /status)
vpnType = 'WireGuard'                               # WireGuard or OpenVPN or other?
mqttUser = 'USERNAME'
mqttPassword = 'PASSWORD'
mqttAddress = 'IP.ADDRESS'                          # assumes standard ports
updateFrequency = 5                                 # in minutes

# ---------------------------------
# --- END CONFIGURATION OPTIONS ---
# ---------------------------------


# MQTT Connection Made
def on_connect(client, userdata, flags, rc):
    logging.debug('--> on_connect')
    logging.info('Connected with result code '+str(rc))
    stateTopic = '{}status'.format(topicPrefix)     # publish status update
    client.publish(stateTopic, payload='Online', qos=0, retain=True) 
    for device in deviceList:                       # call discovery for each device
        publishDiscovery(device)

# Timer based on update frequency
def periodTimeoutHandler():
    global deviceList
    logging.info('Timer interrupt')
    updatedDeviceList = getDeviceList()             # Get an upto date list of devices
    logging.info('Updated device list...')
    logging.info(updatedDeviceList)
    if deviceList != updatedDeviceList:             # Compare the previous and current lists
        logging.info('Device lists are different')
        newDevices = [i for i in updatedDeviceList if i not in deviceList]
        logging.info('New devices:')
        logging.info(newDevices)
        removedDevices = [i for i in deviceList if i not in updatedDeviceList]
        logging.info('Removed Devices')
        logging.info(removedDevices)
        for deviceName in newDevices:               # Create discovery data for new devices
            publishDiscovery(deviceName)
        for deviceName in removedDevices:            # Remove HA entity/device for removed devices
            removeDiscovery(deviceName)
    else:
        logging.info('Device lists are the same')
    deviceList = updatedDeviceList                  # Update the device list
    publishDeviceAttributes()                       # Call to publish the attributes for each device
    startPeriodTimer()

def startPeriodTimer():
    logging.debug('--> startPeriodTimer')
    global endPeriodTimer
    global periodTimeRunningStatus
    stopPeriodTimer()
    endPeriodTimer = threading.Timer(updateFrequency * 30.0, periodTimeoutHandler)
    endPeriodTimer.start()
    periodTimeRunningStatus = True
    logging.info('Timer Started')
    
def stopPeriodTimer():
    global endPeriodTimer
    global periodTimeRunningStatus
    endPeriodTimer.cancel()
    periodTimeRunningStatus = False
    logging.info('Timer stopped')


# Get VPN Device List
def getDeviceList():
    logging.debug('--> getDeviceList')
    rawDevices = os.popen("pivpn -l").read().split()
    deviceCount = (len(rawDevices) - 9) / 7
    x = 0
    namePosition = 9
    deviceList = []
    while x < deviceCount:
        deviceName = rawDevices[namePosition]
        logging.info('Appending device ' + deviceName + ' to deviceList')
        deviceList.append(deviceName)
        x += 1
        namePosition += 7
    return deviceList   

# Publish discovery data for a device
def publishDiscovery(deviceName):
    logging.debug('--> publishDiscovery(' + deviceName + ')')
    discoveryTopic = '{}{}/config'.format(discoveryTopicPrefix, deviceName)
    payload = {}
    payload['name'] = 'VPN Client {}'.format(deviceName.title())
    payload['unique_id'] = 'VPN{}{}Client'.format(vpnType, deviceName)
    #payload['device_class'] = 'timestamp'
    payload['state_topic'] = '{}{}/state'.format(topicPrefix, deviceName)
    payload['payload_available'] = 'Online'
    payload['payload_not_available'] = 'Offline'
    payload['availability_topic'] = '{}status'.format(topicPrefix)
    payload['icon'] = 'mdi:vpn'
    payload['json_attributes_topic'] = '{}{}/attr'.format(topicPrefix, deviceName)
    payload['dev'] = {
            'identifiers' : ['vpnClient{}'.format(deviceName)],
            'manufacturer' : vpnType,
            'name' : 'VPN-Client-{}'.format(deviceName.title()),
            'model' : 'VPN Client',
            'sw_version': "not applicable"            
        }
    client.publish(discoveryTopic, json.dumps(payload), 0, retain=True)

# Remove discovery data for deleted devices
def removeDiscovery(deviceName):
    logging.debug('--> publishDiscovery(' + deviceName + ')')
    discoveryTopic = '{}{}/config'.format(discoveryTopicPrefix, deviceName)
    payload = {}
    client.publish(discoveryTopic, json.dumps(payload), 0, retain=True)

# Publish attribute data for devices
def publishDeviceAttributes():
    logging.debug('--> publishDeviceAttributes')
    for deviceName in deviceList:
        logging.info('Getting device attributes for ' + deviceName)
        query = "pivpn -c | grep '" + deviceName + "'"          # Get device row data
        clientRecord = os.popen(query).read().split()
        if clientRecord[5]=="(not":
            data = json.dumps({"device":clientRecord[0], "remote_ip":clientRecord[1], "local_ip":clientRecord[2], "received":clientRecord[3], "sent":clientRecord[4], "seen":clientRecord[5]+' '+clientRecord[6]})
            state = clientRecord[5] + ' ' + clientRecord[6]
        else:
            data = json.dumps({"device":clientRecord[0], "remote_ip":clientRecord[1], "local_ip":clientRecord[2], "received":clientRecord[3], "sent":clientRecord[4], "seen":clientRecord[5]+' '+clientRecord[6]+' '+clientRecord[7]+' '+clientRecord[8]+' '+clientRecord[9]})
            state = clientRecord[5] + ' ' + clientRecord[6] + ' ' + clientRecord[7] + ' ' + clientRecord[8] + ' ' + clientRecord[9]
        logging.info('Device attributes...')
        logging.info(data)
        logging.info('Device state...')
        logging.info(state)
        topic = '{}{}/attr'.format(topicPrefix, deviceName) 
        client.publish(topic, str(data), retain=False)      # Publish attributes
        topic = '{}{}/state'.format(topicPrefix, deviceName)
        client.publish(topic, state, retain=False)          # Publish state


# Timer configuration
deviceList = []
endPeriodTimer = threading.Timer(updateFrequency * 60.0, periodTimeoutHandler)
periodTimeRunningStatus = False
reported_first_time = False


# MQTT connection
client = mqtt.Client()
client.on_connect = on_connect
client.username_pw_set(username=mqttUser,password=mqttPassword)
client.connect(mqttAddress, 1883, 60)
stateTopic = '{}status'.format(topicPrefix)     # set last will
client.will_set(stateTopic, payload='Offline', qos=0, retain=True) 

# Commence Timer & get initial device list
deviceList = getDeviceList()
logging.info('Inital device list...')
logging.info(deviceList)
startPeriodTimer()


client.loop_forever()

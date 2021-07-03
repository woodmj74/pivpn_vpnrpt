#!/usr/bin/env python3

import os
import json
import paho.mqtt.client as mqtt
import time
import threading
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

# -----------------------------
# --- CONFIGURATION OPTIONS ---
# -----------------------------

discoveryTopicPrefix = 'homeassistant/sensor/'
topicPrefix = 'home/nodes/sensor/'                  # [clientname]/suffix (state /state, attributes /attr, availability /status)
vpnType = 'WireGuard'                               # WireGuard or OpenVPN or other?
mqttUser = 'homeassistant'
mqttPassword = 'Phei1ja3ahHe2hee3tue2ahx4afaep9liepohcheinie7thohzoz4yae2but4aij'
mqttAddress = '192.168.10.84'                       # assumes standard ports
updateFrequency = 1                                 # in minutes

# ---------------------------------
# --- END CONFIGURATION OPTIONS ---
# ---------------------------------


# MQTT Connection Made
def on_connect(client, userdata, flags, rc):
    logging.debug('--> on_connect')
    logging.info('Connected with result code '+str(rc))
##??    stateTopic = '{}status'.format(topicPrefix)     # publish status update
##??    client.publish(stateTopic, payload='Online', qos=0, retain=True) 
    for client in clientList:                       # call discovery for each device
        publishDiscovery(client)

# Timer based on update frequency
def periodTimeoutHandler():
    global clientList
    logging.info('Timer interrupt')
    updatedClientList = getClientList()             # Get an upto date list of clients
    logging.info('Updated client list...')
    logging.info(updatedClientList)
    if clientList != updatedClientList:             # Compare the previous and current lists
        logging.info('Client lists are different')
        newClients = [i for i in updatedClientList if i not in clientList]
        logging.info('New clients:')
        logging.info(newClients)
        removedClients = [i for i in clientList if i not in updatedClientList]
        logging.info('Removed Clients')
        logging.info(removedClients)
        for clientName in newClients:               # Create discovery data for new devices
            publishDiscovery(clientName)
        for clientName in removedClients:            # Remove HA entity/device for removed devices
            removeDiscovery(clientName)
    else:
        logging.info('Client lists are the same')
    clientList = updatedClientList                  # Update the device list
    publishClientAttributes()                       # Call to publish the attributes for each device
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


# Get VPN Client List
def getClientList():
    logging.debug('--> getClientList')
    rawClients = os.popen("pivpn -l").read().split()
    clientCount = (len(rawClients) - 9) / 7
    x = 0
    namePosition = 9
    clientList = []
    while x < clientCount:
        clientName = rawClients[namePosition]
        logging.info('Appending client ' + clientName + ' to clientList')
        clientList.append(clientName)
        x += 1
        namePosition += 7
    return clientList   

# Publish discovery data for a client
def publishDiscovery(clientName):
    logging.debug('--> publishDiscovery(' + clientName + ')')
    discoveryTopic = '{}{}/config'.format(discoveryTopicPrefix, clientName)       
    payload = {}
    payload['name'] = 'VPN Client {}'.format(clientName.title())
    payload['unique_id'] = 'VPN{}{}Client'.format(vpnType, clientName)
    payload['state_topic'] = '{}{}/state'.format(topicPrefix, clientName)
    payload['payload_available'] = 'Online'
    payload['payload_not_available'] = 'Offline'
    payload['availability_topic'] = '{}{}/status'.format(topicPrefix, clientName)
    payload['icon'] = 'mdi:vpn'
    payload['json_attributes_topic'] = '{}{}/attr'.format(topicPrefix, clientName)
    payload['dev'] = {
            'identifiers' : ['vpncltmon'],
            'manufacturer' : vpnType,
            'name' : 'VPN Client Monitor'          
        }
    client.publish(discoveryTopic, json.dumps(payload), 0, retain=True)

    stateTopic = '{}{}/status'.format(topicPrefix, clientName)     # set last will
    client.will_set(stateTopic, payload='Offline', qos=0, retain=True) 

    stateTopic = '{}{}/status'.format(topicPrefix, clientName)     # publish status update
    client.publish(stateTopic, payload='Online', qos=0, retain=True) 

# Remove discovery data for deleted devices
def removeDiscovery(clientName):
    logging.debug('--> publishDiscovery(' + clientName + ')')
    discoveryTopic = '{}{}/config'.format(discoveryTopicPrefix, clientName)
    payload = {}
    client.publish(discoveryTopic, json.dumps(payload), 0, retain=True)

# Publish attribute data for devices
def publishClientAttributes():
    logging.debug('--> publishClientAttributes')
    for clientName in clientList:
        logging.info('Getting client attributes for ' + clientName)
        query = "pivpn -c | grep '" + clientName + "'"          # Get device row data
        clientRecord = os.popen(query).read().split()
        if clientRecord[5]=="(not":
            data = json.dumps({"client":clientRecord[0], "remote_ip":clientRecord[1], "local_ip":clientRecord[2], "received":clientRecord[3], "sent":clientRecord[4], "seen":clientRecord[5]+' '+clientRecord[6]})
            state = clientRecord[5] + ' ' + clientRecord[6]
        else:
            data = json.dumps({"client":clientRecord[0], "remote_ip":clientRecord[1], "local_ip":clientRecord[2], "received":clientRecord[3], "sent":clientRecord[4], "seen":clientRecord[5]+' '+clientRecord[6]+' '+clientRecord[7]+' '+clientRecord[8]+' '+clientRecord[9]})
            state = clientRecord[5] + ' ' + clientRecord[6] + ' ' + clientRecord[7] + ' ' + clientRecord[8] + ' ' + clientRecord[9]
        logging.info('Client attributes...')
        logging.info(data)
        logging.info('Client state...')
        logging.info(state)
        topic = '{}{}/attr'.format(topicPrefix, clientName) 
        client.publish(topic, str(data), retain=False)      # Publish attributes
        topic = '{}{}/state'.format(topicPrefix, clientName)
        client.publish(topic, state, retain=False)          # Publish state


# Timer configuration
clientList = []
endPeriodTimer = threading.Timer(updateFrequency * 60.0, periodTimeoutHandler)
periodTimeRunningStatus = False
reported_first_time = False


# MQTT connection
client = mqtt.Client()
client.on_connect = on_connect
client.username_pw_set(username=mqttUser,password=mqttPassword)
client.connect(mqttAddress, 1883, 60)
##??????? stateTopic = '{}status'.format(topicPrefix)     # set last will
##???????? client.will_set(stateTopic, payload='Offline', qos=0, retain=True) 

# Commence Timer & get initial device list
clientList = getClientList()
logging.info('Inital client list...')
logging.info(clientList)
startPeriodTimer()


client.loop_forever()

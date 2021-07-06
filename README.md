# pivpn_vpnrpt
MQTT Reporting for PI VPN on Home Assistant

** I am not a pro and hacked this together through the good work of others, I would welcome feedback and help with improving this **

Purpose: report configured VPN clients on PiVPN to HomeAssistant via MQTT

How to use: assumes you already have an MQTT broker running and the appropiate configuration with Home Assistant set up. To use this, place the python script on your piVPN box, the run! Would be best setting a service to run this.

What it does: when running it effectively presents the ```pivpn -c``` command data to Home Assistance. Using discovery a device is created in HA representing piVPN instance and each configured client then is represented as an entity of that device.

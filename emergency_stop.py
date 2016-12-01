#!/home/pi/oprint/bin/python

import sys, os, pwd, time
import RPi.GPIO as GPIO
import httplib
import logging
from time import sleep
from subprocess import call
import yaml
import thread
import smbus
 
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

#RPi GPIO pin where the momentary Emergency Stop button is connected
PIN_BUTTON = 18

#RPi GPIO pin that controls the relay to turn on/off the main power for the printer 
PIN_POWER = 24

#RPi GPIO pin connected to any of the available RESET pins on the printer board
RESET_PIN = 21

#funduino address
I2C_ADDRESS = 0x04

#gpio on funduino (reference only)
PIN_5 = 0
PIN_6 = 1
PIN_9 = 2
LED_STATUS = 3
LED_WIFI = 4

#led status (reference only)
LED_OFF = 0
LED_ON = 1
LED_BLINK = 2
LED_BLINK_FAST = 3
LED_BLINK_BEEP_BEEP = 4
LED_FADE = 5

HEARTBEAT = 1
BOUNCE = 300

REQUEST_RID = 1

EMPTY_RID = 100000


try:
	logging.basicConfig(filename='/var/log/emergency_stop.log',level=logging.DEBUG,format='%(asctime)s.%(msecs).03d %(message)s',datefmt='%d/%m/%Y %H:%M:%S')
except:
	pass
	
def log(message):
	print(message)
	try:
		logging.info(message)
	except:
		pass

def is_root():
    return pwd.getpwuid( os.getuid() )[ 0 ] == "root"

octoprint_config = "/home/pi/.octoprint/config.yaml"
API_KEY = None
if os.path.isfile(octoprint_config):
	with open(octoprint_config,'r') as f:
		data = yaml.safe_load(f)
		API_KEY = data["api"]["key"]
else:
	log("Octoprint config file not found. API_KEY unavailable. ")


#[resistor value][name, color, extruders, nozzles, diameter]
# each hotend has up to 3 resistors in paralel, which with the additional default 100k resistor will identify the characteristics of the hotend.
# empty values indicate 
smart_heads = dict( p1 = [[10000], ["chimera", "white", 2, 2, 0.4]], 
					p2 = [[22000], ["chimera", "black", 2, 2, 0.2]], 
					p3 = [[4990], ["cyclops", "blue", 2, 1, 0.4]] , 
					p4 = [[4990, 22000], ["chimera volcano", "green", 2, 2, 0.8]], 
					c1 = [[], ["spindle"]], 
					c2 = [[], ["laser"]] )

for v in smart_heads.values():
	v[0].append(EMPTY_RID) #known value
	
for k, v in smart_heads.items():
	rs =  1 / sum([ 1.0 / float(x) for x in v[0]])
	v[0] = int(rs)
	#print "%s => %s"%(k, v[0])

#map resistor value to RID 
rid_values = [v[0] for k,v in smart_heads.items()] 

#map to them back 
rids = dict(zip(rid_values, smart_heads.keys()))

#remove empty 
if 1 in rids.keys():
	rids.pop(1)

marlin_firmware_config = "/home/pi/.marlin"
cnc_firmware_config = "/home/pi/.grbl"

current_rid = None

def update_hotend(rid):
	global current_rid

	if (rid == current_rid):
		 return
		 	
	current_rid = rid
	
	if (rid == EMPTY_RID):
		
		#send_led_command(LED_STATUS, LED_BLINK_FAST):
		
		data = '{"appearance":{"name":"Don\'t print!", "color":"red"}}'
		call('/usr/bin/curl --insecure --connect-timeout 15 --request POST -H "Content-Type: application/json" -H "X-Api-Key: %s" --data "%s"  https://i3.hossu.net/api/settings > /dev/null 2>&1'%(API_KEY, data.replace('"','\\"')), shell=True)

		data = '{"command":"reload"}'
		call('/usr/bin/curl --insecure --connect-timeout 15 --request POST -H "Content-Type: application/json" -H "X-Api-Key: %s" --data "%s" https://i3.hossu.net/api/plugin/switch > /dev/null 2>&1'%(API_KEY, data.replace('"','\\"')), shell=True)

		#data = '{"command": "disconnect"}'
		#call('/usr/bin/curl --insecure --connect-timeout 15 --request POST -H "Content-Type: application/json" -H "X-Api-Key: %s" --data "%s" https://i3.hossu.net/api/connection > /dev/null 2>&1'%(API_KEY, data.replace('"','\\"')), shell=True)
		
	elif rid.startswith('p'):
		
		#send_led_command(LED_STATUS, LED_ON):
		
		name, color, extruders, nozzles, diameter = smart_heads[rid][1]
		log("Updating hotend config and OctoPrint profile to `%s with %s extruders and %s, %smm nozzle(s)`..."%(name, extruders, nozzles, diameter))
		if nozzles == 1:
			offset = "[0,0]"
		if nozzles == 2:
			offset = "[0,0],[18,0]"
			
		#data = '{"command": "connect"}'
		#call('/usr/bin/curl --insecure --connect-timeout 15 --request POST -H "Content-Type: application/json" -H "X-Api-Key: %s" --data "%s" https://i3.hossu.net/api/connection > /dev/null 2>&1'%(API_KEY, data.replace('"','\\"')), shell=True)

		data = '{"profile":{"extruder":{"count":%s,"offsets":[%s],"nozzleDiameter":%s}}}'%(extruders, offset, diameter)
		call('/usr/bin/curl --insecure --connect-timeout 15 --request PATCH -H "Content-Type: application/json" -H "X-Api-Key: %s" --data "%s"  https://i3.hossu.net/api/printerprofiles/_default > /dev/null 2>&1'%(API_KEY, data.replace('"','\\"')), shell=True)

		data = '{"appearance":{"name":"%smm %s", "color":"%s"}}'%(diameter, name ,color)
		call('/usr/bin/curl --insecure --connect-timeout 15 --request POST -H "Content-Type: application/json" -H "X-Api-Key: %s" --data "%s"  https://i3.hossu.net/api/settings > /dev/null 2>&1'%(API_KEY, data.replace('"','\\"')), shell=True)
		
		data = '{"command":"reload"}'
		call('/usr/bin/curl --insecure --connect-timeout 15 --request POST -H "Content-Type: application/json" -H "X-Api-Key: %s" --data "%s" https://i3.hossu.net/api/plugin/switch > /dev/null 2>&1'%(API_KEY, data.replace('"','\\"')), shell=True)
		
		with open("/home/pi/.hotend", 'w') as f:
			f.write("|".join([str(extruders), str(nozzles), str(diameter), name]))

		#TODO: check if current firmware matches the smart head 
		if os.path.isfile(marlin_firmware_config):
			with open(marlin_firmware_config,'r') as f:
				firmware_extruders, firmware_nozzles = f.readline().split("|")
				#check for single dual extruders and update firmware if needed
		else:
			#most likely we need to update firmware since we're on cnc
			pass
			#remove cnc_firmware_config

	elif rid.startswith('c'):
		log("CNC machines not yet supported")
		
		#delete marlin_firmware_config


def printer_reset():
	state = GPIO.input(PIN_POWER)
	if state:
		printer_off()
	GPIO.setup(RESET_PIN, GPIO.OUT, initial=0)
	time.sleep(1)
	GPIO.setup(RESET_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	if state:
		printer_on()
	log("[reset printer]")

def printer_off():
	GPIO.output(PIN_POWER, GPIO.LOW)
	log("[printer powered off]")

def printer_on():
	GPIO.output(PIN_POWER, GPIO.HIGH)	
	log("[printer powered on]")

def current_service():
	with open('/home/pi/.service', 'r') as f:
		return f.read().strip() #octoprint or cyclone

def web_service_restart():	
	service = current_service()
	call(["sudo", "service", service, "restart"])
	log("[%s restarted]"%service)
	
def restart_me():
	call(["sudo", "service", "emergency_stop", "restart"])
	log("[emergency_stop service restarted]")	

def restart_wifi():
	call(["sudo", "/home/pi/bin/wifi.sh", "reset"])
	log("[wifi restarted]")	
		
def emergency_stop():
	log("[emergeny stop start]")
	printer_reset()
	web_service_restart()
	log("[emergeny stop complete]")

def check_button(channel):
	state = GPIO.input(PIN_BUTTON)
	log("Detected button [%s] pressed [%s]? !"%(channel, state))
	if not state: #safety pin 2
		log("Buton [%s]!"%state)
		emergency_stop()
		#restart_wifi()
		restart_me()

def send_led_command(led, status):
	try:
		bus = smbus.SMBus(1)
		bus.write_word_data(I2C_ADDRESS, led, status)
		bus.close()
	except Exception as e:
		log("Failed to set LED status [%s]"%e)
		
def almost_equal(a, b, tolerance = 15): 
	bt = b * tolerance / 100
	#print "tolerance on %s = %s"%(b, bt)
	if a < b - bt: return False
	if a > b + bt: return False
	return True

def read_resistor_value ():
	try:
		bus = smbus.SMBus(1)
		ret = bus.read_word_data(I2C_ADDRESS, REQUEST_RID)
		bus.close()
		return ret
	except:
		pass

def smart_head_detection():
	try:
		unknown = True
		resistor_value = read_resistor_value()
		log("RID %s"%resistor_value)
		if almost_equal(resistor_value, EMPTY_RID): #empty!
			update_hotend(EMPTY_RID)
		else:
			for v in rid_values:
				if almost_equal(resistor_value, v):
					rid_value = rids.get( v )
					update_hotend( rid_value )
					unknown = False
		if unknown:
			log("Unknown RID %s"%resistor_value)
	except Exception as e:
		log("Error in the 'smart_head_detection' [%s]"%e)

def detection_loop():
	while True:
		smart_head_detection()
		time.sleep(10) #every 10 seconds

	
if __name__ == "__main__":
	if GPIO.VERSION >= "0.6" or is_root():
		
		GPIO.setup(PIN_BUTTON, GPIO.IN)
		GPIO.setup(PIN_POWER, GPIO.OUT)
		GPIO.setup(RESET_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		if len(sys.argv) > 1 and sys.argv[1] == "run":			#run from command line (called from octoprint system menu)
			emergency_stop()
		elif len(sys.argv) > 1 and sys.argv[1] == "reset":		#reset the printer board only
			printer_reset()	
		elif len(sys.argv) > 1 and sys.argv[1] == "wifi":		#reset the wifi
			restart_wifi()	
		elif len(sys.argv) > 1 and sys.argv[1] == "on":			#turn printer on
			printer_on()
		elif len(sys.argv) > 1 and sys.argv[1] == "off":		#turn printer off
			printer_off()
		elif len(sys.argv) > 1 and sys.argv[1] == "rid":		#turn printer off
			if len(sys.argv) == 2:
				time.sleep(1)
				smart_head_detection() 
			else:
				if API_KEY:
					try:
						rid = int(sys.argv[2]) 
					except:
						rid = None
					if len(sys.argv) > 2 and rid in rid_values:
						update_hotend(rids.get( rid ))
					else:
						if rid:
							print("Valid options %s"%dict(zip(rids, [ smart_heads[x][0] + " " + str(smart_heads[x][4]) if len(smart_heads[x]) == 5 else smart_heads[x][1] for x in smart_heads.keys() ])))
						else:
							resistor_value = read_resistor_value()
							print("RID %s"%resistor_value)

		elif len(sys.argv) > 2 and sys.argv[1] == "led":
			try:
				send_led_command(int(sys.argv[2]), int(sys.argv[3]))
			except Exception as e:
				log(e)
				
		elif len(sys.argv) > 1 and sys.argv[1] == "service":	#start as service
			log("start as service")
			GPIO.add_event_detect(PIN_BUTTON, GPIO.FALLING, callback=check_button, bouncetime=BOUNCE) #bouncetime - safety pin 1
 
			thread.start_new_thread(detection_loop, ())
			
			try:
				while True:
					time.sleep(HEARTBEAT)
			except KeyboardInterrupt:
				log("[done]")
		else:
			log("Valid keywords: run, service, wifi, on, off, rid, led ID Staus")
	else:
		log("RPi.GPIO must be greater than 0.6 or you must be root")

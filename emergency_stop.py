#!/usr/bin/env python
import sys, os, pwd, time
import RPi.GPIO as GPIO
import httplib
import logging
from time import sleep
from subprocess import call

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

#RPi GPIO pin where the momentary Emergency Stop button is connected
PIN_BUTTON = 18

#RPi GPIO pin that controls the relay to turn on/off the main power for the printer 
PIN_POWER = 24

#RPi GPIO pin connected to any of the available RESET pins on the printer board
RESET_PIN = 2

HEARTBEAT = 1
BOUNCE = 300

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

def get_username():
    return pwd.getpwuid( os.getuid() )[ 0 ]

def printer_reset():
	GPIO.setup(RESET_PIN, GPIO.OUT, initial=0)
	time.sleep(1)
	GPIO.cleanup(RESET_PIN)
	log("[reset printer]")

def printer_off():
	GPIO.output(PIN_POWER, GPIO.LOW)
	log("[printer powered off]")

def printer_on():
	GPIO.output(PIN_POWER, GPIO.HIGH)	
	log("[printer powered on]")

def octoprint_restart():	
	call(["service", "octoprint", "restart"])
	log("[octoprint restarted]")

def emergeny_stop():
	log("[emergeny stop start]")
	state = GPIO.input(PIN_POWER)
	printer_off()
	printer_reset()
	octoprint_restart()
	if state:
		printer_on()
	log("[emergeny stop complete]")
	
def ke():
	log("[reinitializing emergeny button]")	
	call(["service", "emergency_stop", "restart"])
		
def check_button(channel):
	state = GPIO.input(PIN_BUTTON)
	log("Detected button [%s] pressed [%s]? !"%(channel, state))
	if not state: #safety pin 2
		log("Buton [%s]!"%state)
		emergeny_stop()
		ke()
	
if __name__ == "__main__":
	user = get_username() 
	if user == "root":
		log("[started as root]")
		
		GPIO.setup(PIN_BUTTON, GPIO.IN)
		GPIO.setup(PIN_POWER, GPIO.OUT)		

		if len(sys.argv) > 1 and sys.argv[1] == "run":			#run from command line (called from octoprint system menu)
			emergeny_stop()
		elif len(sys.argv) > 1 and sys.argv[1] == "reset":		#reset the printer board only
			printer_reset()	
		elif len(sys.argv) > 1 and sys.argv[1] == "ke":			#restart service 
			ke()
		else:													#start as service
			GPIO.add_event_detect(PIN_BUTTON, GPIO.FALLING, callback=check_button, bouncetime=BOUNCE) #bouncetime - safety pin 1
			try:
				while True:
					time.sleep(HEARTBEAT)
			except KeyboardInterrupt:
				log("[done]")
		
		GPIO.cleanup()
	else:
		log("%s, you must be root!"%user)

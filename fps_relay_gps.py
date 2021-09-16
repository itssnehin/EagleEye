import blynklib
import RPi.GPIO as GPIO
import os
import thread
import random
import serial
import time
import pynmea2
import string
import fingerpi as fp # fps


from time import sleep
GPIO.setmode(GPIO.BOARD)

pins = [31, 33, 35, 37] #Board pins
BLYNK_AUTH = '3UfzuSNKfdtCn01CTrZ_QpkXOeYW00MZ'
blynk = blynklib.Blynk(BLYNK_AUTH)

#initialize pins
for pin in pins:
	print("Pin " + str(pin) + " initialized!")
	GPIO.setup(pin, GPIO.OUT)

#Function for +V on H-bridge
def high():
	GPIO.output(pins[0], True)
	GPIO.output(pins[1], False)
	GPIO.output(pins[2], False)
	GPIO.output(pins[3], True)
	blynk.virtual_write(1, 255)

#Function for -V on H-Bridge
def low():
	GPIO.output(pins[0], False)
	GPIO.output(pins[1], True)
	GPIO.output(pins[2], True)
	GPIO.output(pins[3], False)
	blynk.virtual_write(1, 0)



terminal = ""
portname = "/dev/ttyACM0"
f = fp.FingerPi(port = portname)
f.CmosLed(False)


# ------------------------------------------ FPS Bullshit --------------------------------------------

def setup_FPS():
	port = "/dev/ttyACM0" #USB UART interface
	baudrate = 9600
	device_id = 0x01
	timeout = 2

	if not os.path.exists(port):
		raise IOError("Port " + port + "can't be opened")

	ser = serial.Serial(port, baudrate, timeout=5)
	ser.flushInput()

	#f = fp.FingerPi()
	print "Opening connection to FPS"
	f.Open(extra_info = True, check_baudrate = True)
	f.ChangeBaudrate(115200)
	f.CmosLed(True)



def Enroll():
	# Need three enrolls to successfully enroll a user
	username = raw_input("Enter a username: \n")

	#find an open enroll id
	enrollid = 0
	usedid = True
	while usedid == True:
		msg = f.CheckEnrolled(enrollid)
		if msg[0]['ACK'] == True:
			enrollid = enrollid + 1
		else:
			usedid = False

	print("New ID for " + username + ": " + str(enrollid))


	# turn on backlight
	f.CmosLed(False)
	time.sleep(1)
	f.CmosLed(True)
	time.sleep(1)
	f.CmosLed(False)
	time.sleep(1)
	f.CmosLed(True)
	print("FPS LED On")	

	f.EnrollStart(enrollid)
	#Check if finger is on fps

	count = f.GetEnrollCount()
	print(count)
	
	pressed = False # Flag to check if finger is pressed
	print("First enrollment. Please place finger on the scanner.")
	
	#delay
	while pressed == False:
		#print(pressed)
		time.sleep(0.5)
		response = f.IsPressFinger()
		if int(response[0]['Parameter']) < 1:
			print("Finger Detected!")
			pressed = True
	
	#implement enroll1/2/3
	bret = f.CaptureFinger(True)
	iret = 0
	if bret != False:
		f.Enroll1()
		print("Remove finger.")

		while pressed == True:
			#print(pressed)
			time.sleep(0.5)
			response = f.IsPressFinger()
			if int(response[0]['Parameter']) > 1:
				print("Finger Removed!")
				pressed = False
		
		print("Press Finger again")
		
		while pressed == False:
			#print(pressed)
			time.sleep(0.5)
			response = f.IsPressFinger()
			if int(response[0]['Parameter']) < 1:
				print("Finger Detected!")
				pressed = True


		bret = f.CaptureFinger(True)
		
		if bret != False:
			f.Enroll2()
			print("Remove finger")

			while pressed == True:
				#print(pressed)
				time.sleep(0.5)
				response = f.IsPressFinger()
				if int(response[0]['Parameter']) > 1:
					print("Finger Detected!")
					pressed = False

			print("Press finger again")
			
			while pressed == False:
				#print(pressed)
				time.sleep(0.5)
				response = f.IsPressFinger()
				if int(response[0]['Parameter']) < 1:
					print("Finger Detected!")
					pressed = True
			
			bret = f.CaptureFinger(True)
			
			if bret != False:
				print("Remove finger")
				iret = f.Enroll3()

				if iret[0]['ACK'] == True:
					print("Enroll Successfull")
				else:
					print("Error with enrolling code:")
					print(iret)
			else:
				print("Failed to capture 3rd finger")
		else:
			print("Failed to capture 2nd finger")
	else:
		print("Failed to capture 1st finger")

	f.CmosLed(False)
	return True

def Identify():
	f.CmosLed(True)
	print("Place Finger on FPS")

	pressed = False
	while pressed == False:
		#print(pressed)
		time.sleep(0.2)
		response = f.IsPressFinger()
		if int(response[0]['Parameter']) < 1:
			print("Finger Detected!")
			pressed = True

	f.CaptureFinger(False)

	msg = f.Identify()

	if msg[0]['ACK'] == True:
		terminal = "User detected! \t User ID: " + str(msg[0]['Parameter'])
		print("User detected! \t User ID: " + str(msg[0]['Parameter']))
		print("Remove Finger.")
		return True
	else:
		print("Unauthorized User!")
		return False


# ------------------------------------------------------------------------------------------------------

# register handler for virtual pin V4 write event

WRITE_EVENT_PRINT_MSG = "[WRITE_VIRTUAL_PIN_EVENT] Pin: V{} Value: '{}'"






@blynk.handle_event('write V0')
def write_virtual_pin_handler(pin, value):
        if value == ['1']:
                print('Button ON')
                high()
        else:
                print('Button OFF')
                low()



def gps():
	port = "/dev/ttyAMA0"
	ser = serial.Serial(port, baudrate=9600, timeout = 1)
	dataout = pynmea2.NMEAStreamReader()
	newdata = ser.readline()
	
	if newdata[0:6] == "$GPRMC":
		newmsg = pynmea2.parse(newdata)
		lat = newmsg.latitude
		lng = newmsg.longitude
		gps = "Lat = " + str(lat) + " Long = " + str(lng)
		print(gps)
		blynk.virtual_write(3, str('{0:.3f}'.format(lat)))
		blynk.virtual_write(2, str('{0:.3f}'.format(lng)))



def main():
	
	delay = 7 # time delay in secs
	blynk.run()
	low()
	setup_FPS()
	blynk.virtual_write(3, 1)
	option = str(raw_input("Identify user? (y/n) \n"))

	if option == "y":
		f.CmosLed(True)
		valid = Identify()

		if valid:
			high()
		else:
			low()
	else:
		pass

	while True:
		blynk.run()
		#print("Here")
		gps()
		#print("There")


if __name__ == '__main__':
	
	try:
		main()
	except KeyboardInterrupt:
		print("Closing program")
	except:
		print("Other error ocurred!")
	finally:
		low()
		GPIO.cleanup()

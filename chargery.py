#Chargery.py

# Description: open RS232 serial port and read Chargery BMS data.
# Publish data to MQTT broker and logs to emoncms
# Credit - open source community esp Joe Elliot
# Final Edit - Mank1234 

# Compatible with chargery bms8t, bms16t and bms24t communication 
# protocol version 1.25 and backward compatible.
# insert your MQTT username and password if it exist
# change emoncmsApiKey to your emoncms apikey

# Protocol at http://chargery.com/uploadFiles/BMS24T,16T,8T%20Additional%20Protocol%20Info%20V1.25.pdf

# MQTT published topics - comment or uncomment the ones you need
# 1 to 13 sent to emoncms NODE 40, except no 8 and no 13
#1 chargerybms/watthour || 
#2 chargerybms/amphour
#3 chargerybms/batteryvolt
#4 chargerybms/cellhigh
#5 chargerybms/celllow
#6 chargerybms/maxvolt
#7 chargerybms/current
#8 chargerybms/modename #discharge, charge or storage ####this is not sent to emoncms
#9 chargerybms/modeint #0,1 or 2
#10 chargerybms/temp1
#11 chargerybms/temp2
#12 chargerybms/soc
#13 chargerybms/aggimped

import serial
import sys, os, io
import time
import binascii
import paho.mqtt.client as mqtt
import requests

emoncmsApiKey = "3bf8518d5f81ecd466eacec5a095a5f9"; #emoncms api write key
emoncmsURL = "http://127.0.0.1:9991/input/post";
mqttURL = "127.0.0.1";
mqttPort = "1883";
devName = '/dev/ttyUSB0'; #change to port name that ypur serial device is connected to


debug = False;
if ((len(sys.argv) > 1) and (sys.argv[1] == "-d")):
        debug=True
        print("sys.argv[1]: Debug: enabled")

modeList = ["Discharge", "Charge", "Storage"];
gotCellData = False;
gotSysData  = False;
gotIRData   = False;

def on_connect(client,userdata,flag,rc):
    if(debug):
        print("mqtt client connected \n");################
    client.connected_flag=True
    pass

def on_publish(client,userdata,result):
    if(debug):
        print("data published \n");##############
    pass

def bin2hex(str1):
        bytes_str = bytes(str1)
        return binascii.hexlify(bytes_str)

def get_voltage_value(byte1, byte2):
        return float((float(byte1 * 256) + float(byte2)) / 1000)

def get_current_value(byte1, byte2):
        return float((float(byte1 * 256) + float(byte2)) / 10)

def get_temp_value(byte1, byte2):
        return float((float(byte1 * 256) + float(byte2)) / 10)

def get_xh_value(byte1, byte2, byte3, byte4):
        return float((float(byte1) + (float(byte2) * 256) + (float(byte3) * 256 * 256) + (float(byte4) * 256 * 256 * 256)) / 1000)

def get_imped_value(byte1, byte2):
        return float((float(byte2 * 256) + float(byte1)) / 10) # note byte swap order

def getCellData(hexLine):
        decStrLen = len(hexLine)
        dataStart = 0   
        cellNum = 1
        cellHigh = 0.1111
        cellLow = 5.1111
        aggVolts = 0    # total voltage of the battery
        postString = "{";
        global gotCellData

        if (debug): print("getCellData: called - hexLine ", hexLine)
        
        for cell in range(dataStart, decStrLen-18, 4): # exclude checksum,wh and ah
        		#cellNum and cellVolts retrieval
                cellVolts = get_voltage_value(int(hexLine[cell:cell+2], 16), int(hexLine[cell+2:cell+4], 16))
                #publishing to MQTT
                #client.publish("chargerybms/cellvolt"+cellNum, cellVolts)
                if (debug): print("Cell ", cellNum, ":", cellVolts, "v")

                aggVolts += cellVolts
                cellNum += 1
                if(cellHigh < cellVolts): cellHigh = cellVolts
                if(cellLow > cellVolts): cellLow = cellVolts
		
        client.publish("chargerybms/batteryvolt", aggVolts)
        postString = postString + '"batteryvolt":' + str(aggVolts);
        
        client.publish("chargerybms/cellhigh", cellHigh)
        postString = postString + ',"cellhigh":' + str(cellHigh);
        
        client.publish("chargerybms/celllow", cellLow)
        postString = postString + ',"celllow":' + str(cellLow);

        #Wh - watthour retrieval
        Wh = get_xh_value(int(hexLine[cell+4:cell+6], 16), int(hexLine[cell+6:cell+8], 16), int(hexLine[cell+8:cell+10], 16), int(hexLine[cell+10:cell+12], 16))
        client.publish("chargerybms/watthour", Wh)
        postString = postString + ',"watthour":' + str(Wh);

	#Ah - amphour retrieval
        Ah = get_xh_value(int(hexLine[cell+12:cell+14], 16), int(hexLine[cell+14:cell+16], 16), int(hexLine[cell+16:cell+18], 16), int(hexLine[cell+18:cell+20], 16))
        client.publish("chargerybms/amphour", Ah)
        postString = postString + ',"amphour":' + str(Ah) + '}';
        
        postString = emoncmsURL + "?apikey=" + emoncmsApiKey + "&node=40&fulljson=" + postString; 
        
        if (debug):
                print("Battery Wh:", Wh, "Wh")
                print("Battery Ah:", Ah, "Ah")
                print("Battery voltage:", aggVolts, "v")
                print("Highest cell voltage:", cellHigh, "v")
                print("Lowest cell voltage:", cellLow, "v")
                print (postString)

        #post to Emoncms
        requests.post(postString);
       
        gotCellData = True;
        return(False)

def getSysData(hexLine):
        decStrLen = len(hexLine)
        dataStart = 4   
        postString="{";
        global gotSysData
        
        if (debug): print("getSysData: called - hexLine ", hexLine)

        endVolt_hi = hexLine[0:2]       # End voltage of cell
        endVolt_lo = hexLine[2:4]       # End voltage of cell

        mode       = hexLine[4:6]       # Current mode

        amps_hi    = hexLine[6:8]       # Current amps
        amps_lo    = hexLine[8:10]      # Current amps

        temp1_hi   = hexLine[10:12]     # Temp 1
        temp1_lo   = hexLine[12:14]     # Temp 1

        temp2_hi   = hexLine[14:16]     # Temp 2
        temp2_lo   = hexLine[16:18]     # Temp 2

        soc        = hexLine[18:20]     # SOC

        maxVolts = get_voltage_value(int(endVolt_hi, 16), int(endVolt_lo, 16))
        client.publish("chargerybms/maxvolt", maxVolts)
        postString = postString + '"maxvolt":' + str(maxVolts);

        currentFlow = get_current_value(int(amps_hi, 16), int(amps_lo, 16))
        
        modeName = modeList[int(mode, 16)]
        client.publish("chargerybms/modename", modeName)
       # postString = postString + ',"modename":"' + modeName + '"';

        modeInt = int(mode, 16)
        client.publish("chargerybms/modeint", modeInt)
        postString = postString + ',"modeint":' + str(modeInt);

        temp1 = get_temp_value(int(temp1_hi, 16), int(temp1_lo, 16))
        client.publish("chargerybms/temp1", temp1)
        postString = postString + ',"temp1":' + str(temp1);

        temp2 = get_temp_value(int(temp2_hi, 16), int(temp2_lo, 16))
        client.publish("chargerybms/temp2", temp2)
        postString = postString + ',"temp2":' + str(temp2);

        socInt = int(soc, 16)
        client.publish("chargerybms/soc", socInt)
        postString = postString + ',"soc":' + str(socInt);

        if (int(mode) == 0):
                currentFlow = currentFlow * -1 # flow is in or out of the battery?
                
        client.publish("chargerybms/current", currentFlow)
        postString = postString + ',"current":' + str(currentFlow) + '}';

        postString = emoncmsURL + "?apikey=" + emoncmsApiKey + "&node=40&fulljson=" + postString;

        if (debug):
                print("End voltage of cell_hi:", int(endVolt_hi, 16), "v")
                print("End voltage of cell_lo:", int(endVolt_lo, 16), "v")
                print("mode:", int(mode, 16))
                print("amps_hi:", int(amps_hi, 16), "a")
                print("amps_lo:", int(amps_lo, 16), "a")
                print("Temp 1_hi:", int(temp1_hi, 16), "c")
                print("Temp 1_lo:", int(temp1_lo, 16), "c")
                print("Temp 2_hi:", int(temp2_hi, 16), "c")
                print("Temp 2_lo:", int(temp2_lo, 16), "c")
                print("SOC:", int(soc, 16), "%")
                print (postString)

        #post to Emoncms
        requests.post(postString);

        gotSysData = True;
        return(False)
        
def getIRData(hexLine):
        decStrLen = len(hexLine)
        dataStart = 6   # data starts at byte 8 in 2 byte chunks (hi-lo)
        aggIR = 0    # total internal resistance of the battery
        cellNum = 1
        global gotIRData

        if (debug): print("getIRData: called - hexline ", hexLine)

        mode1      = hexLine[0:2]       # Current mode

        amps1_lo   = hexLine[2:4]       # Current amps  low byte first!
        amps1_hi   = hexLine[4:6]       # Current amps

        for cell in range(dataStart, decStrLen-2, 4): 
                cellImped = get_imped_value(int(hexLine[cell:cell+2], 16), int(hexLine[cell+2:cell+4], 16))		
                #client.publish("chargerybms/cellimped"+cellNum, cellImped)
                
                if (debug): print("Cell ", cellNum, ":", cellImped, "mohm")
                aggIR += cellImped
                cellNum += 1
		
        client.publish("chargerybms/aggimped",aggIR)
        
        currentFlow1 = get_current_value(int(amps1_hi, 16), int(amps1_lo, 16))
        
        modeName1 = modeList[int(mode1, 16)]
        modeInt1 = int(mode1, 16)
        #client.publish("chargerybms/modenameimped", modeName1)
        #client.publish("chargerybms/modeintimped", modeInt1)
        
        if (debug):
                print("current:",  currentFlow1, "A")
                print("mode:", modeInt1, modeName1)
                print("aggIR:", aggIR, "mohm")

        if (int(mode1) == 0):
                currentFlow1 = currentFlow1 * -1 # flow is in or out of the battery?

        #client.publish("chargerybms/currentimped", currentFlow)

        gotIRData = True;
        return(False)


################ main ##################     
client = mqtt.Client("chargery")
client.on_connect = on_connect
client.on_publish = on_publish
#set up username and password for your MQTT server 
#client.username_pw_set("username", password="password")
client.connect(mqttURL, mqttPort, 60)
client.loop_start()
ser = serial.Serial(devName, 115200, bytesize=8, parity='N', stopbits=1, timeout=0.1)
if (debug): print("Opened:", ser.name)
if ((len(sys.argv) > 1) and (sys.argv[1] == "-t")):
        debug = True;
        testData = '2424562D0CFD0D040D040D020D030D040D060D010D080D020D050CFE0D060CFB0D0F0CFC76FED50263140E0095'; #cell data
        testData += '2424570F0E240100E4008300845B27'; #sys data
        testData += '2424582801E4000100030003000300020003000000000001000100010000000500020003000300CC'; #ir data
        ser.write(binascii.unhexlify(testData));
while (ser.is_open):
        ser.read_until(b'$$',255) #wait for messag header
        aggChecksum = 72
        myBin  = ser.read()              # read command
        byteC = bin2hex(myBin)
        byteC = byteC.decode('utf-8')
        aggChecksum += int(byteC[0:2], 16)
        aggChecksum &= 255
        if (debug):
            print("command:",byteC[0:2], " aggChecksum:",aggChecksum)
        myBin = ser.read()              # read length
        byteD = bin2hex(myBin)
        byteD = byteD.decode('utf-8')
        aggChecksum += int(byteD[0:2], 16)
        aggChecksum &= 255
        if (debug):
            print("length:",byteD[0:2], " aggChecksum:",hex(aggChecksum))
        myBin = ser.read(int(byteD[0:2], 16)-4)     #read main data
        hexLine = bin2hex(myBin)
        hexLine = hexLine.decode('utf-8')
        dataLen = len(hexLine)
        for bite in range (0, dataLen-2, 2):
            aggChecksum += int(hexLine[bite:bite+2], 16)
            aggChecksum &= 255
            if (debug):
                print("data:",hexLine[bite:bite+2], " aggChecksum:",hex(aggChecksum))
		if (debug):
		    print("Checksum:",hexLine[bite+2:bite+4]," and aggChecksum:",hex(aggChecksum))
		    print("Read datalength:",str(dataLen)," and expected datalength:",str(int(byteD, 16)*2-8))
		if ((aggChecksum == int(hexLine[bite+2:bite+4], 16)) and ((int(byteD, 16)*2-8) == dataLen)):    #good checksum and datalength is same as specified
		    if (gotSysData and gotCellData):
			if (debug): print(" Cell and System data gotten")
			gotSysData  = False;
			gotCellData = False;
		    if (gotIRData):
			if (debug): print(" IR data gotten")
			gotIRData = False;
		    if (byteC == "56"):
			if (debug): print("Found Cell block", byteC, hexLine)
			if (not gotCellData):                                    
			    getCellData(hexLine)                                    
		    elif (byteC == "57"):
			if (debug): print("Found System block", byteC, hexLine)
			if (not gotSysData):
			    getSysData(hexLine)

		    elif (byteC == "58"):
			if (debug): print("Found System block", byteC, hexLine)
			if (not gotIRData):
			    getIRData(hexLine)
		    else:
			if (debug): print("Found Unexpected command block", byteC, hexLine)     
		else:
		    if (debug): print("Bad Checksum or data truncated")
client.disconnect()
client.loop_stop()
ser.close()

# End.

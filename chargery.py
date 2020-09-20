#Chargery.py

# Description: open RS232 serial port and read Chargery BMS data.
# Publish data to MQTT broker in proper format
# Credit - open source community esp Joe Elliot
# Final Edit - Mank1234 

# Compatible with chargery bms8t, bms16t and bms24t communication 
# protocol version 1.25 and backward compatible.
# uncomment line 59 - and insert your MQTT username and password if it exist

# Protocol at http://chargery.com/uploadFiles/BMS24T,16T,8T%20Additional%20Protocol%20Info%20V1.25.pdf

# MQTT published topics - comment or uncomment the ones you need
# chargerybms/cellvoltX where X is cell number 1 to 24 depending on numver of cells
#1 chargerybms/watthour
#2 chargerybms/amphour
#3 chargerybms/batteryvolt
#4 chargerybms/cellhigh #highest cell voltage
#5 chargerybms/celllow #lowest cell voltage
#6 chargerybms/maxvolt
#7 chargerybms/current
#8 chargerybms/modename #discharge, charge or storage
#9 chargerybms/modeint #0,1 or 2
#10 chargerybms/temp1
#11 chargerybms/temp2
#12 chargerybms/soc
# chargerybms/cellimpedX where X is cell number - 1 to 24 depending on number of cells
#13 chargerybms/aggimped
# chargerybms/currentimped
# chargerybms/modenameimped
# chargerybms/modeintimped
# Note headers, command, datalength and checksum are not published not published

import serial
import sys, os, io
import time
import binascii
import paho.mqtt.client as mqtt

devName='/dev/ttyUSB0' #change to port name that ypur serial device is connected to
modeList= ["Discharge", "Charge", "Storage"]
gotCellData = False;
gotSysData  = False;
gotIRData   = False;
debug = False;
test = False

def on_connect(client,userdata,flag,rc):
    if(debug):
        print("mqtt client connected \n")
    client.connected_flag=True
    pass

def on_publish(client,userdata,result):
    if(debug):
        print("data published \n")
    pass

client = mqtt.Client("chargery")
client.on_connect = on_connect
client.on_publish = on_publish
#set up username and password for your MQTT server 
#client.username_pw_set("username", password="password")
#ip address/website of MQTT server
client.connect("127.0.0.1", 1883, 60)
client.loop_start()

if (len(sys.argv) > 1):
        if (sys.argv[1] == "-d"):
                debug=True
                print("sys.argv[1]: Debug: enabled")
        if (sys.argv[1] == "-t"):
                debug=True
                print("sys.argv[1]: Test Data: enabled")

if (len(sys.argv) > 2):
        if (sys.argv[2] == "-d"):
                debug=True
                print("sys.argv[2]: Debug: enabled")
        if (sys.argv[2] == "-t"):
                test=True
                print("sys.argv[2]: Test Data: enabled")

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

def getCellData(hexLine, strLen):
        decStrLen = len(hexLine)
        minLen = 42     # minimal bytes for the 8s inc header (each byte is 2 chars)
        dataStart = 8   # cell voltage data starts at byte 9 in 2 byte chunks (hi-lo) was 8
        cellNum = 1
        cellHigh = 0.1111
        cellLow = 5.1111
        aggVolts = 0    # total voltage of the battery
        global gotCellData

        if (debug): print("getCellData: called - ", hexLine)
        if (debug):
                header  = hexLine[0:4]          # header
                command = hexLine[4:6]          # command
                dataLen = hexLine[6:8]          # data length
                print("header:", header)
                print("command:", command)
                print("dataLen:", int(dataLen, 16), "bytes")

        if (decStrLen < strLen) or (decStrLen < minLen):
                if (debug): print("Truncated cell block - len:", len(hexLine), "Expected:", strLen)
                return(True)
        else:
                if (debug): print("hexLine len", len(hexLine))
        for cell in range(dataStart, strLen*2-18, 4): # exclude checksum,wh and ah
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
        client.publish("chargerybms/cellhigh", cellHigh)
        client.publish("chargerybms/celllow", cellLow)

        #Wh - watthour retrieval
        Wh = get_xh_value(int(hexLine[cell+4:cell+6], 16), int(hexLine[cell+6:cell+8], 16), int(hexLine[cell+8:cell+10], 16), int(hexLine[cell+10:cell+12], 16))
        client.publish("chargerybms/watthour", Wh)

		#Ah - amphour retrieval
        Ah = get_xh_value(int(hexLine[cell+12:cell+14], 16), int(hexLine[cell+14:cell+16], 16), int(hexLine[cell+16:cell+18], 16), int(hexLine[cell+18:cell+20], 16))
        client.publish("chargerybms/amphour", Ah)
        
        if (debug):
                print("Battery Wh:", Wh, "Wh")
                print("Battery Ah:", Ah, "Ah")
                print("Checksum:", int(hexLine[strLen*2-2:strLen*2], 16))
                print("Battery voltage:", aggVolts, "v")
                print("Highest cell voltage:", cellHigh, "v")
                print("Lowest cell voltage:", cellLow, "v")
        gotCellData = True;
        return(False)

def getSysData(hexLine, strLen):
        decStrLen = len(hexLine)
        dataStart = 8   # data starts at byte 8 in 2 byte chunks (hi-lo)
        minLen = 30     # minimal bytes inc header (each byte is 2 chars)
        global gotSysData
        if (debug): print("getSysData: called - ", hexLine)
        if (decStrLen < strLen) or (decStrLen < minLen):
                if (debug): print("Truncated system block - len:", len(hexLine), "Expected:", strLen)
                return(True)
        else:
                if (debug): print("hexLine len", len(hexLine))
        # first 3 fields for debug only)
        header     = hexLine[0:4]       # header
        command    = hexLine[4:6]       # command
        dataLen    = hexLine[6:8]       # data length

        endVolt_hi = hexLine[8:10]       # End voltage of cell
        endVolt_lo = hexLine[10:12]       # End voltage of cell

        mode       = hexLine[12:14]       # Current mode

        amps_hi    = hexLine[14:16]       # Current amps
        amps_lo    = hexLine[16:18]      # Current amps

        temp1_hi   = hexLine[18:20]     # Temp 1
        temp1_lo   = hexLine[20:22]     # Temp 1

        temp2_hi   = hexLine[22:24]     # Temp 2
        temp2_lo   = hexLine[24:26]     # Temp 2

        soc        = hexLine[26:28]     # SOC

        chksum     = hexLine[28:30]     # Checksum

        maxVolts = get_voltage_value(int(endVolt_hi, 16), int(endVolt_lo, 16))
        client.publish("chargerybms/maxvolt", maxVolts)

        currentFlow = get_current_value(int(amps_hi, 16), int(amps_lo, 16))
        
        modeName = modeList[int(mode, 16)]
        client.publish("chargerybms/modename", modeName)

        modeInt = int(mode, 16)
        client.publish("chargerybms/modeint", modeInt)

        temp1 = get_temp_value(int(temp1_hi, 16), int(temp1_lo, 16))
        client.publish("chargerybms/temp1", temp1)

        temp2 = get_temp_value(int(temp2_hi, 16), int(temp2_lo, 16))
        client.publish("chargerybms/temp2", temp2)

        socInt = int(soc, 16)
        client.publish("chargerybms/soc", socInt)

        if (debug):
                print("dataLen:", int(dataLen, 16), "bytes")
                print("End voltage of cell:",  maxVolts, "v")
                print("mode:", modeInt, modeName)
                print("Current:", currentFlow, "A")
                print("Temp 1:", temp1, "c, ", temp1 * 9 / 5 + 32, "f")
                print("Temp 2:", temp2, "c, ", temp2 * 9 / 5 + 32, "f")
                print("SOC:", socInt, "%")
                print("Checksum:", int(chksum, 16))

        if (int(mode) == 0):
                currentFlow = currentFlow * -1 # flow is in or out of the battery?
                client.publish("chargerybms/current", currentFlow)
        else:
            client.publish("chargerybms/current", currentFlow)


        if (debug):
                print("header:", header)
                print("command:", command)
                print("dataLen:", int(dataLen, 16), "bytes")
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
                print("Checksum:", int(chksum, 16))

        gotSysData = True;
        return(False)
        
def getIRData(hexLine, strLen):
        decStrLen = len(hexLine)
        dataStart = 8   # data starts at byte 8 in 2 byte chunks (hi-lo)
        minLen = 32     # minimal bytes inc header (each byte is 2 chars)
        aggIR = 0    # total internal resistance of the battery
        cellNum = 1
        global gotIRData

        if (debug): print("getIRData: called - ", hexLine)

        if (decStrLen < strLen) or (decStrLen < minLen):
                if (debug): print("Truncated system block - len:", len(hexLine), "Expected:", strLen)
                return(True)
        else:
                if (debug): print("hexLine len", len(hexLine))

        # first 3 fields for debug only)
        header     = hexLine[0:4]       # header
        command    = hexLine[4:6]       # command
        dataLen    = hexLine[6:8]       # data length

        mode1      = hexLine[8:10]       # Current mode

        amps1_lo   = hexLine[10:12]       # Current amps  low byte first!
        amps1_hi   = hexLine[12:14]       # Current amps

        for cell in range(dataStart+6, strLen*2-2, 4): # IR data starts at 14 in 2 bytes chunk. exclude checksum
                cellImped = get_imped_value(int(hexLine[cell:cell+2], 16), int(hexLine[cell+2:cell+4], 16))		
                #client.publish("chargerybms/cellimped"+cellNum, cellImped)
                
                if (debug): print("Cell ", cellNum, ":", cellImped, "mohm")
                aggIR += cellImped
                cellNum += 1
		
        client.publish("chargerybms/aggimped",aggIR)
        
        chksum = hexLine[strLen*2-2:strLen*2]     # Checksum
        
        currentFlow1 = get_current_value(int(amps1_hi, 16), int(amps1_lo, 16))
        
        modeName1 = modeList[int(mode1, 16)]
        modeInt1 = int(mode1, 16)
        #client.publish("chargerybms/modenameimped", modeName1)
        #client.publish("chargerybms/modeintimped", modeInt1)
        
        if (debug):
                print("dataLen:", int(dataLen, 16), "bytes")
                print("current:",  currentFlow1, "A")
                print("mode:", modeInt1, modeName1)
                print("Checksum:", int(chksum, 16))
                print("aggIR:", aggIR, "mohm")

        if (int(mode1) == 0):
                currentFlow1 = currentFlow1 * -1 # flow is in or out of the battery?

        #client.publish("chargerybms/currentimped", currentFlow)

        gotIRData = True;
        return(False)


################ main ##################

# id id type len data                          checksum
# 24 24 57   0F  10 68 02 00 00 FF 21 FF 21 00 68
# 24 24 56   16  00 0A 00 0A 00 09 00 0B 00 0D 00 11 00 01 00 15 00 10
# len includes id & type
# data is written to the serial port every second or less, waiting too long results in garbled lines.
# Read fast and often to get the best results. System and Cell data is written at different frequencies.

ser = serial.Serial(devName, 115200, bytesize=8, parity='N', stopbits=1, timeout=0.1)
if (debug): print("Opened:", ser.name)

while (ser.is_open):
                
        myBin  = ser.read(256)              # read command

        hexLine = bin2hex(myBin)
        hexLine = hexLine.decode('utf-8')       # remove leading b in Python3
        
        if (test):
                hexLine='2424562D0CFD0D040D040D020D030D040D060D010D080D020D050CFE0D060CFB0D0F0CFC76FED50263140E009509876'; #for testing cell data
                #hexLine='2424582801E4000100030003000300020003000000000001000100010000000500020003000300CC'; #for internal resistance datat
                #hexLine='2424570F0E240100E4008300845B270000000'; #for testing system data
        
        dataLen = len(hexLine)

        if (debug): print("Read ", len(hexLine), "bytes: ", hexLine, "gotSysData:", gotSysData, "gotCellData:", gotCellData)

        if (dataLen > 14):
                byteA = hexLine[0:2]    # header
                byteB = hexLine[2:4]    # header
                byteC = hexLine[4:6]    # packet type 56 | 57
                byteD = hexLine[6:8]    # packet len

                if (byteA == "24" and byteB == "24"):

                        if (gotSysData and gotCellData):
                                gotSysData  = False;    # start all over again
                                gotCellData = False;

                        if (byteC == "56"):
                                if (debug): print("Found Cell block", byteA, byteB, byteC, hexLine)
                                if (not gotCellData):
                                        getCellData(hexLine, int(byteD, 16))
                        elif (byteC == "57"):
                                if (debug): print("Found System block", byteA, byteB, byteC, hexLine)
                                if (not gotSysData):
                                        getSysData(hexLine, int(byteD, 16))
                        elif (byteC == "58"):
                                if (debug): print("Found System block", byteA, byteB, byteC, hexLine)
                                if (not gotIRData):
                                        getIRData(hexLine, int(byteD, 16))
                        else:
                                if (debug): print("Found Unexpected command block", byteA, byteB, byteC, hexLine)
                else:
                        if (debug): print("Found Unexpected header block", byteA, byteB, byteC, hexLine)
        else:
                if (debug): print("Read Empty line", len(hexLine), "bytes: ", hexLine)


client.disconnect()
client.loop_stop()
ser.close()

# End.

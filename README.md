# Logger for Chargery Battery Monitor BMS8T, BMS16T and BMS24T.
Program runs as a service at the background without user intervention and continously logs data from chargery bms to your emoncms server and publishes to specific mqtt topics.

#### ** Background**
This was developed following pioneering work by gentlemen listed at the end of this file in a diy solar forum. Having used and enjoyed [solpiplog by nuno](https://github.com/njfaria/SolPipLog), I needed logging from chargery bms as i felt Victron BMS is doing what the bms already has built-in. With this I can monitor my setup, and optionally control my inverter.

#### ** MQTT topics published to**
1. chargerybms/watthour 
2. chargerybms/amphour 
3. chargerybms/batteryvolt 
4. chargerybms/cellhigh 
5. chargerybms/celllow 
6. chargerybms/maxvolt 
7. chargerybms/current 
8. chargerybms/modename 
9. chargerybms/modeint 
10. chargerybms/temp1 
11. chargerybms/temp2 
12. chargerybms/soc 
13. chargerybms/aggimped

#### ** Values sent to emoncms on node 40**
1. watthour 
2. amphour 
3. batteryvolt 
4. cellhigh 
5. celllow 
6. maxvolt 
7. current 
8. modeint 
9. temp1 
10. temp2 
11. soc 

#### ** Dependecies**
1. pyserial: run sudo pip install pyserial
2. paho-mqtt: run sudo pip install paho-mqtt
3. requests: run sudo pip install requests
4. emoncms and mqtt server


#### ** Installation **
For raspberry pi users,
1. clone the repository to "/home/pi" directory
2. execute setup.sh
3. edit "/home/pi/chargery.py as follows:

emoncmsApiKey = "ae4352drehuy65756i897ba7f"; value should be your emoncms api write key. 

emoncmsURL = "http://127.0.0.1:8081/input/post"; change to your emoncms ip address or url and port. 

mqttURL = "127.0.0.1"; change to your mqtt server address. 

mqttPort = "1883"; change to your mqtt server port. 

devName = '/dev/ttyUSB0'; #change to port name that your serial device is connected to

#### **Testing **
Connect TX and RX of the serial cable while no bms is attached. 
In terminal, run sudo python /home/pi/chargery.py -t


**Special credit to nuno, Joe Elliot, [Craig, Steve_S, BarkingSpider, mariovanwyk1, cass3825 & others](https://diysolarforum.com/threads/chargery-bms-communications.5905/)

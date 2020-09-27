#!/bin/bash
sudo cp chargery.py /home/pi
sudo cp chargery.log /home/pi
sudo cp chargery.service /usr/lib/systemd/system
sudo chmod 644 /usr/lib/systemd/system/chargery.service
sudo systemctl daemon-reload
sudo systemctl chargery.service
sudo systemctl start chargery.service
# Emergency button for the 3D printer (via RPi) 


use an endstop with soldered wires to help with interferences. last thing you need is fake emergency stops :D

![screenshot](button.png)

Connected to GPIO 18

GPIO 21 is connected to the RESET of the printer board.

##running as service service 

`chmod +x emergency_stop.py`

create file `/lib/systemd/system/emergency_stop.service` with:

```
[Unit]
Description=EmergencyStop
After=syslog.target

[Service]
ExecStart=/home/pi/emergency_stop.py service
Restart=always

[Install]
WantedBy=multi-user.target
```

then execute

```
systemctl daemon-reload 
systemctl enable emergency_stop.service
```

## other options

- run from command line (called from octoprint system menu)
`sudo /home/pi/emergency_stop.py run`

- reset the printer board only
`sudo /home/pi/emergency_stop.py reset`


Update: an arduino nano (using a funduino - chinese dirt cheap clone :D ) is now connected to the RPi via i2c to provide additional functionality: LED blinking for Wifi and Power status, as well as reading the resistor value of the smart hotend.

TODO:  change to bidirectional i2c (need level shifting)



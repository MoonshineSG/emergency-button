# Emergency button for the 3D printer (via RPi) 


![screenshot](schema.png)

use shielded cable for the button. this, together with the capacitor will help with interferences. last thing you need is fake emergency stops :D

![screenshot](button.png)

- GPIO 2 connects via a simple wire to the RESET pin of the printer board

- GPIO 24 is connectd to a replay that swithces on/off the 24V power for the printer

##running as service service 

`chmod +x emergency_stop.py`

create file `/lib/systemd/system/emergency_stop.service` with:

```
[Unit]
Description=EmergencyStop
After=syslog.target

[Service]
ExecStart=/home/pi/emergency_stop.py
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
- restart service 
`sudo /home/pi/emergency_stop.py ke`

- run from command line (called from octoprint system menu)
`sudo /home/pi/emergency_stop.py run`

- reset the printer board only
`sudo /home/pi/emergency_stop.py reset`

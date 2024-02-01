# Python VU-AMS

> [!NOTE]  
> This script is unofficial. I'm not affiliated with the Vrije Universiteit Amsterdam.

The VU-AMS is a portable device for the recording of EKG, IKG, and Electrodermal Activity.

This script allows controlling the VU-AMS via Python while the device is connected to the computer using the [USB infrared serial communication interface cable](https://vu-ams.nl/product/amsiusb/).

## Requirements

- Windows computer (tested on Windows 10)
- Python 3 (tested on 3.10.11)
- Python package `pyserial`
- VU-DAMS software and the CDM_v2.10.00_WHQL_Certified driver (both available [here](https://vu-ams.nl/downloads/))

## Usage

This script can be used either via command line arguments as a stand-alone script, or by importing the `AmsDevice` class from vuams_serial.py from within another Python script.

### Command Line Usage

Demonstration:

[python_vuams_demonstration.webm](https://github.com/nixmo/python_vuams/assets/56759362/e2180eeb-5225-4d98-b11a-8c22064a94aa)

Command Line Arguments:

```
> python vuams_serial.py --help
usage: vuams_serial.py [-h] [--port PORT]
                       (--device-present | --label | --status | --status-integer | --sync-time | --start-recording | --stop-recording | --send-marker MARKER)

Interact with a VU-AMS device connected to the computer via the AMS USB infared bridge.

options:
  -h, --help            show this help message and exit
  --port PORT           Set a specific port (e.g. COM5). If not set, port will be
                        determined automatically
  --device-present      Check if device is present
  --label               Get device label (serial number)
  --status              Get device status
  --status-integer      Get device status as an integer
  --sync-time           Set device time to system time
  --start-recording     Start recording
  --stop-recording      Stop recording
  --send-marker MARKER  Send marker MARKER
```

### Python usage

Example usage from within another Python script:

```python
from vuams_serial import AmsDevice

# initialize device instance
port = AmsDevice.find_device_port()  # get port automatically
device = AmsDevice(port)

# connect
device.connect()

# check if device is present
device_present = device.is_device_present()
print(f'{port},{device_present}')

# get device label (serial number)
device_label = device.get_device_label()
print(f'{port},{device_label}')

# get device status as human readable string
status_string = device.get_device_status(string=True)
print(f'{port},{status_string}')

# get device status as integer
status_integer = device.get_device_status()
print(f'{port},{status_integer}')

# set device time to computer time
device.sync_time()

# start recording
device.start_recording()

# send marker
device.send_marker(1)

# stop recording
device.stop_recording()

# disconnect
device.disconnect()
```

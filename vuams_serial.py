"""
Script Name: vuams_serial.py
Description: This script facilitates communication with a VU-AMS device via USB infrared bridge, allowing for operations such as checking device presence, syncing time, starting/stopping recording, and sending markers. It utilizes the pySerial library for serial communication and supports command-line interaction for ease of use.
Author: nixmo (nixmo@posteo.de)
Version: 1.0
Date: 2024-02-01
License: MIT License
GitHub: https://github.com/nixmo/python_vuams
Dependencies: pySerial (https://pyserial.readthedocs.io/en/latest/pyserial.html)
Usage: Run this script with command-line arguments to interact with the VU-AMS device. Use '--help' to list all available options. Example: `python vuams_serial.py --port COM5 --status`. Alternatively, you can import the AmsDevice class from this script, initialize an instance of the device, and call the methods of the class directly. For examples see the readme on the github repository.
Note: This is an unofficial script not supported by the Vrije Universiteit Amsterdam. Ensure the AMS device is connected via the USB infrared bridge and the VU-DAMS software and the CDM_v2.10.00_WHQL_Certified driver are installed before running this script (https://vu-ams.nl/downloads/).
"""

import serial
from serial.tools import list_ports
import time
import zlib
import datetime
import argparse
from sys import exit

class AmsDevice:
    status_labels = {
        1: "No Memory",
        2: "Close Cover",
        3: "Idle",
        4: "Recording",
        5: "Memory Full",
        6: "Battery Low"
    }

    def __init__(self, port_name, baudrate=38400, bytesize=8, stopbits=1, parity='N', timeout=0, write_timeout=0):
        self.isConnected = False
        self.serialPort = None
        self.port_name = port_name
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.stopbits = stopbits
        self.parity = parity
        self.timeout = timeout
        self.write_timeout = write_timeout

    @staticmethod
    def find_device_port():
        ports = list_ports.comports()
        for port in ports:
            try:
                # pyserial represents vendor and product id in decimal by default - we convert to hexadecimal to follow convention used by node js serialport package
                vid_hex = f"{port.vid:04X}"
                pid_hex = f"{port.pid:04X}"

                if (port.description == f"USB Serial Port ({port.device})" and
                    # port.vid == 1027 and
                    # port.pid == 24577 and
                    vid_hex == "0403" and
                    pid_hex == "6001" and
                    port.manufacturer == "FTDI"):
                    return port.device
            except:
                pass
        return None

    def connect(self):
        try:
            self.serialPort = serial.Serial(
                port=self.port_name,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                stopbits=self.stopbits,
                parity=self.parity,
                timeout=self.timeout,
                write_timeout=self.write_timeout
            )
        except serial.serialutil.SerialException as e:
            print(f"Error occured while trying to open port {self.port_name}: {e}")
            return False

        r = self.is_device_present()
        if r:
            self.isConnected = True
            return True
        self.disconnect()
        return False

    def disconnect(self):
        if self.serialPort:
            self.serialPort.close()
        self.isConnected = False

    def send_packet(self, packet):
        # Convert packet to bytes
        byte_packet = bytearray([(p + 256) % 256 for p in packet])
        
        # Calculate CRC32
        crc = zlib.crc32(byte_packet) & 0xFFFFFFFF
        crc_bytes = bytearray([(crc >> (8 * i)) & 0xFF for i in range(4)])  # big-endian order
        
        # Append CRC bytes to the packet
        byte_packet.extend(crc_bytes)
        
        try:
            self.serialPort.write(byte_packet)
        except serial.SerialException as e:
            print(f"Serial port exception: {e}")
        except Exception as e:
            print(f"Exception occurred while sending packet: {e}")
    
    def receive_packet(self, timeout=3):
        end_time = time.time() + timeout  # Calculate when we should stop (current time + timeout seconds)
        data_received = None
        try:
            while True:
                if time.time() > end_time:
                    print("Timeout exceeded, exiting receive mode...")
                    break

                if self.serialPort.in_waiting > 0:
                    data = self.serialPort.read(self.serialPort.in_waiting)
                    data_received = data
                    break

                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Exiting receive mode...")
        finally:
            return data_received
    
    # checks if the VU-AMS device is present on this port by looking for a specific, hardcoded response via serial
    def is_device_present(self):
        try:
            data = self.get_parameter_from_device(200)
            if data and isinstance(data, (bytes, bytearray)):
                data_list = [int(byte) for byte in data]
                if data_list[:8] == [12, 0, 129, 200, 65, 77, 83, 50]:
                    return True
        except:
            return False
    
    def start_recording(self):
        self.send_command(5)

    def stop_recording(self):
        self.send_command(6)
    
    def get_device_status(self, string=False):
        data = self.get_parameter_from_device(100)
        if data is None:
            return None
        data_list = [int(byte) for byte in data]
        status = data_list[4]
        if not string:
            return status
        else:
            return self.status_labels[status]

    def get_device_label(self):
        data = self.get_parameter_from_device(202)
        if data is None:
            return None
        data_list = [int(byte) for byte in data]
        device_label = str(data_list[4])
        return device_label

    def get_parameter_from_device(self, par):
        # get_parameter_from_device(100) - status
        # get_parameter_from_device(109) - battery voltage in unknown units
        # get_parameter_from_device(200) - will return 8 specific bytes if device is present
        # get_parameter_from_device(201) - version
        # get_parameter_from_device(202) - "device label" (serial number)
        # There are more. I have not tested all.

        b = [8, 0, 1, par]
        self.send_packet(b)
        r = self.receive_packet()
        return r
        
    def sync_time(self):
        dt = datetime.datetime.now()
        isdst = int(time.localtime().tm_isdst)
        
        time_array = [
            dt.year - 1900,
            dt.month - 1,  # device expects java convention month numbering (0-11)
            dt.day,
            dt.hour,
            dt.minute,
            dt.second,
            isdst,
            dt.weekday() + 1
        ]

        # Prepend the protocol specific header information
        b = [8 + len(time_array), 0, 6, 0] + time_array

        # Send the packet with the time information
        self.send_packet(b)

        # Receive the response packet
        r = self.receive_packet()
        if r is not None:
            return True
        return False

    def send_command(self, com):
        b = [8, 0, 11, com]
        self.send_packet(b)
        r = self.receive_packet()
        if r:
            return True
        else:
            return False
    
    def send_marker(self, s):
        s = str(s)
        # Truncate input to 32 characters and replace non-ASCII characters
        s = s[:32].encode('ascii', 'replace').decode()
        s = s.replace('?', '_')  # Replace the replacement character with underscore

        b = [0] * 52  # Initialize an array of 52 zeros

        # Set specific positions to certain values
        b[0] = 56
        b[2] = 14
        b[4] = 3
        b[6] = 48
        b[8] = 17
        b[9] = 17
        b[10] = 17
        b[11] = 17
        b[12] = 1
        b[16] = 4

        # Fill with ASCII values of the characters in the string
        for j in range(20, 20 + len(s)):
            b[j] = ord(s[j - 20])  # Use ord to get ASCII value of character

        # Send the packet
        self.send_packet(b)


def main():
    parser = argparse.ArgumentParser(description='Interact with a VU-AMS device connected to the computer via the AMS USB infared bridge.')
    parser.add_argument('--port', help='Set a specific port (e.g. COM5). If not set, port will be determined automatically', type=str)
    exclusive_group = parser.add_mutually_exclusive_group(required=True)
    exclusive_group.add_argument('--device-present', action='store_true', help='Check if device is present')
    exclusive_group.add_argument('--label', action='store_true', help='Get device label (serial number)')
    exclusive_group.add_argument('--status', action='store_true', help='Get device status')
    exclusive_group.add_argument('--status-integer', action='store_true', help='Get device status as an integer')
    exclusive_group.add_argument('--sync-time', action='store_true', help='Set device time to system time')
    exclusive_group.add_argument('--start-recording', action='store_true', help='Start recording')
    exclusive_group.add_argument('--stop-recording', action='store_true', help='Stop recording')
    exclusive_group.add_argument('--send-marker', metavar='MARKER', help='Send marker MARKER', type=str)

    args = parser.parse_args()

    # If port is not specified, find it automatically
    port = args.port if args.port else AmsDevice.find_device_port()
    if not port:
        print("Could not find a compatible device port automatically.")
        exit(1)

    # Instantiate the device with the selected port
    device = AmsDevice(port)
    if device.connect():
        try:
            if args.device_present:
                device_present = device.is_device_present()
                print(f'{port},{device_present}')
            elif args.label:
                device_label = device.get_device_label()
                print(f'{port},{device_label}')
            elif args.status:
                status = device.get_device_status(True)
                print(f'{port},{status}')
            elif args.status_integer:
                status = device.get_device_status()
                print(f'{port},{status}')
            elif args.sync_time:
                device.sync_time()
            elif args.start_recording:
                device.start_recording()
            elif args.stop_recording:
                device.stop_recording()
            elif args.send_marker:
                device.send_marker(args.send_marker)
        finally:
            device.disconnect()
            exit(0)
    else:
        print("Failed to connect to the device.")
        exit(1)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# Copyright © 2024 Augusto Fraga Giachero <afg@augustofg.net>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the “Software”), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import serial
import argparse

class FT817Cmd:
    def __init__(self, serialport, stopbits, baudrate):
        self.sp = serial.Serial(serialport, stopbits=stopbits, baudrate=baudrate, timeout=None)
    def _read_eeprom_cmd(self, address):
        cmd = bytes([
            (address & 0xFF00) >> 8,
            (address & 0x00FF),
            0,
            0,
            0xBB
        ])
        self.sp.write(cmd)
        return self.sp.read(2)

    def read_eeprom(self, address, size):
        bytes_read = 0
        data = bytearray([])
        while bytes_read < size:
            data.extend(self._read_eeprom_cmd(address + bytes_read))
            bytes_read = bytes_read + 2
        return data[:size]

    def _write_eeprom_cmd(self, address, data_arr):
        if len(data_arr) != 2:
            raise ValueError("data_arr should have exactly 2 bytes")
        cmd = bytes([
            (address & 0xFF00) >> 8,
            (address & 0x00FF),
            data_arr[0],
            data_arr[1],
            0xBC
        ])
        self.sp.write(cmd)
        self.sp.read(1)

    def write_eeprom(self, address, data):
        bytes_written = 0
        while bytes_written < len(data) - 1:
            self._write_eeprom_cmd(address + bytes_written, data[bytes_written:bytes_written+2])
            bytes_written = bytes_written + 2

        # If still one byte left to write, do a read-modify-write operation
        if bytes_written < len(data):
            data_read = self._read_eeprom_cmd(address + bytes_written)
            data_to_write = bytes([data[bytes_written], data_read[1]])
            self._write_eeprom_cmd(address + bytes_written, data_to_write)



parser = argparse.ArgumentParser(
                    description="Utility to read and write the EEPROM contents of the Yaesu FT817/FT817nd radio via CAT interface",
                    epilog="Use with caution!")

parser.add_argument("-p", "--serial-port", help="Serial port file", required=True, type=str)
parser.add_argument("-b", "--baud-rate", help="Serial port baud rate [default=4800]", required=False, type=int, choices=[4800, 9600, 38400], default=4800)
op_group = parser.add_mutually_exclusive_group(required=True)
op_group.add_argument("-r", "--read-to", help="Read the EEPROM and save to file", type=str)
op_group.add_argument("-w", "--write-from", help="Read from file and write to EEPROM", type=str)

args = parser.parse_args()

ft = FT817Cmd(args.serial_port, stopbits=serial.STOPBITS_TWO, baudrate=args.baud_rate)
ee_size = 0x1925

if args.read_to != None:
    data = ft.read_eeprom(0x0000, ee_size)
    with open(args.read_to, "wb") as f:
        f.write(data)

if args.write_from != None:
    print("Before writing to the EEPROM, make a backup first!")
    bytes_to_write = ee_size
    with open(args.write_from, "rb") as f:
        data = f.read()
        data_size = len(data)
        if data_size < ee_size:
            print("Warning: binary file smaller than expected size (expected: {} bytes, read: {} bytes)".format(ee_size, data_size), file=sys.stderr)
            bytes_to_write = data_size
        elif data_size > ee_size:
            print("Warning: binary file larger than expected size (expected: {} bytes, read: {} bytes)".format(ee_size, data_size), file=sys.stderr)
            bytes_to_write = ee_size
    ans = input("Are you sure you want to proceed writing to the EEPROM? [Y/n] ")
    if ans == "Y":
        ft.write_eeprom(0x0000, data[0:bytes_to_write])
    else:
        print("Aborting...")

#!/usr/bin/python
from PCF8583 import *
import argparse
import time

ESC = "\033["
YELLOW = ESC+"33m"
RED = ESC+"31m"
RESET = ESC+"0m"
SAVE = ESC+"s"
LOAD = ESC+"u"
HOME = ESC + "f"
HIGHLIGHT = ESC+"7m"
CLEAR_LINE = ESC+"2K"
CLEAR_SCREEN = ESC+"2J"


def monitor(bus, addr):
    print(CLEAR_SCREEN + HOME)
    pcf = PCF8583(bus, addr)
    mode = pcf.get_mode()
    if mode == MODE_EVENT_COUNTER:
        count = pcf.get_count()
        return f"MODE: {mode2string(mode)}\n\n" \
               f"COUNT: {count}\n\n"

    elif mode == MODE_CLOCK_50HZ or mode == MODE_CLOCK_32KHZ:
        time = pcf.get_datetime()
        alarm_control_enabled = pcf.get_alarm_control()
        alarm_time = pcf.get_alarm_time()
        alarm_mode, interrupt = pcf.get_alarm_mode()
        return f"MODE: {mode2string(mode)}\tALARM CONTROL: {alarm_control_enabled}\t" \
               f"ALARM MODE: {alarm_mode2string(alarm_mode)}\tINTERRUPT: {interrupt}\n\n" \
               f"DATE: {time.strftime('%d.%m.%Y')}\tTIME: {time.strftime('%H:%M:%S')}\n" \
               f"ALARM: {alarm_time.strftime('%H:%M:%S')}\n\n"
    else:
        return "FAULTY MODE!"


def hex(string):
    return int(string, 16)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor for a PCF8583.")
    parser.add_argument("-a", "--addr", help="The I2C address of the PCF8583.", type=hex, metavar="ADDR", required=True)
    parser.add_argument("-b", "--bus", help="Choose the SMBus number.", type=int, default=1)
    args = parser.parse_args()

    old_string = ""
    while True:
        print(monitor(args.bus, args.addr))
        time.sleep(1)

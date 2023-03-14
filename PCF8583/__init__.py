# PCF8583 RTC and Event Counter Library for Arduino
# Copyright (C) 2013-2018 by Xose Pérez <xose dot perez at gmail dot com>
# Translated to Python in 2019 by Tibor Völcker <tiborvoelcker@hotmail.de>
# The PCF8583 library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# The PCF8583 library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
# You should have received a copy of the GNU Lesser General Public License
# along with the PCF8583 library.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime, time

from smbus2 import SMBus

from PCF8583.constants import *


def bcd2byte(value):
    if value >> 4 > 9 or value & 0x0F > 9:
        raise ValueError(f"invalid value for byte convertion: {hex(value)}")
    return ((value >> 4) * 10) + (value & 0x0F)


def byte2bcd(value):
    if value >= 100:
        raise ValueError(f"invalid value for bcd convertion: {value}")
    return ((value // 10) << 4) + (value % 10)


def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))


def mode2string(mode):
    if mode == MODE_CLOCK_32KHZ:
        return "CLOCK (32 kHz)"
    elif mode == MODE_CLOCK_50HZ:
        return "CLOCK (50 Hz)"
    elif mode == MODE_EVENT_COUNTER:
        return "EVENT COUNTER"
    else:
        return False


def alarm_mode2string(mode):
    if mode == ALARM_MODE_NO_ALARM:
        return "NO ALARM"
    if mode == ALARM_MODE_DAILY_ALARM:
        return "DAILY ALARM"
    if mode == ALARM_MODE_DATED_ALARM:
        return "DATED ALARM"
    if mode == ALARM_MODE_WEEKDAY_ALARM:
        return "WEEKDAY ALARM"
    else:
        return False


class PCF8583:
    def __init__(self, bus_number=1, address=0x50):
        self._bus = bus_number
        self._addr = address

    def __start(self):
        with SMBus(self._bus) as bus:
            control = bus.read_byte_data(self._addr, LOCATION_CONTROL)
            bus.write_byte_data(self._addr, LOCATION_CONTROL, control & 0x7F)

    def __stop(self):
        with SMBus(self._bus) as bus:
            control = bus.read_byte_data(self._addr, LOCATION_CONTROL)
            bus.write_byte_data(self._addr, LOCATION_CONTROL, control | 0x80)

    def __get_register(self, register):
        with SMBus(self._bus) as bus:
            value = bus.read_byte_data(self._addr, register)
        return value

    def __set_register(self, register, value):
        with SMBus(self._bus) as bus:
            bus.write_byte_data(self._addr, register, value)

    def reset(self):
        with SMBus(self._bus) as bus:
            bus.write_i2c_block_data(
                self._addr,
                LOCATION_CONTROL,
                [
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x01,
                    0x01,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x01,
                    0x01,
                    0x00,
                ],
            )
            for i in range(1, 15):
                bus.write_i2c_block_data(self._addr, LOCATION_CONTROL + 16 * i, [0x00] * 16)

    def set_mode(self, mode):
        control = self.__get_register(LOCATION_CONTROL)
        control = (control & ~MODE_TEST) | (mode & MODE_TEST)
        self.__set_register(LOCATION_CONTROL, control)

    def get_mode(self):
        return self.__get_register(LOCATION_CONTROL) & MODE_TEST

    def get_second(self):
        return bcd2byte(self.__get_register(LOCATION_SECONDS))

    def get_minute(self):
        return bcd2byte(self.__get_register(LOCATION_MINUTES))

    def get_hour(self):
        return bcd2byte(self.__get_register(LOCATION_HOURS))

    def get_timestamp(self):
        total = self.get_hour()
        total = total * 60 + self.get_minute()
        total = total * 60 + self.get_second()
        return total

    def set_time(self, hour, min, sec):
        sec = byte2bcd(constrain(sec, 0, 59))
        min = byte2bcd(constrain(min, 0, 59))
        hour = byte2bcd(constrain(hour, 0, 23))

        self.__stop()
        with SMBus(self._bus) as bus:
            bus.write_i2c_block_data(self._addr, LOCATION_SECONDS, [sec, min, hour])
        self.__start()

    def get_day(self):
        return bcd2byte(self.__get_register(LOCATION_DAY) & 0x3F)

    def get_month(self):
        return bcd2byte(self.__get_register(LOCATION_MONTH) & 0x1F)

    def get_year(self):
        year = self.__get_register(LOCATION_DAY) >> 6
        last = self.__get_register(LOCATION_LAST_YEAR)
        offset = self.__get_register(LOCATION_OFFSET_YEAR)

        if not last == year:
            if last > year:
                self.__set_register(LOCATION_OFFSET_YEAR, offset + 4)
            self.__set_register(LOCATION_LAST_YEAR, year)

        return BASE_YEAR + offset + year

    def get_weekday(self):
        return self.__get_register(LOCATION_MONTH) >> 5

    def set_date(self, day, month, year, weekday=0):
        year -= BASE_YEAR
        offset = year & 0xFC
        year -= offset

        day = byte2bcd(constrain(day, 1, 31))
        month = byte2bcd(constrain(month, 1, 12))
        weekday = byte2bcd(constrain(weekday, 0, 6))

        self.__stop()
        with SMBus(self._bus) as bus:
            bus.write_i2c_block_data(
                self._addr, LOCATION_DAY, [day | (year << 6), month | (weekday << 5)]
            )
            bus.write_i2c_block_data(self._addr, LOCATION_OFFSET_YEAR, [offset, year])
        self.__start()

    def set_date_time(self, hour, min, sec, day, month, year, weekday=0):
        self.set_time(hour, min, sec)
        self.set_date(day, month, year, weekday)

    def set_today(self):
        t = datetime.today()
        self.set_date_time(t.hour, t.minute, t.second, t.day, t.month, t.year, t.weekday())

    def get_datetime(self):
        return datetime(
            self.get_year(),
            self.get_month(),
            self.get_day(),
            self.get_hour(),
            self.get_minute(),
            self.get_second(),
        )

    def set_alarm(self, hour, min, sec):
        sec = byte2bcd(constrain(sec, 0, 59))
        min = byte2bcd(constrain(min, 0, 59))
        hour = byte2bcd(constrain(hour, 0, 23))

        with SMBus(self._bus) as bus:
            bus.write_i2c_block_data(self._addr, LOCATION_ALARM_SECONDS, [sec, min, hour])

    def get_alarm_time(self):
        with SMBus(self._bus) as bus:
            alarm = bus.read_i2c_block_data(self._addr, LOCATION_ALARM_SECONDS, 3)
            return time(byte2bcd(alarm[2]), byte2bcd(alarm[1]), byte2bcd(alarm[0]))

    def enable_alarm_control(self, bool):
        if bool:
            control = self.__get_register(LOCATION_CONTROL)
            self.__set_register(LOCATION_CONTROL, control | 0x04)
        else:
            control = self.__get_register(LOCATION_CONTROL)
            self.__set_register(LOCATION_CONTROL, control & 0xFB)

    def get_alarm_control(self):
        control = self.__get_register(LOCATION_CONTROL)
        return control & 0x04 == 0x04

    def set_alarm_mode(self, mode, interrupt=True):
        if interrupt:
            mode = (mode & MODE_TEST) | 0x80
        else:
            mode = (mode & MODE_TEST) & 0x7F
        control = self.__get_register(LOCATION_ALARM_CONTROL)
        control = (control & ~0xB0) | mode
        self.__set_register(LOCATION_ALARM_CONTROL, control)

    def get_alarm_mode(self):
        control = self.__get_register(LOCATION_ALARM_CONTROL)
        mode = control & MODE_TEST
        interrupt = control & 0x80
        return mode, interrupt == 0x80

    def clear_interrupt(self):
        control = self.__get_register(LOCATION_CONTROL)
        self.__set_register(LOCATION_CONTROL, control & 0xFC)

    def set_count(self, count):
        count1 = byte2bcd(count % 100)
        count2 = byte2bcd((count // 100) % 100)
        count3 = byte2bcd((count // 10000) % 100)

        self.__stop()
        with SMBus(self._bus) as bus:
            bus.write_i2c_block_data(self._addr, LOCATION_COUNTER, [count1, count2, count3])
        self.__start()

    def get_count(self):
        with SMBus(self._bus) as bus:
            count = bus.read_i2c_block_data(self._addr, LOCATION_COUNTER, 3)
        return bcd2byte(count[0]) + bcd2byte(count[1]) * 100 + bcd2byte(count[2]) * 100000

    def get_ram(self):
        with SMBus(self._bus) as bus:
            ram = []
            length = 0xFF - LOCATION_RAM
            for i in range(length // 32):
                ram += bus.read_i2c_block_data(self._addr, LOCATION_RAM + 32 * i, 32)
        return "".join(chr(i) for i in ram)

    def set_ram(self, string):
        length = 0xFF - LOCATION_RAM
        if len(string) > length:
            return False
        else:
            string = string.ljust(length)
            string = [ord(i) for i in string]
            i = 0
            with SMBus(self._bus) as bus:
                while len(string) > 0:
                    bus.write_i2c_block_data(self._addr, LOCATION_RAM + 32 * i, string[:32])
                    del string[:32]
                    i += 1


# ToDo: count event steps and count event alarm
# ToDo: timer and timer alarm

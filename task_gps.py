## @file task_gps.py
#  This file implements a cotask which reads a stream of NEMA blather from a GPS
#  module, parses it, and makes the results available to other cotasks.
#
#  Originally for a uBlox GPS - Tested, works
#  Trying with an old, banged up Fastrax UP501 - seems to work
# 
#  @author JR Ridgely
#  @date   2020-Apr-01 Original file, and I'm not kidding
#  @date   2022-Dec-27 Modified to use asyncio
#  @date   2022-Dec-30 Cleaned up and put things into a class
#  @date   2023-Nov-20 Modifying to not use SD card task and try other GPSes
#  @date   2023-Dec-08 Changed some pins for wave radar
#  @copyright (c) 2020-2-23 by JR Ridgely and released under the GNU Public
#          License V3.

from machine import Pin, UART, SDCard
from micropython import const
import uasyncio as asyncio
import as_GPS.as_GPS as as_GPS


## The local time offset, which may be standard or daylight time. It's negative
#  for longitudes West of Greenwich, such as those in North America.
LOCAL_OFFSET = -8

## The UART number for the GPS, usually 2 for an ESP32 device
GPS_UART_NUM = 2

## The baud rate for the GPS, 57600 for LocoSys, 9600 for uBlox Neo-6M-0
GPS_UART_BAUD = 9600

## The number of the pin used for the UART's TXD line (ESP32 out, GPS in)
GPS_TXD_PIN = 14

## The number of the pin used for the UART's RXD line (GPS out, ESP32 in)
GPS_RXD_PIN = 32

## The number of the GPIO pin used to turn the GPS on and off with a MOSFET
GPS_POWER_PIN = 15

## Add a new way to return latitude and longitude: signed decimal degrees which
#  work for calculations of distance and bearing to a mark
SDD = const(100)


## This extension of the AS_GPS class adds the ability to compute the range
#  and bearing to a mark as well as miscellaneous refinements.
class Boatsie_GPS(as_GPS.AS_GPS):

    ## Create a GPS task by instantiating the parent object and adding some
    #  extra data for the mark to which we're trying to go.
    #  @param uart A serial port (UART) to which the GPS module is connected
    def __init__(self, uart, power_pin_number=None):

        # Set up the parent class object
        super().__init__(asyncio.StreamReader(uart), local_offset=LOCAL_OFFSET)
                         # , fix_cb=gps_callback)

        ## A saved copy of the UART can be used to turn the UART off
        self._uart = uart

        ## The name of the mark, or None if we don't have a destination
        self.mark_name = None

        ## The pin used to control the GPS's power, or None if the GPS is
        #  always on and the power pin isn't used
        if power_pin_number is not None:
            self.power_pin = Pin(power_pin_number, Pin.OUT)
        else:
            self.power_pin = None


    ## Turn on the GPS module by setting the power control pin high. This
    #  assumes that there's an N-channel MOSFET connecting the ground of the
    #  GPS module to system ground. If no power pin has been specified, this
    #  method does nothing.
    def on(self):
        if self.power_pin is not None:
            self.power_pin.value(1)


    ## Turn off the GPS module by setting the power control pin high. This
    #  assumes that there's an N-channel MOSFET connecting the ground of the
    #  GPS module to system ground.  If no power pin has been specified, this
    #  method does nothing.
    def off(self):
        if self.power_pin is not None:
            self.power_pin.value(0)


    ## Turn off the UART to save power
    def uart_off(self):
        self._uart.deinit()


    ## This overridden method adds the Signed Decimal Degrees format for
    #  latitude. Code for the other formats is copied from the parent class.
    #  @param coord_format The format for coordinates, default a signed number
    def latitude(self, coord_format=SDD):
        if coord_format == SDD:
            signed_degrees = self._latitude[0] + (self._latitude[1] / 60)
            if self._latitude[2] == 'S':
                signed_degrees = -signed_degrees
            return signed_degrees
        elif coord_format == as_GPS.DD:
            decimal_degrees = self._latitude[0] + (self._latitude[1] / 60)
            return [decimal_degrees, self._latitude[2]]
        elif coord_format == as_GPS.DMS:
            mins = int(self._latitude[1])
            seconds = round((self._latitude[1] - mins) * 60)
            return [self._latitude[0], mins, seconds, self._latitude[2]]
        elif coord_format == as_GPS.DM:
            return self._latitude
        raise ValueError('Unknown latitude format.')


    ## This overridden method adds the Signed Decimal Degrees format for
    #  longitude. Code for the other formats is copied from the parent class.
    #  @param coord_format The format for coordinates, default a signed number
    def longitude(self, coord_format=SDD):
        if coord_format == SDD:
            signed_degrees = self._longitude[0] + (self._longitude[1] / 60)
            if self._longitude[2] == 'W':
                signed_degrees = -signed_degrees
            return signed_degrees
        elif coord_format == as_GPS.DD:
            decimal_degrees = self._longitude[0] + (self._longitude[1] / 60)
            return [decimal_degrees, self._longitude[2]]
        elif coord_format == as_GPS.DMS:
            mins = int(self._longitude[1])
            seconds = round((self._longitude[1] - mins) * 60)
            return [self._longitude[0], mins, seconds, self._longitude[2]]
        elif coord_format == as_GPS.DM:
            return self._longitude
        raise ValueError('Unknown longitude format.')


## The one and only GPS object, which will be instantiated when the task is
#  started
gps = None


## Task function which turns on the GPS module, sets up the NMEA data parser,
#  then does whatever is needed to keep them running (probably not much).
async def gps_task_function():
    global gps

    # Set up the GPS power pin and turn on the GPS

    # The UART for the Wave Radar GPS is Serial1 on Arduino, UART 2 on mPy?!
    uart = UART(GPS_UART_NUM, GPS_UART_BAUD, tx=GPS_TXD_PIN, rx=GPS_RXD_PIN)

    # Instantiate asynchronous GPS data processor
    gps = Boatsie_GPS(uart, GPS_POWER_PIN)
    gps.on()

    while True:
#         print(f"{gps.date_string()}, {gps.time_string()}, {gps.speed():.1f} kt")
        print(f"{gps.local_time}")

        await asyncio.sleep_ms(5_000)


## Function to turn on the GPS module. This is usually done when we need to
#  update the time in the RTC (real-time clock).
def gps_on():
    gps.on()


## Function to turn off the GPS module. This is likely to be done after a time
#  fix has been received and applied to the RTC.
def gps_off():
    gps.off()


## Function to get the most recently measured time.
#  @returns The time as a tuple of hours, minutes, and decimal seconds
def get_time():
    return (gps.local_time)


#===============================================================================

if __name__ == "__main__":

    async def main():
        """!
        Get the task functions running, then twiddle thumbs ad infinitum.
        """
        asyncio.create_task(gps_task_function())

        while True:
            await asyncio.sleep_ms(60_000)

    print("Beginning GPS parser test; Ctrl-C to exit.")
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("Ctrl-C. ", end='')

    gps.off()
    asyncio.new_event_loop()
    print("Test finished.")


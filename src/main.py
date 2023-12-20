## @file main.py
#  This is the main file for the wave radar project. It gets several tasks
#  running using the MicroPython uasyncio framework which is documented at:
#  @c https://github.com/peterhinch/micropython-async/tree/master/v3/docs
#
#  @author JR Ridgely
#  @date   2023-Dec-08 Original file
#  @copyright (c) 2020-2-23 by JR Ridgely and released under the GNU Public
#          License V3.

import uasyncio as asyncio
from machine import Pin, UART, RTC
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


gps_power_pin = Pin(GPS_POWER_PIN, Pin.OUT)


## Update the Real-Time Clock with data from the GPS.
#  The GPS must be turned on, we must wait for a good GPS fix, then the
#  date and time may be received and put into the RTC.
#  To keep things simple, this system is only accurate to within 2 ~ 3 seconds.
#  @param rtc The Real Time Clock object in which date and time are updated
#  @param gps The asynchronous GPS object which gives us the time
async def update_RTC(rtc, gps, power_pin):

    print("GPS on...", end='')

    # First turn on the GPS and wait for a good reading
    power_pin.value(1)
    await gps.data_received(position=True, date=True)

    date = gps.date
    time = gps.local_time

    # Year, month, day; hour, minute, second; microseconds, timezone-info
    rtc.datetime((2000 + date[2], date[1], date[0], 0,
                 time[0], time[1], time[2],
                 0))

    power_pin.value(0)

    print(f"RTC set to {rtc.datetime()}")
    

## Task function which uses the GPS module and RTC (Real-Time Clock) in the
#  microcontroller to keep reasonably accurate time.
async def clock_task_function():

    # The UART for the Wave Radar GPS is Serial1 on Arduino, UART 2 on mPy?!
    uart = UART(GPS_UART_NUM, GPS_UART_BAUD, tx=GPS_TXD_PIN, rx=GPS_RXD_PIN)

    # Create the GPS object which gets time in unmodified GMT
    gps = as_GPS.AS_GPS(asyncio.StreamReader(uart), local_offset=LOCAL_OFFSET)

    # Now set up the Real-Time Clock object; we'll put a sensible date and time
    # into it when the GPS gets going
    rtc = RTC()

    await update_RTC(rtc, gps, gps_power_pin)

    while True:
#         print(f"{gps.date_string()}, {gps.time_string()}, {gps.speed():.1f} kt")
#         print(gps.date, gps.local_time)

        # If the time has crossed local noon, meaning we've gone from AM to PM,
        # load the RTC with updated time from the GPS. This should prevent RTC
        # drift (which can be severe) from causing bad time readings
        if False:
            await update_RTC(rtc, gps, gps_power_pin)
        
        year, month, day, dow, hour, mnt, sec, frac = rtc.datetime()
        print(f"{year}-{month:02d}-{day:02d} {hour:02d}:{mnt:02d}:{sec:02d}")

        await asyncio.sleep_ms(5_000)



#-------------------------------------------------------------------------------

## Get the task functions running, then twiddle thumbs ad infinitum.
async def main():
    asyncio.create_task(clock_task_function())

    while True:
        await asyncio.sleep_ms(60_000)


print("Beginning GPS parser test; Ctrl-C to exit.")
try:
    asyncio.run(main())

except KeyboardInterrupt:
    print("Ctrl-C. ", end='')

gps_power_pin.value(0)
asyncio.new_event_loop()
print("Test finished.")




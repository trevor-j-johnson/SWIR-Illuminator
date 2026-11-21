#setting up the I/0
from machine import Pin, PWM
from display.display_engine import DisplayEngine
from camera_view import cam_view
import profiles
import asyncio

led_red = PWM(16, freq=100, duty_u16=0)
led_blue = PWM(17, freq=100, duty_u16=0)
led_yellow = PWM(18, freq=100, duty_u16=0)
led_green = PWM(19, freq=100, duty_u16=0)

def all_leds_off():
    led_red.duty_u16(0)
    led_blue.duty_u16(0)
    led_yellow.duty_u16(0)
    led_green.duty_u16(0)

def led_duty(current_duty):
    duty_percent = (current_duty +25)
    if duty_percent > 100:
        duty_percent = 25
    return duty_percent

def convert_duty(duty):
    return int((duty/100)*65535)

display = DisplayEngine(
    leds_off_callback=all_leds_off,
    red_led_pwm_callback=led_duty,
    blue_led_pwm_callback=led_duty,
    yellow_led_pwm_callback=led_duty,
    green_led_pwm_callback=led_duty,
    cam_view_callback=cam_view,
    cam_view_kwargs={"num_cams": 3},
    profiles=profiles.functions
)

async def sync_leds():
    while True:
        if display.running_profile is None:
            if display.red_led_on:
                led_red.duty_u16(convert_duty(display.red_duty_percent))
            else:
                led_red.duty_u16(0)

            if display.blue_led_on:
                led_blue.duty_u16(convert_duty(display.blue_duty_percent))
            else:
                led_blue.duty_u16(0)
            
            if display.yellow_led_on:
                led_yellow.duty_u16(convert_duty(display.yellow_duty_percent))
            else:
                led_yellow.duty_u16(0)

            if display.green_led_on:
                led_green.duty_u16(convert_duty(display.green_duty_percent))
            else:
                led_green.duty_u16(0)

        await asyncio.sleep_ms(0)

async def main():
    asyncio.create_task(display.run())
    await sync_leds()

asyncio.run(main())
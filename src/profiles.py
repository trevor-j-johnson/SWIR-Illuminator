import asyncio
import neopixel
from machine import Pin, PWM

# TODO: Make these asynchronous

# Neat trick to set compile-time conditionals
_EXTERNAL_LEDS = const(False)

async def cycle_color_leds():
    led_red = PWM(16, freq=100, duty_u16=0)
    led_blue = PWM(17, freq=100, duty_u16=0)
    led_yellow = PWM(18, freq=100, duty_u16=0)
    led_green = PWM(19, freq=100, duty_u16=0)
    leds = [led_red, led_blue, led_yellow, led_green]
    
    loops = 3
    delay_ms = 1000
    
    duty_off = 0
    duty_on = 65535

    try:
        for _ in range(loops):
            for i in range(len(leds)):
                leds[i % 4].duty_u16(duty_on)
                leds[(i+1) % 4].duty_u16(duty_off)
                leds[(i+2) % 4].duty_u16(duty_off)
                leds[(i+3) % 4].duty_u16(duty_off)
                
                await asyncio.sleep_ms(delay_ms)
    finally:
        for led in leds:
            led.duty_u16(0)

async def pulse_color_leds():
    led_red = PWM(16, freq=100, duty_u16=0)
    led_blue = PWM(17, freq=100, duty_u16=0)
    led_yellow = PWM(18, freq=100, duty_u16=0)
    led_green = PWM(19, freq=100, duty_u16=0)
    leds = [led_red, led_blue, led_yellow, led_green]
    
    loops = 3
    step_delay_ms = 5
    max_duty = 100

    try:
        for _ in range(loops):
            for i in range(max_duty + 1):
                duty_percent = i / max_duty
                duty = int(duty_percent*65535)
                
                for led in leds:
                    led.duty_u16(duty)

                await asyncio.sleep_ms(step_delay_ms)

            for i in range(max_duty, -1, -1):
                duty_percent = i / max_duty
                duty = int(duty_percent*65535)
                
                for led in leds:
                    led.duty_u16(duty)

                await asyncio.sleep_ms(step_delay_ms)
    finally:
        for led in leds:
            led.duty_u16(0)

async def cycle_neopixel():
    loops = 3
    steps = 25
    step_delay_ms = 20

    red = (255, 0, 0)
    yellow = (127, 127, 0)
    green = (0, 255, 0)
    cyan = (0, 127, 127)
    blue = (0, 0, 255)
    magenta = (127, 0, 127)
    colors = (red, yellow, green, cyan, blue, magenta)

    pixel = neopixel.NeoPixel(Pin(12), 1)

    try:
        for _ in range(loops):
            for r, g, b in colors:
                for i in range(steps + 1):
                    scale = i / steps
                    pixel.fill((int(r * scale), int(g * scale), int(b * scale)))
                    pixel.write()

                    await asyncio.sleep_ms(step_delay_ms)

                for i in range(steps, -1, -1):
                    scale = i / steps
                    pixel.fill((int(r * scale), int(g * scale), int(b * scale)))
                    pixel.write()

                    await asyncio.sleep_ms(step_delay_ms)
    finally:
        pixel.fill((0, 0, 0))
        pixel.write()

async def flashing_leds():
    loops = 3
    toggles = 20

    leds = [Pin(16, Pin.OUT, value=1), Pin(17, Pin.OUT, value=0)]
    delay_ms = (500, 100)

    try:
        for _ in range(loops):
            for time in delay_ms:
                for _ in range(toggles):
                    for led in leds:
                        led.toggle()
                    
                    await asyncio.sleep_ms(time)
    finally:
        for led in leds:
            led.off()

if _EXTERNAL_LEDS:
    functions = {
        "Pulse LEDs": pulse_color_leds,
        "Cycle LEDs": cycle_color_leds
    }
else:
    functions = {
        "Cycle NeoPixel": cycle_neopixel,
        "Flashing LEDs": flashing_leds
    }
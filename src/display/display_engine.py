from machine import Pin, SPI, I2C
from drivers.st7796 import ST7796
from drivers.gt911 import GT911
from display.display_ui import Display, Button
from time import sleep_ms
import asyncio

# TODO: Major - fix heap fragmentation issues

# Breakout board uses:
# 	Display:
# 		sck_pin = 2
# 		tx_pin = 3
#	 	rx_pin = 4    Not used
# 		cs_pin = 5    Active-low
# 		dc_pin = 6    cmd = low, data = high
# 		rst_pin = 7   Active-low
#	Touch Screen:
#		sda_pin = 8
#		scl_pin = 9
#		rst_pin = 10
#		irq_pin = 11

class DisplayEngine:
    def __init__(
            self,
            leds_off_callback=None,
            red_led_pwm_callback=None,
            red_led_pwm_kwargs=None,
            green_led_pwm_callback=None,
            green_led_pwm_kwargs=None,
            blue_led_pwm_callback=None,
            blue_led_pwm_kwargs=None,
            yellow_led_pwm_callback=None,
            yellow_led_pwm_kwargs=None,
            cam_view_callback=None,
            cam_view_kwargs=None,
            histogram_callback=None,
            histogram_kwargs=None,
            profiles=None
        ):
        # Set up graphics display using ST7796
        self.lcd_driver = ST7796(
            spi_instance=SPI(
                0,
                baudrate=50_000_000,
                sck=Pin(2), mosi=Pin(3), miso=Pin(4)
            ),
            cs_pin=5, dc_pin=6, rst_pin=7
        )
        self.lcd_driver.init()
        self.lcd = Display(self.lcd_driver)

        # Set up touch screen using GT911
        self.touch = GT911(
            i2c_instance=I2C(
                0,
                scl=Pin(9), sda=Pin(8),
                freq=100_000
            ),
            reset_pin=Pin(10),
            irq_pin=Pin(11),
            touch_callback=self._on_touch
        )
        self.touch.init()
        
        # Stores touchscreen data
        self.touch_data = self.touch.read_points()
        self.touch_triggered = False

        # UI colors
        self.DARK_SLATE_BLUE = self.lcd.hex565(0x1A1F2C)
        self.TEAL_BLUE = self.lcd.hex565(0x00BAD8)
        self.LIGHT_GRAY = self.lcd.hex565(0xEEEEEC)
        self.MID_GRAY = self.lcd.hex565(0x6A737D)
        self.MAGENTA = self.lcd.color565(255, 0, 255)

        # LED colors
        self.RED = self.lcd.color565(255, 0, 0)
        self.GREEN = self.lcd.color565(0, 200, 0)
        self.BLUE = self.lcd.color565(0, 0, 255)
        self.YELLOW = self.lcd.color565(225, 225, 0)
        
        # Chunk lines - Needs to be a factor of 320
        self.CHUNK_LINES = 40
        
        # Flush the touchscreen buffer
        self.debounce()
        
        # Set up the LED states
        self.led_on = False         # TODO: Find a use for this
        self.red_led_on = False
        self.green_led_on = False
        self.blue_led_on = False
        self.yellow_led_on = False

        # Store LED duty cycle percentages
        self.red_duty_percent = 100
        self.green_duty_percent = 100
        self.blue_duty_percent = 100
        self.yellow_duty_percent = 100

        # Assign callback functions
        self.leds_off_callback = leds_off_callback
        self.red_pwm_callback = red_led_pwm_callback
        self.green_pwm_callback = green_led_pwm_callback
        self.blue_pwm_callback = blue_led_pwm_callback
        self.yellow_pwm_callback = yellow_led_pwm_callback
        self.cam_view_callback = cam_view_callback
        self.histogram_callback = histogram_callback

        # Assign keyword argument dictionaries
        self.red_pwm_kwargs = red_led_pwm_kwargs
        self.green_pwm_kwargs = green_led_pwm_kwargs
        self.blue_pwm_kwargs = blue_led_pwm_kwargs
        self.yellow_pwm_kwargs = yellow_led_pwm_kwargs
        self.cam_view_kwargs = cam_view_kwargs
        self.histogram_kwargs = histogram_kwargs

        # Profiles
        self.profiles = profiles
        self.running_profile = None
        self.profile_task = None

        # Set the initial state function
        self.is_first_frame = True
        self.current_state = self.home_screen()
    
    def _on_touch(self, pin):
        self.touch_triggered = True

    def update_screen(self):
        if self.touch_triggered:
            self.touch_data = self.touch.read_points()
            self.touch_triggered = False
            
        next_state = self.current_state()
            
        if next_state != self.current_state:
            self.is_first_frame = True
            self.current_state = next_state

    async def run(self):
        while True:
            self.update_screen()
            await asyncio.sleep_ms(0)
    
    # Waits for finger to be lifted from the screen
    def debounce(self, time_ms=20):
        while True:
            num_points, _ = self.touch.read_points()
            
            if num_points > 0:
                sleep_ms(time_ms)
            else:
                # Double check the touch
                sleep_ms(time_ms)
                num_points, _ = self.touch.read_points()
                if num_points == 0:
                    break

    def turn_off_leds(self):
        self.led_on = False
        self.red_led_on = False
        self.green_led_on = False
        self.blue_led_on = False
        self.yellow_led_on = False

        if self.leds_off_callback is not None:
            self.leds_off_callback()

    def home_screen(self):
        # Make buttons
        led_ctrl_btn = Button(
            self.lcd,
            40, 30, 195, 120,
            self.LIGHT_GRAY,
            text="LED Control", text_color=self.TEAL_BLUE
        )
        pwm_ctrl_btn = Button(
            self.lcd,
            245, 30, 195, 120,
            self.LIGHT_GRAY,
            text="PWM Control", text_color=self.TEAL_BLUE
        )
        cam_view_btn = Button(
            self.lcd,
            40, 160, 195, 120,
            self.LIGHT_GRAY,
            text="Camera View",  text_color=self.TEAL_BLUE
        )
        # histogram_btn = Button(
        #     self.lcd,
        #     245, 160, 195, 120,
        #     self.LIGHT_GRAY,
        #     text="Histogram", text_color=self.TEAL_BLUE
        # )
        profiles_btn = Button(
            self.lcd,
            245, 160, 195, 120,
            self.LIGHT_GRAY,
            text="Profiles", text_color=self.TEAL_BLUE
        )
        
        # Draw screen
        if self.is_first_frame:
            self.lcd.fill_screen(self.DARK_SLATE_BLUE, chunk_lines=self.CHUNK_LINES)
            self.lcd.text("SWIR Illuminator", 176, 11, self.TEAL_BLUE, self.DARK_SLATE_BLUE)

            led_ctrl_btn.draw()
            pwm_ctrl_btn.draw()
            cam_view_btn.draw()
            # histogram_btn.draw()
            profiles_btn.draw()
            
            self.is_first_frame = False
        
        # Check buttons
        if led_ctrl_btn.is_pressed(self.touch_data):
            self.debounce()
            return self.led_ctrl_screen
        if pwm_ctrl_btn.is_pressed(self.touch_data):
            self.debounce()
            return self.pwm_ctrl_screen
        if cam_view_btn.is_pressed(self.touch_data):
            self.debounce()
            return self.cam_view_screen
        # if histogram_btn.is_pressed(self.touch_data):
        #     self.debounce()
        #     return self.histogram_screen
        if profiles_btn.is_pressed(self.touch_data):
            self.debounce()
            return self.profiles_screen
        
        return self.home_screen

    def led_ctrl_screen(self):
        # Make buttons
        back_btn = Button(
            self.lcd,
            5, 5, 50, 25,
            self.LIGHT_GRAY,
            text="Back", text_color=self.TEAL_BLUE
        )
        
        # Helper functions to make the buttons in the correct state
        def make_red_btn():
            btn_color = self.RED if self.red_led_on else self.LIGHT_GRAY
            txt_color = self.LIGHT_GRAY if self.red_led_on else self.RED
            return Button(
                self.lcd,
                20, 40, 210, 120,
                btn_color,
                text="Red LED", text_color=txt_color
            )
        def make_green_btn():
            btn_color = self.GREEN if self.green_led_on else self.LIGHT_GRAY
            txt_color = self.LIGHT_GRAY if self.green_led_on else self.GREEN
            return Button(
                self.lcd,
                250, 40, 210, 120,
                btn_color,
                text="Green LED", text_color=txt_color
            )
        def make_blue_btn():
            btn_color = self.BLUE if self.blue_led_on else self.LIGHT_GRAY
            txt_color = self.LIGHT_GRAY if self.blue_led_on else self.BLUE
            return Button(
                self.lcd,
                20, 180, 210, 120,
                btn_color,
                text="Blue LED", text_color=txt_color
            )
        def make_yellow_btn():
            btn_color = self.YELLOW if self.yellow_led_on else self.LIGHT_GRAY
            txt_color = self.LIGHT_GRAY if self.yellow_led_on else self.YELLOW
            return Button(
                self.lcd,
                250, 180, 210, 120,
                btn_color,
                text="Yellow LED", text_color=txt_color
            )
        
        red_led_btn = make_red_btn()
        green_led_btn = make_green_btn()
        blue_led_btn = make_blue_btn()
        yellow_led_btn = make_yellow_btn()
        
        # Draw screen
        if self.is_first_frame:
            self.lcd.fill_screen(self.DARK_SLATE_BLUE, chunk_lines=self.CHUNK_LINES)
            self.lcd.text("LED Control", 196, 16, self.TEAL_BLUE, self.DARK_SLATE_BLUE)
        
            back_btn.draw()
            red_led_btn.draw()
            green_led_btn.draw()
            blue_led_btn.draw()
            yellow_led_btn.draw()
            
            self.is_first_frame = False
        
        # Check buttons
        if back_btn.is_pressed(self.touch_data):
            self.debounce()
            return self.home_screen
        elif red_led_btn.is_pressed(self.touch_data):
            self.debounce()
            self.red_led_on = not self.red_led_on
            make_red_btn().draw()
        elif green_led_btn.is_pressed(self.touch_data):
            self.debounce()
            self.green_led_on = not self.green_led_on
            make_green_btn().draw()
        elif blue_led_btn.is_pressed(self.touch_data):
            self.debounce()
            self.blue_led_on = not self.blue_led_on
            make_blue_btn().draw()
        elif yellow_led_btn.is_pressed(self.touch_data):
            self.debounce()
            self.yellow_led_on = not self.yellow_led_on
            make_yellow_btn().draw()
        
        return self.led_ctrl_screen
    
    def pwm_ctrl_screen(self):
        # Make buttons
        back_btn = Button(
            self.lcd,
            5, 5, 50, 25,
            self.LIGHT_GRAY,
            text="Back", text_color=self.TEAL_BLUE
        )
        red_pwm_btn = Button(
            self.lcd,
            20, 40, 210, 80,
            self.LIGHT_GRAY,
            text="Red Duty %", text_color=self.RED
        )
        green_pwm_btn = Button(
            self.lcd,
            250, 40, 210, 80,
            self.LIGHT_GRAY,
            text="Green Duty %", text_color=self.GREEN
        )
        blue_pwm_btn = Button(
            self.lcd,
            20, 180, 210, 80,
            self.LIGHT_GRAY,
            text="Blue Duty %", text_color=self.TEAL_BLUE
        )
        yellow_pwm_btn = Button(
            self.lcd,
            250, 180, 210, 80,
            self.LIGHT_GRAY,
            text="Yellow Duty %", text_color=self.YELLOW
        )

        # Duty percent label helpers
        def make_red_duty_percent_label():
            self.lcd.text(
                f"Duty %: {self.red_duty_percent:>3}%",
                85, 136,
                self.TEAL_BLUE, self.DARK_SLATE_BLUE
            )
        def make_green_duty_percent_label():
            self.lcd.text(
                f"Duty %: {self.green_duty_percent:>3}%",
                315, 136,
                self.TEAL_BLUE, self.DARK_SLATE_BLUE
            )
        def make_blue_duty_percent_label():
            self.lcd.text(
                f"Duty %: {self.blue_duty_percent:>3}%",
                85, 276,
                self.TEAL_BLUE, self.DARK_SLATE_BLUE
            )
        def make_yellow_duty_percent_label():
            self.lcd.text(
                f"Duty %: {self.yellow_duty_percent:>3}%",
                315, 276,
                self.TEAL_BLUE, self.DARK_SLATE_BLUE
            )
        
        # Draw screen
        if self.is_first_frame:
            self.lcd.fill_screen(self.DARK_SLATE_BLUE, chunk_lines=self.CHUNK_LINES)
            self.lcd.text("PWM Control", 196, 16, self.TEAL_BLUE, self.DARK_SLATE_BLUE)
        
            back_btn.draw()
            red_pwm_btn.draw()
            green_pwm_btn.draw()
            blue_pwm_btn.draw()
            yellow_pwm_btn.draw()

            make_red_duty_percent_label()
            make_green_duty_percent_label()
            make_blue_duty_percent_label()
            make_yellow_duty_percent_label()
            
            self.is_first_frame = False
        
        # Check buttons
        if back_btn.is_pressed(self.touch_data):
            self.debounce()
            return self.home_screen
        elif red_pwm_btn.is_pressed(self.touch_data):
            self.debounce()

            if self.red_pwm_callback is not None:
                if self.red_pwm_kwargs is not None:
                    kwargs = self.red_pwm_kwargs.copy()
                else:
                    kwargs = {}

                kwargs["current_duty"] = self.red_duty_percent
                self.red_duty_percent = self.red_pwm_callback(**kwargs)

            make_red_duty_percent_label()
        elif green_pwm_btn.is_pressed(self.touch_data):
            self.debounce()

            if self.green_pwm_callback is not None:
                if self.green_pwm_kwargs is not None:
                    kwargs = self.green_pwm_kwargs.copy()
                else:
                    kwargs = {}

                kwargs["current_duty"] = self.green_duty_percent
                self.green_duty_percent = self.green_pwm_callback(**kwargs)

            make_green_duty_percent_label()
        elif blue_pwm_btn.is_pressed(self.touch_data):
            self.debounce()

            if self.blue_pwm_callback is not None:
                if self.blue_pwm_kwargs is not None:
                    kwargs = self.blue_pwm_kwargs.copy()
                else:
                    kwargs = {}

                kwargs["current_duty"] = self.blue_duty_percent
                self.blue_duty_percent = self.blue_pwm_callback(**kwargs)

            make_blue_duty_percent_label()
        elif yellow_pwm_btn.is_pressed(self.touch_data):
            self.debounce()

            if self.yellow_pwm_callback is not None:
                if self.yellow_pwm_kwargs is not None:
                    kwargs = self.yellow_pwm_kwargs.copy()
                else:
                    kwargs = {}

                kwargs["current_duty"] = self.yellow_duty_percent
                self.yellow_duty_percent = self.yellow_pwm_callback(**kwargs)

            make_yellow_duty_percent_label()
        
        return self.pwm_ctrl_screen

    def cam_view_screen(self):
        # Make buttons
        back_btn = Button(
            self.lcd,
            5, 5, 50, 25,
            self.LIGHT_GRAY,
            text="Back", text_color=self.TEAL_BLUE
        )
        
        # Draw screen
        if self.is_first_frame:
            self.lcd.fill_screen(self.DARK_SLATE_BLUE, chunk_lines=self.CHUNK_LINES)
            self.lcd.text("Camera View", 196, 16, self.TEAL_BLUE, self.DARK_SLATE_BLUE)
            if self.cam_view_callback is None:
                # For right now, chunk_lines needs to be a factor of 260
                self.lcd.fill_area(
                    20, 40, 440, 260,
                    self.MAGENTA, chunk_lines=52
                )
        
            back_btn.draw()
            
            self.is_first_frame = False

        # Update screen with camera view
        if self.cam_view_callback is not None:
            if self.cam_view_kwargs is not None:
                payload = self.cam_view_callback(**self.cam_view_kwargs)
            else:
                payload = self.cam_view_callback()

            for key in payload:
                payload[key]["color"] = self.lcd.color565(*payload[key]["color"])
                self.lcd.fill_area(**payload[key])
        
        # Check buttons
        if back_btn.is_pressed(self.touch_data):
            self.debounce()
            return self.home_screen
        
        return self.cam_view_screen
    
    def histogram_screen(self):
        # Make buttons
        back_btn = Button(
            self.lcd,
            5, 5, 50, 25,
            self.LIGHT_GRAY,
            text="Back", text_color=self.TEAL_BLUE
        )
        
        # Draw screen
        if self.is_first_frame:
            self.lcd.fill_screen(self.DARK_SLATE_BLUE, chunk_lines=self.CHUNK_LINES)
            self.lcd.text("Histogram", 204, 16, self.TEAL_BLUE, self.DARK_SLATE_BLUE)
            if self.histogram_callback is None:
                # For right now, chunk_lines needs to be a factor of 260
                self.lcd.fill_area(
                    20, 40, 440, 260,
                    self.MAGENTA, chunk_lines=52
                )
        
            back_btn.draw()
            
            self.is_first_frame = False

        if self.histogram_callback is not None:
            if self.histogram_kwargs is not None:
                self.histogram_callback(**self.histogram_kwargs)
            else:
                self.histogram_callback()
        
        # Check buttons
        if back_btn.is_pressed(self.touch_data):
            self.debounce()
            return self.home_screen
        
        return self.histogram_screen

    def profiles_screen(self):
        # Make buttons
        back_btn = Button(
            self.lcd,
            5, 5, 50, 25,
            self.LIGHT_GRAY,
            text="Back", text_color=self.TEAL_BLUE
        )

        if self.profiles is not None:
            profile_btns = {}
            # 4 buttons per page
            btn_positions = (
                (20, 40),
                (250, 40),
                (20, 180),
                (250, 180)
            )

            for label, (x, y) in zip(self.profiles, btn_positions):
                profile_btns[label] = Button(
                    self.lcd,
                    x, y, 195, 120,
                    self.LIGHT_GRAY,
                    text=label, text_color=self.TEAL_BLUE
                )

        # Draw screen
        if self.is_first_frame:
            self.lcd.fill_screen(self.DARK_SLATE_BLUE, chunk_lines=self.CHUNK_LINES)
            self.lcd.text("Profiles", 196, 16, self.TEAL_BLUE, self.DARK_SLATE_BLUE)

            back_btn.draw()
            if self.profiles is not None:
                for button in profile_btns.values():
                    button.draw()

            self.is_first_frame = False

        # Check buttons
        if back_btn.is_pressed(self.touch_data):
            self.debounce()
            return self.home_screen

        if self.profiles is not None:
            for label, button in profile_btns.items():
                if button.is_pressed(self.touch_data):
                    self.debounce()
                    self.turn_off_leds()

                    self.running_profile = label

                    return self.profile_running_screen

        return self.profiles_screen

    def profile_running_screen(self):
        # Make buttons
        cancel_btn = Button(
            self.lcd,
            180, 130, 120, 60,
            self.LIGHT_GRAY,
            text="Cancel", text_color=self.TEAL_BLUE
        )

        # Draw screen
        if self.is_first_frame:
            self.lcd.fill_screen(self.DARK_SLATE_BLUE, chunk_lines=self.CHUNK_LINES)
            self.lcd.text(f"Running profile: {self.running_profile}", 160, 266, self.TEAL_BLUE, self.DARK_SLATE_BLUE)

            cancel_btn.draw()

            self.is_first_frame = False

        # Handle profile
        if self.profile_task is None and self.running_profile in self.profiles:
            self.profile_task = asyncio.create_task(self.profiles[self.running_profile]())

        if self.profile_task is not None and self.profile_task.done():
            self.profile_task = None
            self.running_profile = None

            return self.profiles_screen

        # Check buttons
        if cancel_btn.is_pressed(self.touch_data):
            self.debounce()

            if self.profile_task is not None and not self.profile_task.done():
                self.profile_task.cancel()

            self.profile_task = None
            self.running_profile = None

            return self.profiles_screen

        return self.profile_running_screen

# The following is the bare minimum required to run the display
if __name__ == "__main__":
    display = DisplayEngine()

    asyncio.run(display.run())
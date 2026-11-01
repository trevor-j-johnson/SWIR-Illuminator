from machine import Pin, SPI
from time import sleep_ms

# Command registers
_SWRESET =  const(0x01) # Software reset
_SLPIN =    const(0x10) # Sleep in
_SLPOUT =   const(0x11) # Sleep out
_INVOFF =   const(0x20) # Display inversion off
_INVON =    const(0x21) # Display inversion on
_DISPOFF =  const(0x28) # Display off
_DISPON =   const(0x29) # Display on
_CASET =    const(0x2A) # Column address set
_RASET =    const(0x2B) # Row address set
_RAMWR =    const(0x2C) # Memory write
_MADCTL =   const(0x36) # Memory data access control
_COLMOD =   const(0x3A) # Interface pixel format
_WRDISBV =  const(0x51) # Write display brightness

class ST7796:
    WIDTH =  const(480)
    HEIGHT = const(320)
    
    def __init__(
            self,
            spi_instance,
            cs_pin,
            dc_pin,
            rst_pin,
        ):
        # Initialize class variables
        self.spi = spi_instance
        self.cs = Pin(cs_pin, mode=Pin.OUT, value=0)
        self.dc = Pin(dc_pin, mode=Pin.OUT, value=1)
        self.rst = Pin(rst_pin, mode=Pin.OUT, value=0)

        # Display initialization sequence
        self.hw_reset()
        self.init()

    def init(self):
        # Software reset
        self._write_cmd(_SWRESET)
        sleep_ms(150)

        # Memory access control (Landscape mode)
        self._write_cmd(_MADCTL)
        self._write_data(bytearray([0x28]))

        # Set pixel format (16-bit/pixel - RBG565)
        self._write_cmd(_COLMOD)
        self._write_data(bytearray([0x55]))

        # Turn color inversion on
        self._write_cmd(_INVON)

        # Exit sleep
        self._write_cmd(_SLPOUT)
        sleep_ms(150)

        # Turn on display
        self._write_cmd(_DISPON)
        sleep_ms(150)

    def hw_reset(self):
        self.rst.high()
        sleep_ms(10)
        self.rst.low()
        sleep_ms(20)
        self.rst.high()
        sleep_ms(150)

    # Max area of 132000 pixels on Pi Pico
    # (This becomes a max area of 260000 pixels with the Pi Pico 2)
    def render(self, x, y, width, height, buf):
        # Get end positions
        x2 = x + width - 1
        y2 = y + height - 1

        # Send position coordinates
        self._write_cmd(_CASET)
        self._write_data(
            bytearray([
                (x >> 8) & 0xFF,    # Start x high byte
                x & 0xFF,           # Start x low byte
                (x2 >> 8) & 0xFF,   # End x high byte
                x2 & 0xFF           # End x low byte
            ])
        )
        self._write_cmd(_RASET)
        self._write_data(
            bytearray([
                (y >> 8) & 0xFF,    # Start y high byte
                y & 0xFF,           # Start y low byte
                (y2 >> 8) & 0xFF,   # End y high byte
                y2 & 0xFF           # End y low byte
            ])
        )

        # Send frame buffer
        self._write_cmd(_RAMWR)
        self._write_data(buf)

    def _write_cmd(self, cmd):
        self.dc.low()
        self.__cs_select()
        self.spi.write(bytearray([cmd]))
        self.__cs_deselect()

    def _write_data(self, byte_array):
        self.dc.high()
        self.__cs_select()
        self.spi.write(byte_array)
        self.__cs_deselect()

    def __cs_select(self):
        self.cs.low()

        # CS needs >15ns before write operations
        self.__nop()
        self.__nop()
        self.__nop()

    def __cs_deselect(self):
        # CS needs >15ns before going high
        self.__nop()
        self.__nop()
        self.__nop()

        self.cs.high()

        # CS needs to remain high for >40ns
        self.__nop()
        self.__nop()
        self.__nop()
        self.__nop()
        self.__nop()
        self.__nop()
    
    @staticmethod
    @micropython.asm_thumb
    def __nop():
        nop()
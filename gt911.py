from time import sleep_ms, sleep_us
from array import array
from machine import Pin

# Addresses
_DEFAULT_ADDR = const(0x5D)
_ALT_ADDR = const(0x14)

# Real-time command registers
_COMMAND = const(0x8040)

# Configuration information registers
_CONFIG_VERSION = const(0x8047)
_RESOLUTION_X = const(0x8048) # 2 bytes
_RESOLUTION_Y = const(0x804A) # 2 bytes
_TOUCH_POINTS = const(0x804C)
_MODULE_SWITCH1 = const(0x804D)
_REFRESH_RATE = const(0x8056)
_CONFIG_CHKSUM = const(0x80FF)
_CONFIG_FRESH = const(0x8100)

# Coordinate information registers
_DATA_BUFFER = const(0x814E)
_POINT_DATA_START = const(0x8150) # 8 bytes

class GT911:
    def __init__(
        self,
        i2c_instance,
        reset_pin,
        irq_pin,
        address=_DEFAULT_ADDR,
        touch_callback=None,
        trigger=Pin.IRQ_RISING
    ):
        self.i2c = i2c_instance
        self.address = self.__check_addr(address)
        self.reset_pin = reset_pin
        self.irq_pin = irq_pin
        self.touch_callback = touch_callback
        self.trigger = trigger
        self.points_data = None
    
    def init(
            self,
            width=480,
            height=320,
            touch_points=1,
            reverse_x=True,
            reverse_y=False,
            reverse_axis=True,
            sito=True,
            irq_trigger="rising",
            refresh_rate=50,
        ):
        self.reset()

        self._write_reg(_RESOLUTION_X, width, 2)
        self._write_reg(_RESOLUTION_Y, height, 2)
        self._write_reg(_TOUCH_POINTS, touch_points)
        self._write_reg(
            _MODULE_SWITCH1,
            (
                (int(reverse_y) << 7) |
                (int(reverse_x) << 6) |
                (int(reverse_axis) << 3) |
                (int(sito) << 2) |
                (self.__return_irq_trigger(irq_trigger))
            )
        )
        self._write_reg(
            _REFRESH_RATE,
            self.__convert_refresh(refresh_rate)
        )
        # Set command to read coordinates status
        self._write_reg(_COMMAND, 0x00)
        self._update_config()

        # Allocate a scratch buffer
        self.points_data = [array("H", [0, 0, 0, 0]) for x in range(5)]

    def reset(self):
        # Disable interrupts
        self.irq_pin.irq(handler=None)

        # Set rst and irq output low
        self.reset_pin.low()
        self.irq_pin.init(mode=Pin.OUT, value=0)

        if self.address == _ALT_ADDR:
            self.irq_pin.high()
        
        # T1/T2: Must wait at least 100 us
        sleep_us(200)

        self.reset_pin.high()
        # T3: Must wait at least 5 ms
        sleep_ms(10)

        if self.address == _ALT_ADDR:
            self.irq_pin.low()
        
        # T4: Must wait at least 50 ms
        sleep_ms(100)

        self.irq_pin.init(mode=Pin.IN, pull=None)
        
        # Sets the callback function
        if self.touch_callback is not None:
            self.irq_pin.irq(
                handler=self.touch_callback, trigger=self.trigger
            )

    def read_points(self):
        status = self._read_reg(_DATA_BUFFER)[0]
        num_points = status & 0x0F
        if status & 0x80:
            for i in range(num_points):
                self._read_reg(
                    _POINT_DATA_START + 8*i,
                    buf=self.points_data[i]
                )
                # Shifting out the extra reserved byte
                self.points_data[i][-1] = self.points_data[i][-1] >> 8
            self._write_reg(_DATA_BUFFER, 0)
        return num_points, self.points_data

    def _read_reg(self, reg, size=1, buf=None):
        if buf is not None:
            self.i2c.readfrom_mem_into(
                self.address, reg, buf, addrsize=16
            )
        else:
            return self.i2c.readfrom_mem(
                self.address, reg, size, addrsize=16
            )
    
    def _write_reg(self, reg, data, size=1):
        buf = (bytes([data & 0xFF]) if size == 1
               else bytes([data & 0xFF, data >> 8]))
        self.i2c.writeto_mem(
            self.address, reg, buf, addrsize=16
        )
    
    def _update_config(self):
        # Read all config info (0x8047-0x80FE) and calc checksum
        chksum = ~sum(self._read_reg(_CONFIG_VERSION, 184)) + 1
        # Update checksum
        self._write_reg(_CONFIG_CHKSUM, chksum)
        # Set config flag to 1
        self._write_reg(_CONFIG_FRESH, 0x01)
    
    def __return_irq_trigger(self, trigger):
        if trigger == "rising":
            return 0x00
        elif trigger == "falling":
            return 0x01
        raise ValueError("Trigger must be rising or falling")
    
    def __convert_refresh(self, refresh):
        if refresh < 50 or refresh > 200:
            raise ValueError("Refresh rate must be between 50-200 Hz")
        # Return refresh period between 0-15 ms
        return 1000 // refresh - 5

    def __check_addr(self, address):
        if address == _DEFAULT_ADDR or address == _ALT_ADDR:
            return address
        raise ValueError("Address not valid for GT911")
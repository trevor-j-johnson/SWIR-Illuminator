import framebuf

# Button object
class Button:
    def __init__(
            self,
            Display,
            x, y, width, height,
            color,
            text=None, text_color=None
        ):
        # Assigns class instances
        self.display = Display

        # Absolute coordinates of the button
        self.x1 = x
        self.x2 = x + width - 1
        self.y1 = y
        self.y2 = y + height - 1

        # Button properties
        self.width = width
        self.height = height
        self.color = color
        self.text = text
        self.text_color = text_color

    def draw(self):
        buf = bytearray(self.width * self.height * 2)
        fbuf = framebuf.FrameBuffer(buf, self.width, self.height, framebuf.RGB565)

        fbuf.rect(0, 0, self.width, self.height, self.color, True)

        if self.text and self.text_color is not None:
            x_text = (self.width - len(self.text)*8) // 2
            y_text = (self.height - 8) // 2
            fbuf.text(self.text, x_text, y_text, self.text_color)

        self.display.lcd.render(self.x1, self.y1, self.width, self.height, fbuf)
    
    # Checks if button is pressed
    def is_pressed(self, touch_data):
        num_points, touch_coords = touch_data
        
        if num_points == 0:
            return False
        
        for i in range(num_points):
            x = touch_coords[i][0]
            y = touch_coords[i][1]
            if (self.x1 <= x <= self.x2) and (self.y1 <= y <= self.y2):
                return True
        
        return False

class Display:
    def __init__(self, lcd_driver):
        # We initialize the class with the display driver being used
        # (ex. ST7796)
        self.lcd = lcd_driver
    
    def text(self, text, x, y, text_color, bg_color):
        width = len(text) * 8
        height = 8
        
        buf = bytearray(width * height * 2)
        fbuf = framebuf.FrameBuffer(buf, width, height, framebuf.RGB565)
        
        fbuf.rect(0, 0, width, height, bg_color, True)
        fbuf.text(text, 0, 0, text_color)

        self.lcd.render(x, y, width, height, fbuf)

    def fill_screen(self, color, chunk_lines=20):
        # Create the frame buffer
        buf = bytearray(self.lcd.WIDTH * chunk_lines * 2)
        fbuf = framebuf.FrameBuffer(buf, self.lcd.WIDTH, chunk_lines, framebuf.RGB565)

        # Set the chunk color
        fbuf.fill(color)

        # For now, chunk_lines needs to perfectly divide the screen height
        # Render the screen
        for n in range(self.lcd.HEIGHT // chunk_lines):
            self.lcd.render(0, n*chunk_lines, self.lcd.WIDTH, chunk_lines, fbuf)
    
    def fill_area(self, x, y, width, height, color, chunk_lines = 20):
        # Create the frame buffer
        buf = bytearray(width * chunk_lines * 2)
        fbuf = framebuf.FrameBuffer(buf, width, chunk_lines, framebuf.RGB565)
        
        # Set the chunk color
        fbuf.fill(color)
        
        # For now, chunk_lines needs to perfectly divide the screen height
        # Render the screen
        for n in range(height // chunk_lines):
            self.lcd.render(x, n*chunk_lines + y, width, chunk_lines, fbuf)

    # Converts RGB values to a 16-bit RGB565 value
    def color565(self, r, g, b, little_endian=True):
        color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        if little_endian:
            color = ((color & 0xFF) << 8) | (color >> 8)
        return color
    
    # Converts color hex code to a 16-bit RGB565 value
    def hex565(self, hex, little_endian=True):
        color = ((hex & 0xF80000) >> 8) | ((hex & 0xFC00) >> 5) | ((hex & 0xF8) >> 3)
        if little_endian:
            color = ((color & 0xFF) << 8) | (color >> 8)
        return color
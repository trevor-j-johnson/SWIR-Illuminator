from machine import ADC
import framebuf
from time import sleep_ms

def cam_view(num_cams):
    color = (255, 255, 255) # White at max brightness
    payload = {}
    side_px = 80

    y = 160 - side_px // 2

    for cam_num in range(num_cams):
        multiplier = num_cams - 2 * cam_num
        x = 240 - (side_px // 2) * multiplier

        cam = ADC(cam_num)
        # Maps ADC as float point from 0 to 1
        cam_read = (cam.read_u16() >> 4) / 4095

        # Vary brightness based on ADC
        disp_color = tuple(int(c * cam_read) for c in color)

        payload[f"Cam{cam_num}"] = {
            "x": x, "y": y,
            "width": side_px, "height": side_px,
            "color": disp_color,
            "chunk_lines": side_px
        }
        
        sleep_ms(10)

    return payload

# Test the above function on the breakout board joystick
if __name__ == "__main__":
    from display_engine import DisplayEngine

    display = DisplayEngine(
        cam_view_callback=cam_view,
        cam_view_kwargs={"num_cams": 2}
    )

    while True:
        display.update_screen()
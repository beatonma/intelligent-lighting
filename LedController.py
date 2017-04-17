import color
import wiringpi as WP

from color import hsv_to_string
from color import string_to_hsv
from color import string_to_rgb
from datetime import datetime
from util import log


class LedController:

    def __init__(self, preferences=None, pin_red=22, pin_green=27, pin_blue=17):
        self.pin_red = pin_red
        self.pin_green = pin_green
        self.pin_blue = pin_blue

        self._init_gpio()

        # The last 'selected' color, discounting any changes made by
        # interpolation. i.e. the previous target_color
        self.old_color = '0 0 0'

        # The last color that was actually sent to the lights
        self.previous_color = '0 0 0'
        self.color_change_time = 0

        self.preferences = preferences

    def _init_gpio(self):
        result = WP.wiringPiSetupGpio()
        if result == -1:
            log('LedController setup failed')
        else:
            log('LedController setup successful')

            for pin in [self.pin_red, self.pin_green, self.pin_blue]:
                WP.pinMode(pin, 1)
                WP.softPwmCreate(pin, 0, 100)

    def set_preferences(self, preferences):
        self.preferences = preferences

    def set_color(self, rgb_string):
        if self.preferences.color_change_interpolate:
            interpolated_result = self._morph_to_color(rgb_string)

            if interpolated_result == rgb_string:
                self.old_color = rgb_string
            rgb_string = interpolated_result

        rgb_string = self._apply_restrictions(rgb_string)

        if rgb_string == self.previous_color:
            # Sending repeated commands to the lights can cause flickering so
            # we return here if the color has not changed
            return

        r, g, b = string_to_rgb(rgb_string)

        WP.softPwmWrite(self.pin_red, r)
        WP.softPwmWrite(self.pin_green, g)
        WP.softPwmWrite(self.pin_blue, b)

        self.previous_color = rgb_string

    # Constrain brightness to fit user preferences
    def _apply_restrictions(self, rgb_string):
        h, s, v = string_to_hsv(rgb_string)
        v = int(min(self.preferences.max_brightness / 100.0 * 255.0,
                    max(v, self.preferences.min_brightness / 100.0 * 255.0)))

        return hsv_to_string((h, s, v))

    def _morph_to_color(self, rgb_string):
        now = datetime.now()
        if self.old_color == rgb_string:
            # No changes
            return rgb_string

        if self.color_change_time == 0:
            self.color_change_time = now

        progress = (now - self.color_change_time).total_seconds() / \
            self.preferences.color_change_duration
        if progress > 1:
            self.old_color = rgb_string
            self.color_change_time = 0
            return rgb_string

        return color.morph(self.old_color, rgb_string, progress)

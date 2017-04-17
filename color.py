from colorsys import hsv_to_rgb, rgb_to_hsv
from math import fabs


class Color:
    _RED = "255 0 0"
    _GREEN = "0 255 0"
    _BLUE = "0 0 255"
    _YELLOW = "255 255 0"
    _CYAN = "0 255 255"
    _MAGENTA = "255 0 255"
    _WHITE = "255 255 255"
    _BLACK = "0 0 0"

    _ORANGE = "255 10 0"
    _PINK = "255 0 10"

    NAMES = {
        'red': _RED,
        'green': _GREEN,
        'blue': _BLUE,
        'yellow': _YELLOW,
        'cyan': _CYAN,
        'light blue': _CYAN,
        'magenta': _MAGENTA,
        'purple': _MAGENTA,
        'white': _WHITE,
        'black': _BLACK,
        'off': _BLACK,
        'orange': _ORANGE,
        'pink': _PINK
    }

    _COLORS = [
        _RED,
        _GREEN,
        _BLUE,
        _YELLOW,
        _CYAN,
        _MAGENTA,
        _WHITE
    ]

    def __init__(self, colors=None):
        self.index = 0
        self.set_colors(colors)

    def set_colors(self, colors=None):
        if colors is None or len(colors) == 0:
            self.colors = Color._COLORS
        else:
            self.colors = [Color.NAMES[x] for x in colors]

    def get_next(self):
        self.index = (self.index + 1) % len(self.colors)
        return self.get()

    def get(self, color_name=None):
        if color_name is None:
            return self.colors[self.index]
        else:
            try:
                return Color.NAMES[color_name]
            except:
                return self.colors[self.index]


def string_to_rgb(string):
    r, g, b = [int(x) for x in string.split(" ")]
    return (r, g, b)


def string_to_hsv(string):
    r, g, b = string_to_rgb(string)
    h, s, v = rgb_to_hsv(r, g, b)
    return h, s, v


def rgb_to_string(rgb):
    r, g, b = rgb
    return "{} {} {}".format(r, g, b)


def hsv_to_string(hsv):
    h, s, v = hsv
    r, g, b = [int(x) for x in hsv_to_rgb(h, s, v)]

    return rgb_to_string((r, g, b))


def get_hue(string):
    h, s, v = string_to_hsv(string)
    return h


def get_saturation(string):
    h, s, v = string_to_hsv(string)
    return s


def get_brightness(string):
    h, s, v = string_to_hsv(string)
    return v


def set_brightness(string, value):
    h, s, v = string_to_hsv(string)
    return hsv_to_string((h, s, value * 255.0))

#
# Functions for interpolating from one color to another
#


# Linear interpolation
def interpolate(f, min, max):
    return min + ((max - min) * f)


def constrain(val, min, max):
    if val < min:
        return min
    elif val > max:
        return max
    else:
        return val


def progress(v, a, b):
    v1 = min(a, b)
    v2 = max(a, b)
    return constrain((v - v1) / (v2 - v1), 0, 1)


def morph(from_string, to_string, t):
    # from_hue, from_saturation, from_value
    fh, fs, fv = string_to_hsv(from_string)

    # to_hue, to_saturation, to_value
    th, ts, tv = string_to_hsv(to_string)

    # Decide how close the hues are to each other to determine whether
    # we should interpolate directly between them or use an
    # intermediate fade-out
    distance = fabs(fh - th)
    direct = distance < 0.2

    if direct:
        h = interpolate(t, fh, th)
        s = interpolate(t, fs, ts)
        v = interpolate(t, fv, tv)
    else:
        d0 = progress(t, 0.0, 0.4)
        d1 = progress(t, 0.4, 0.6)
        d2 = progress(t, 0.6, 1.0)

        # desaturate and dim, then change hue, then brighten and saturate again
        min_saturation = 0.9 * fs
        min_brightness = 0.05 * fv

        if d1 == 0:
            h = fh
            s = interpolate(d0, fs, min_saturation)
            v = interpolate(d0, fv, min_brightness * 255.0)
        elif d2 == 0:
            h = interpolate(d1, fh, th)
            s = min_saturation
            v = min_brightness * 255.0
        else:
            h = th
            s = interpolate(d2, min_saturation, ts)
            v = interpolate(d2, min_brightness * 255.0, tv)

    if tv == 0:
        h = fh
        s = fs
    elif fv == 0:
        h = th
        s = ts

    return hsv_to_string((h, s, v))

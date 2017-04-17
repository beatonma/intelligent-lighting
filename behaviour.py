from datetime import datetime
from math import pi
from math import sin
from random import random
from time import sleep

import color

from color import Color

from util import read_line
from util import read_lines
from util import safe_load


class Behaviour:
    WEB_DIRECTORY = '/var/www/api/led_control/'

    NONE = 0
    CYCLE = 1
    DISCO = 2
    PULSE = 3
    SPOOKY = 4
    AI = 5
    MECH = 6

    # Restrict any bpm-based behaviours to a minimum beat duration (in seconds)
    #  to prevent unpleasant flickering/strobing
    MIN_BEAT_DURATION = 0.25

    @staticmethod
    def get(id):
        if id == Behaviour.CYCLE:
            return CycleBehaviour()
        elif id == Behaviour.DISCO:
            return DiscoBehaviour()
        elif id == Behaviour.SPOOKY:
            return SpookyBehaviour()
        elif id == Behaviour.PULSE:
            return PulseBehaviour()
        elif id == Behaviour.AI:
            return AIBehaviour()
        elif id == Behaviour.MECH:
            return MechBehaviour()
        else:
            return Behaviour()

    def __init__(self, prefs=None):
        self.set_preferences(prefs)
        self.last_update = datetime.now()

    def reset(self):
        pass

    # Return the modified color as a string, and True if this modified color
    # should be considered as canonical
    # (i.e. if True, this behaviour will affect AI learning behaviour,
    # False will not)
    def update(self, fallback_color, now):
        self.last_update = now
        return fallback_color, True

    def set_preferences(self, preferences):
        if preferences is None:
            return

        prefs = safe_load(preferences, '0', {})
        self.duration = safe_load(prefs, 'duration', 10)

    def to_string(self):
        pass

    def id(self):
        return Behaviour.NONE


class CycleBehaviour(Behaviour):

    def __init__(self, prefs=None):
        super().__init__(prefs)
        self.set_preferences(prefs)
        self.cycle_start = -1
        self.original_hue = -1
        self.original_brightness = 1
        self.delta = 0

    def reset(self):
        self.cycle_start = -1
        self.original_hue = -1
        self.original_brightness = 1
        self.delta = 0

    def update(self, fallback_color, now):
        if self.original_hue < 0:
            self.original_hue = color.get_hue(fallback_color)
            self.original_brightness = color.get_brightness(fallback_color)
            self.cycle_start = now

        delta = ((now - self.cycle_start).total_seconds() /
                    self.duration) % 1.0
        hue = (self.original_hue + delta) % 1.0

        return color.hsv_to_string((hue, 1.0, self.original_brightness)), False

    def to_string(self):
        return "CycleBehaviour[duration:{}]".format(self.duration)

    def id(self):
        return Behaviour.CYCLE


class DiscoBehaviour(Behaviour):

    def __init__(self, prefs=None):
        self.color = Color()
        super().__init__(prefs)
        self.set_preferences(prefs)
        self.last_change = None

    def reset(self):
        self.last_change = -1
        pass

    def update(self, fallback_color, now):
        if self.last_change is None:
            self.last_change = now

        delta = (now - self.last_change).total_seconds()
        if delta > self.color_duration:
            self.color.get_next()
            self.last_change = now

        return self.color.get(), False

    def set_preferences(self, preferences):
        super().set_preferences(preferences)
        prefs = safe_load(preferences, "{}".format(self.id(), {}))

        self.bpm = safe_load(prefs, 'bpm', 60)
        self.color.set_colors(safe_load(prefs, 'colors', None))

        self.color_duration = self._bpm_to_pulse_duration(self.bpm)

    def _bpm_to_pulse_duration(self, bpm):
        pulse = 60 / bpm
        while pulse < Behaviour.MIN_BEAT_DURATION:
            pulse = pulse * 2

        return pulse

    def to_string(self):
        return "DiscoBehaviour[bpm:{}, color_duration:{}]"\
            .format(self.bpm, self.color_duration)

    def id(self):
        return Behaviour.DISCO


'''
###
### WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
### WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
### WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
###
### This behaviour causes the lights to flicker which may cause nausea or
### siezure. Please do not enable this feature if you or anyone around you
### is prone to siezure through photosensitive epilepsy -
### https://en.wikipedia.org/wiki/Photosensitive_epilepsy
### - or any similar condition.
###
### This behaviour is intended to simulate the lightning effects from old-timey
### horror movies
###
'''


class SpookyBehaviour(Behaviour):
    STATE_LOW = 0
    STATE_HIGH = 1

    def __init__(self, prefs=None):
        super().__init__(prefs)
        self.last_change = None
        self.state = SpookyBehaviour.STATE_LOW
        self.set_preferences(prefs)

    def reset(self):
        self.last_change = None
        self.state = SpookyBehaviour.STATE_LOW

    def update(self, fallback_color, now):
        if self.last_change is None:
            self.last_change = now

        brightness = color.get_brightness(fallback_color)

        delta = (now - self.last_change).total_seconds()
        if self.state == SpookyBehaviour.STATE_LOW:
            brightness = 0.01 + (random() * 0.05)

            if delta > self.low_duration and random() > 0.6:
                self.state = SpookyBehaviour.STATE_HIGH
                self.last_change = now
        elif self.state == SpookyBehaviour.STATE_HIGH:
            brightness = 0.2 + (random() * 0.7)

            if delta > self.high_duration and random() > 0.6:
                self.state = SpookyBehaviour.STATE_LOW
                self.last_change = now

        # This can be removed or reduced if you are sure that nobody
        # is likely to suffer adverse affects from flashing lights
        sleep(0.5)

        return color.set_brightness(fallback_color, brightness), False

    def set_preferences(self, preferences):
        super().set_preferences(preferences)
        prefs = safe_load(preferences, "{}".format(self.id(), {}))

        self.high_duration = safe_load(prefs, 'high_duration', 1.5)
        self.low_duration = safe_load(prefs, 'low_duration', 5.0)

    def to_string(self):
        return "SpookyBehaviour[]: WARNING: THIS MAY BE A HEALTH HAZARD"

    def id(self):
        return Behaviour.SPOOKY


class AIBehaviour(Behaviour):
    AI_AMBIENT_FILE = Behaviour.WEB_DIRECTORY + 'ambient_ai'

    def __init__(self, prefs=None):
        super().__init__(prefs)
        self.set_preferences(prefs)
        self.color = None

    def reset(self):
        self.color = None

    def update(self, fallback_color, now):
        if self.color is None:
            self.color = fallback_color
        color = read_line(AIBehaviour.AI_AMBIENT_FILE)
        if color != "":
            # Cache a copy of the color to prevent flickering in case of file
            # read errors
            self.color = color
        return self.color, True

    def set_preferences(self, preferences):
        super().set_preferences(preferences)
        pass

    def to_string(self):
        return "AIBehaviour[]"

    def id(self):
        return Behaviour.AI


class MechBehaviour(Behaviour):
    MECH_FILE = Behaviour.WEB_DIRECTORY + 'mech'

    def __init__(self, prefs=None):
        super().__init__(prefs)
        self.set_preferences(prefs)
        self.color = None
        self.source = ""

    def reset(self):
        self.color = None
        self.source = ""

    def update(self, fallback_color, now):
        if self.color is None:
            self.color = fallback_color

        lines = read_lines(MechBehaviour.MECH_FILE)
        try:
            mech_color = lines[0].strip()
            timestamp = int(lines[1].strip())
            delta = int(now.timestamp()) - timestamp
            if delta < self.timeout:
                if self.only_when_dark and color.get_brightness(fallback_color) > 50:
                    raise Exception(
                        "Not using mech color - not dark enough just now")
                self.color = mech_color
                return mech_color, False
            else:
                self.color = ""
        except Exception as e:
            print("ERROR: {}".format(e))
            pass

        return fallback_color, False

    def set_preferences(self, preferences):
        super().set_preferences(preferences)
        self.timeout = 5
        self.only_when_dark = True

    def to_string(self):
        return "MechBehaviour[]"

    def id(self):
        return Behaviour.MECH


class PulseBehaviour(Behaviour):

    def __init__(self, prefs=None):
        super().__init__(prefs)
        self.set_preferences(prefs)
        self.brightness = -1
        self.cycle_start = -1

    def reset(self):
        self.brightness = -1
        pass

    def update(self, fallback_color, now):
        if self.cycle_start == -1:
            self.cycle_start = now

        h, s, v = color.string_to_hsv(fallback_color)

        delta = ((now - self.cycle_start).total_seconds() /
                 self.beat_duration) % 1.0

        if self.waveform == 'sin':
            v = sin(delta * pi) * 255.0
        # TODO Try out other waveforms
#        elif self.waveform == 'square':
#            pass
#        elif self.waveform == 'triangle':
#            v = delta * 255.0
#        elif self.waveform == 'sawtooth':
#            pass
#        else:
        return color.hsv_to_string((h, s, v)), False

    def set_preferences(self, preferences):
        super().set_preferences(preferences)
        prefs = safe_load(preferences, "{}".format(self.id(), {}))

        self.bpm = safe_load(prefs, 'bpm', 60)
        self.beat_duration = self._bpm_to_pulse_duration(self.bpm)

        self.waveform = safe_load(prefs, 'waveform', 'sin')

    def _bpm_to_pulse_duration(self, bpm):
        pulse = 60 / bpm
        while pulse < Behaviour.MIN_BEAT_DURATION:
            pulse = pulse * 2

        return pulse

    def to_string(self):
        return "PulseBehaviour[]"

    def id(self):
        return Behaviour.PULSE

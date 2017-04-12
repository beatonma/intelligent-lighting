from behaviour import *
from LedController import LedController
from util import json_safe_load, log, read_line
from datetime import datetime
import json

DEBUG = False

WEB_ROOT = "/var/www/api/led_control/"
FILE_AMBIENT = WEB_ROOT + "ambient"
FILE_NOTIFICATIONS = WEB_ROOT + "notifications"
FILE_PREFERENCES = WEB_ROOT + "prefs"
FILE_AI = WEB_ROOT + "ambient_ai"
FILE_CANONICAL = WEB_ROOT + "canonical"

class Lights:
    def __init__(self):
        self.preferences = Preferences()
        self.led_controller = LedController(self.preferences)
        self.inactivity_behaviour = Behaviour.get(self.preferences.inactivity_behaviour_id)
        self.mech_behaviour = Behaviour.get(Behaviour.MECH)
        
    def update(self):
        now = datetime.now()
        self._refresh_preferences()
        
        color = read_line(FILE_AMBIENT)
        
        color, is_canonical = self.inactivity_behaviour.update(color, now)
        
        if is_canonical:
            self._update_canonical(color)
        
        self.led_controller.set_preferences(self.preferences)
        self.led_controller.set_color(color)
    
    def _refresh_preferences(self):
        previous_behaviour_id = self.preferences.inactivity_behaviour_id
        self.preferences.refresh()
        
        if previous_behaviour_id != self.preferences.inactivity_behaviour_id:
            self.inactivity_behaviour = Behaviour.get(self.preferences.inactivity_behaviour_id)
            print("new behaviour: {}".format(self.inactivity_behaviour.to_string()))
            
        self.inactivity_behaviour.set_preferences(self.preferences.inactivity_behaviour_options)
    
    # Canonical colors can affect AI learning
    def _update_canonical(self, color):
        with open(FILE_CANONICAL, 'w') as file:
            file.write(color)

class Preferences:
    def __init__(self):
        self.refresh()
    
    def refresh(self, file=FILE_PREFERENCES):
        with open(file) as f:
            j = json.load(f)
            self.max_brightness = json_safe_load(j, 'pref_max_brightness', 100)
            self.min_brightness = json_safe_load(j, 'pref_min_brightness', 0)
            self.color_change_interpolate = json_safe_load(j, 'pref_interpolate_color_changes', True)
            self.color_change_duration = max(0.5, json_safe_load(j, 'pref_color_change_duration', 1.5))
            self.inactivity_timeout = json_safe_load(j, 'pref_inactivity_timeout', 0)
            self.inactivity_behaviour_id = json_safe_load(j, 'pref_inactivity_behaviour', Behaviour.NONE)
            self.inactivity_behaviour_options = json_safe_load(j, 'pref_inactivity_behaviour_options', {})

lights = Lights()
try:
    while True:
        if DEBUG:
            lights.update() # Allow error messages to halt execution
        else:
            try:
                lights.update()
            except Exception as e:
                print("Error: {}".format(e))
except KeyboardInterrupt as k:
    print("LED Control is stopping...")
    
log("LED Control is no longer active")
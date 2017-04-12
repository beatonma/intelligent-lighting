import argparse
from datetime import datetime
from sklearn.externals import joblib
from colorsys import rgb_to_hsv, hsv_to_rgb


class ScheduleRenderer:
    # Half-hour intervals for each day of the week
    TEST_DATA = [[day_of_week, second_of_day] for second_of_day in range(0, 86400, 1800) for day_of_week in range(0, 7)]
    
    def __init__(self, clf, output_file="schedule.html"):
        self.render(clf, output_file)
    
    def render(self, clf, output_file):
        if clf is None:
            raise ValueError("No classifier given")
        
        now = datetime.now()
        
        print("Writing schedule to file '{}'".format(output_file))
        with open(output_file, 'w') as f:
            f.write(self._get_html_start())
            f.write(self._get_table_headers())
                
            indent = "\t\t\t\t"
            for entry in ScheduleRenderer.TEST_DATA:
                day_of_week, second_of_day = entry
                row = ""
                
                if day_of_week == 0:
                    row += indent + "<tr{}>\n".format(self._get_row_class(now, second_of_day)) + indent + "\t<td{}>{}</td>\n".format(self._get_column_class(now, day_of_week), self._seconds_to_hour_min(second_of_day))
                
                prediction = clf.predict([[day_of_week, second_of_day]])[0]
                row += indent + "\t<td{} style='background-color:{};'>{}</td>\n".format(self._get_column_class(now, day_of_week), self._get_cell_color(prediction), prediction)
                
                if day_of_week == 6:
                    row += indent + "</tr>\n"
                
                f.write(row)
            
            f.write(self._get_html_end())
    
    def _get_row_class(self, now, second_of_day):
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        now_seconds = (now - midnight).seconds
        
        if second_of_day < now_seconds < second_of_day + 1800:
            return " class='now'"
        return ""
    
    def _get_column_class(self, now, day_of_week):
        if day_of_week == now.timetuple().tm_wday:
            return " class='today'"
        return ""
    
    # Convert brightness to alpha value
    def _get_cell_color(self, predicted_color):
        r, g, b = string_to_rgb(predicted_color)
        h, s, v = rgb_to_hsv(r, g, b)
        
        a = 0 if v == 0 else max(0.1, v / 255.0)    # Convert brightness to alpha and apply minimum value
        
        r, g, b = [int(255.0 * x) for x in hsv_to_rgb(h, 0.9, 0.9)] # Update rgb values with a saturated, bright color of the correct hue
        return "rgba({}, {}, {}, {})".format(r, g, b, a)
    
    def _seconds_to_hour_min(self, seconds):
        hours = int(seconds / 3600)
        mins = int((seconds / 60) - (hours * 60))
        return "{:02d}:{:02d}".format(hours, mins)
    
    def _get_table_headers(self):
        column_headers = ['', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        indent = "\t\t\t\t"
        output = ""
        for x in column_headers:
            output = output + indent + "\t<th>{}</th>\n".format(x)        
        return output + indent + "</tr>\n"
        
    def _get_html_start(self):
        return "<html>\n\t<head>\n\t\t<title>Expected schedule</title>\n\t\t" + self._get_html_style() + "\n\t</head>\n\t<body>\n\t\t<main>\n\t\t\t<table>\n\t\t\t\t<tr class='header_row'>\n\t\t\t\t\t"
    
    def _get_html_end(self):
        return "\n\t\t\t</table>\n\t\t</main>\n\t</body><footer>Last update: {}</footer>\n</html>".format(datetime.now().strftime("%Y-%m-%d at %H:%M"))
    
    def _get_html_style(self):
        # Uncomment this if you want to use an external stylesheet
#        return "<link rel='stylesheet' type='text/css' href='styles.css'>"
        return "<style>\nhtml{font-family:monospace;background-color:#444;color:#ddd;} table{width:100%;max-width:800px;min-width:600px;} table,th,td{border:0px solid black;border-collapse:collapse;} th,td{text-align:center;vertical-align:middle;padding:2px;} .today{border-left:1px dashed grey;border-right:1px dashed grey;} .now{padding:32px !important;border-top:1px dashed grey;border-bottom:1px dashed grey;}\n</style>"

def string_to_rgb(rgb_string):
    r, g, b = [int(x) for x in rgb_string.split(" ")]
    return (r, g, b)

def load_saved_model(file):
    if file is None or file == "":
        raise ValueError("Error loading saved model '{}'".format(file))
    return joblib.load(file)
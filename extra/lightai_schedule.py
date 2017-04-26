from colorsys import hsv_to_rgb
from colorsys import rgb_to_hsv
from datetime import datetime

from sklearn.externals import joblib


# Generates a schedule from given training data so that you can see
# an overview of what the model has learned
class ScheduleRenderer:
    # Half-hour intervals for each day of the week
    TEST_DATA = [
        [day_of_week, second_of_day]
        for second_of_day in range(0, 86400, 1800)
        for day_of_week in range(0, 7)
    ]

    def __init__(self, clf, output_file="schedule.html"):
        self.render(clf, output_file)

    # Construct an HTML page showing how our model will affect lighting
    # this week.
    def render(self, clf, output_file):
        if clf is None:
            raise ValueError("No classifier given")

        now = datetime.now()

        print("Writing schedule to file '{}'".format(output_file))
        with open(output_file, 'w') as f:
            f.write(self._get_html_start())
            f.write(self._get_table_headers())

            for entry in ScheduleRenderer.TEST_DATA:
                day_of_week, second_of_day = entry
                row = ""

                if day_of_week == 0:
                    row += (
                        "<tr>\n" +
                        "<td>{}</td>\n".format(
                            self._seconds_to_hour_min(second_of_day)
                        )
                    )

                prediction = clf.predict([[day_of_week, second_of_day]])[0]
                row += (
                    "<td style='background-color:{};'>{}</td>\n"
                    .format(
                        self._get_cell_color(prediction),
                        prediction
                    )
                )

                if day_of_week == 6:
                    row += "</tr>\n"

                f.write(row)

            f.write(self._get_html_end())


    # Convert brightness to alpha value
    def _get_cell_color(self, predicted_color):
        r, g, b = string_to_rgb(predicted_color)
        h, s, v = rgb_to_hsv(r, g, b)

        # Convert brightness to alpha and apply minimum value
        a = 0 if v == 0 else max(0.1, v / 255.0)

        # Update rgb values with a saturated, bright color of the
        # correct hue
        r, g, b = [int(255.0 * x) for x in hsv_to_rgb(h, 0.9, 0.9)]
        return "rgba({}, {}, {}, {})".format(r, g, b, a)

    def _seconds_to_hour_min(self, seconds):
        hours = int(seconds / 3600)
        mins = int((seconds / 60) - (hours * 60))
        return "{:02d}:{:02d}".format(hours, mins)

    def _get_table_headers(self):
        column_headers = [
            '', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
            'Saturday', 'Sunday'
        ]
        output = ""
        for x in column_headers:
            output = output + "<th>{}</th>\n".format(x)
        return output + "</tr>\n"

    def _get_html_start(self):
        return (
            "<html>\n<head>\n<title>Expected schedule</title>\n" +
            self._get_html_style() +
            "\n</head>\n<body>\n<main>\n" +
            "<table>\n<tr class='header_row'>\n"
        )

    def _get_html_end(self):
        return (
            "\n</table>\n</main>\n" + self._get_js() + "\n</body><footer>" +
            "Last update: {}</footer>\n</html>"
            .format(datetime.now().strftime("%Y-%m-%d at %H:%M"))
        )

    def _get_html_style(self):
        return (
            "<style>\n" +
            "html{font-family:monospace;background-color:#444;color:#ddd;}" +
            "table{width:100%;max-width:800px;min-width:600px;}" +
            "table,th,td{border:0px solid black;border-collapse:collapse;} " +
            "th,td{text-align:center;vertical-align:middle;padding:2px;} " +
            ".today{border-left:1px dashed grey;" +
            "border-right:1px dashed grey;} " +
            ".now{padding:32px !important;border-top:1px dashed grey;" +
            "border-bottom:1px dashed grey;}\n</style>"
        )

    def _get_js(self):
        return (
            '''
            <script type="text/javascript">
            /*
             * Add borders to the row/column that correspond
             * to the current day and time
             */
            function highlightNow() {
                const highlightBorderStyle = '2px solid #cccccc';
                const now = new Date();
                const today = now.getDay();
                const hour = now.getHours();
                const minutes = now.getMinutes() > 30 ? 30 : 0;

                const interval = 30; // interval for each row in minutes
                const column = today == 0 ? 6 : today;
                const nowTime = (hour < 10 ? '0' : '') + hour + ':' + (minutes < 10 ? '0' : '') + minutes;
                const rows = document.getElementsByTagName('tr');

                for (let i = 0; i < rows.length; i++) {
                    const row = rows[i];
                    const tds = row.getElementsByTagName('td');
                    const col = tds[column];
                    if (col) {
                        col.style.borderLeft = col.style.borderRight = highlightBorderStyle;
                    }
                    const rowTitle = tds[0];
                    if (rowTitle && nowTime == rowTitle.innerText) {
                        row.style.borderTop = row.style.borderBottom = highlightBorderStyle;
                    }
                }
            }
            highlightNow();
            </script>
            '''
        )


# Convert a space-separated string into an RGB tuple
def string_to_rgb(rgb_string):
    r, g, b = [int(x) for x in rgb_string.split(' ')]
    return (r, g, b)


# Load a model from a saved file
def load_saved_model(file):
    if file is None or file == '':
        raise ValueError('Error loading saved model "{}"'.format(file))
    return joblib.load(file)

if __name__ == '__main__':
    clf = joblib.load('model.pkl')
    renderer = ScheduleRenderer(clf, 'test.html')
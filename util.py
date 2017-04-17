import datetime
import os
import time

DATEFORMAT = "%y/%m/%d %H:%M:%S"
LOG_FILE = "log.txt"


def safe_load(dictionary, key, default_value=""):
    try:
        return dictionary[key]
    except:
        pass
    return default_value


def log(text):
    log_text = get_timestamp() + get_script_name() + text + '\r\n'
    print(log_text)

    lines = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()[-9:]

    with open(LOG_FILE, 'w') as f:
        for l in lines:
            f.write(l)

        f.write(log_text)


def get_timestamp():
    return '[' + str(datetime.datetime.now().strftime(DATEFORMAT)) + '] '


def get_current_time():
    return time.time()


def get_script_name():
    return '[' + os.path.basename(__file__) + '] '


def count_lines(file):
    return sum(1 for line in open(file))


def read_line(file, line_number=0):
    line = ''
    with open(file, 'r') as f:
        try:
            line = f.readlines()[line_number].strip()
        except:
            pass

    return line


def read_lines(file):
    lines = []
    with open(file, 'r') as f:
        try:
            lines = f.readlines()
        except:
            pass
    return lines


def append(file, text):
    with open(file, 'a+') as f:
        f.write(text)

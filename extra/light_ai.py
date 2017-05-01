# Created on 17 November 2016 by Michael Beaton
# Automatic light control using machine learning
#
# Input files may be either:
#   - A raw .dat file from which a model will be constructed before use
#   - A pre-built model in the form of a .pkl file

import argparse

from datetime import datetime

from time import sleep
import requests

from lightai_schedule import ScheduleRenderer

from sklearn import tree
from sklearn.externals import joblib

# day_of_year probably won't have any useful effect until at least
# a year's worth of usage data has been collected. If USE_DAY_OF_YEAR
# is False the day_of_year will be ignored when training the model
USE_DAY_OF_YEAR = True

# URL which handles lighting commands - this should point to your
# node.js server
LIGHTING_URL = 'http://localhost:8080'


class LightAI:
    def __init__(self, classifier):
        self.color = ''
        self.clf = classifier

    def set_classifier(self, classifier):
        self.clf = classifier

    def update(self, now):
        day_of_year = now.timetuple().tm_yday
        day_of_week = now.timetuple().tm_wday
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        second_of_day = (now - midnight).seconds

        if USE_DAY_OF_YEAR:
            rgb = self.clf.prefix(
                [[day_of_year, day_of_week, second_of_day]]
            )[0]
        else:
            rgb = self.clf.predict(
                [[day_of_week, second_of_day]]
            )[0]

        print('[{}, {}] -> {}'.format(day_of_week, second_of_day, rgb))

        if rgb != self.color:
            data = {
                'ai': '',
                'rgb': rgb
            }
            requests.get(LIGHTING_URL, data)
            self.color = rgb


def construct_model(data_file):
    if data_file is None or data_file == '':
        raise ValueError(
            'A data file is required to train a model. ' +
            'Please specify the filename with --data_file'
        )

    X, y = parse_training_data(data_file)

    clf = tree.DecisionTreeClassifier()
    clf = clf.fit(X, y)

    return clf


def parse_training_data(data_file):
    X = []
    y = []

    line_count = 0
    for line in open(data_file, 'r'):
        line_count += 1
        if '#' in line:
            continue

        line = line.strip()
        if line == '':
            continue

        # Split into features,labels
        parts = line.split(':')

        # Split into day_of_year,day_of_week,second_of_day
        features = parts[0].split(',')

        if USE_DAY_OF_YEAR:
            # day_of_year, day_of_week, second_of_day
            X.append([int(features[0]), int(features[1]), int(features[2])])
        else:
            # day_of_week, second_of_day
            X.append([int(features[1]), int(features[2])])

        labels = parts[1].split(',')    # Split into rgb,hue,saturation,value
        y.append(labels[0])
    return X, y


def save_model(clf, save_file, data_file='default_filename'):
    if save_file is None or save_file == '':
        save_file = '{}_{}.pkl'\
            .format(
                data_file.replace('.dat', ''),
                datetime.now().strftime('%y-%m-%d_%H%M%S')
            )
    joblib.dump(clf, save_file)

    ScheduleRenderer(clf, args.save_schedule)


def load_saved_model(file):
    if file is None or file == '':
        raise ValueError('Cannot load saved model "{}"'.format(file))
    return joblib.load(file)


def construct_and_save_model(data_file, save_file):
    global last_update
    clf = construct_model(args.data)
    if update_interval > 0:
        last_update = datetime.now()
    if clf is not None:
        save_model(clf, args.save_as, args.data)
        print('Classifier successfully constructed from data file')

    return clf


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='LightAI')
    parser.add_argument(
        '--data',
        type=str,
        help='Filename for data file to be used for training (.dat file)')
    parser.add_argument(
        '--save_as',
        type=str,
        help='Filename for saving the output classifier (.pkl file)')
    parser.add_argument(
        '--update_interval',
        type=int,
        help='Regularly re-train the classifier using the same input ' +
             'filename (Interval in hours)',
        default=-1)
    parser.add_argument(
        '--saved_classifier',
        type=str,
        help='Define a previously stored classifier (.pkl file)')
    parser.add_argument(
        '--save_schedule',
        type=str,
        default='schedule.html',
        help='Filename for the generated schedule html file')

    args = parser.parse_args()
    clf = None
    last_update = datetime.now()
    update_interval = args.update_interval * 3600
    print('update interval: {}hrs'.format(args.update_interval))

    # Load classifier from saved .pkl file
    if args.saved_classifier is not None:
        clf = load_saved_model(args.saved_classifier)
        print('Loaded classifier from saved file')

    # Train a new classifier using the given data file
    else:
        clf = construct_and_save_model(args.data, args.save_as)

    if clf is None:
        raise ValueException(
            'Classifier was not constructed or loaded. ' +
            'Please check input parameters'
        )

    light_ai = LightAI(clf)

    try:
        while True:
            now = datetime.now()
            light_ai.update(now)

            if update_interval > 0 and (
                (now - last_update).total_seconds() > update_interval
            ):
                print('Updating model...')
                construct_and_save_model(args.data, args.save_as)

            sleep(60)
    except KeyboardInterrupt as k:
        print('LightAI is stopping')
    except Exception as e:
        print('Exception: {}'.format(e))

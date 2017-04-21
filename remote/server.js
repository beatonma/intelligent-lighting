/**
 * This script requires extra modules. Run:
 * 
 * npm install colorsys --save
 * 
 * to install the necessary modules
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const querystring = require('querystring');
const colorsys = require('colorsys');

// If no parameters are given then show gui for manual control
const GUI_HTML = '<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#111111"><link rel="stylesheet" href="https://code.getmdl.io/1.3.0/material.indigo-pink.min.css"><script defer src="https://code.getmdl.io/1.3.0/material.min.js"></script><title>LED Control</title><style>html{background:#232323;}main{flex-direction:column;}.container{width:100vw;height:100vh;margin:auto;max-width: 900px;}.color_card{width:33vw !important;height:33vw !important;}.off_card{width:100% !important;height:33vw !important;}.flexbox{display:flex;flex-wrap:wrap;justify-content: center;}.left{}.right{}@media only screen and (min-width:480px){.container{padding-top:5vw;padding-bottom:5vw;width:90vw;margin:auto;}.color_card{width:30vw !important;height:30vw !important;}.off_card{width:90vw !important;height:33vw !important;max-height:200px !important;}}@media only screen and (min-width:600px){.container{max-width: 600px;}.color_card{width:30% !important;height:auto !important;padding-bottom:30%;}.off_card{width:90% !important;height:33vw !important;}.flexbox{justify-content: center;}}</style><script type="text/javascript">function set_color(params){var slider=document.getElementById("brightness");var brightness=slider.value;post(\'?\' + params + \'&brightness=\' + brightness);}function set_brightness(value){post(\'/?brightness=\' + value);}function post(path){var xhttp=new XMLHttpRequest();var params=window.location.search.substr(1);var query=path + "&" + params;xhttp.open("GET", query, true);console.log(query);xhttp.send();}</script></head><body><main><div class="container"><div class="flexbox left"><div class="mdl-shadow--2dp color_card" style="background:#F44336;" onclick="set_color(\'r=255\')"></div><div class="mdl-shadow--2dp color_card" style="background:#4CAF50;" onclick="set_color(\'g=255\')"></div><div class="mdl-shadow--2dp color_card" style="background:#2196F3;" onclick="set_color(\'b=255\')"></div><div class="mdl-shadow--2dp color_card" style="background:#FFEB3B;" onclick="set_color(\'r=255&g=255\')"></div><div class="mdl-shadow--2dp color_card" style="background:#00BCD4;" onclick="set_color(\'g=255&b=255\')"></div><div class="mdl-shadow--2dp color_card" style="background:#9C27B0;" onclick="set_color(\'r=255&b=255\')"></div><div class="mdl-shadow--2dp color_card" style="background:#E91E63;" onclick="set_color(\'r=255&b=10\')"></div><div class="mdl-shadow--2dp color_card" style="background:#FF9800;" onclick="set_color(\'r=255&g=10\')"></div><div class="mdl-shadow--2dp color_card" style="background:#ffffff;" onclick="set_color(\'r=255&g=255&b=255\')"></div></div><div class="slider_container" style="padding:20px 0 20px 0;"><input class="mdl-slider mdl-js-slider slider" id="brightness" type="range" min="0" max="100" value="100" oninput="set_brightness(this.value)"></div><div class="flexbox right"><div class="mdl-shadow--2dp off_card" style="background:#111111;" onclick="set_brightness(0)"></div></div></div></main></body></html>'

const STATUS_DIRECTORY = 'status'
const FILE_AMBIENT = path.join(STATUS_DIRECTORY, 'ambient');
const FILE_NOTIFICATIONS = path.join(STATUS_DIRECTORY, 'notifications');
const FILE_PREFERENCES = path.join(STATUS_DIRECTORY, 'prefs');
const FILE_CANONICAL = path.join(STATUS_DIRECTORY, 'canonical');
const FILE_AI = path.join(STATUS_DIRECTORY, 'ambient_ai');
const FILE_MECH = path.join(STATUS_DIRECTORY, 'mech');

const mimeTypes = {
    'ico': 'image/x-icon',
    'html': 'text/html',
    'js': 'text/javascript',
    'json': 'application/json',
    'css': 'text/css',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'mp3': 'audio/mpeg',
    'svg': 'image/svg+xml',
    'pdf': 'application/pdf',
};
const staticFilesWhitelist = [
    'favicon.ico',
    'index.html',
    'prefs'
];
const staticFilesRedirects = {
    'prefs': FILE_PREFERENCES,
    'canonical': FILE_CANONICAL
};

if (!fs.existsSync(STATUS_DIRECTORY)) {
    fs.mkdirSync(STATUS_DIRECTORY);
}

const server = http.createServer(function(request, response) {
    const headers = request.headers;
    const method = request.method;
    const url = request.url;
    var data = '';

    request.on('error', function(err) {
        console.error(err);
    }).on('data', function(chunk) {
        data += chunk;
        if (data.length > 1e6) {
            request.connection.destroy();
        }
    }).on('end', function() {
        var params = null;
        if (method === 'GET') {
            // Path starts with /? or ?
            if (url.match(/^\/?\?/)) {
                params = querystring.parse(url.replace(/^\/?\?/, ''));
            }
            else {
                serveStatic(url, response);
                return;
            }
        }
        else if (method === 'POST') {
            params = querystring.parse(data);
        }
        if (params) {
            handleRequest(params, response, function(statusCode, message) {
                response.statusCode = statusCode;
                response.end(message);
            });
        }
        else {
            serveGui(response);
        }

        response.on('error', function(err) {
            console.error(err);
        });
    });
}).listen(8080);

/**
 * @param  {object} GET or POST parameters as a dictionary
 * @param  {Function} Callback with parameters for http status code and 
 *                    text to be returned to the client
 */
function handleRequest(params, response, callback) {
    // If 'ai' parameter is set, the source of this command was an AI/ML agent.
    const ai = 'ai' in params;

    if (safeRead(params, 'add_notification')) {
        addNotification(params['add_notification'], params['rgb']);
    }
    else if (safeRead(params, 'remove_notification')) {
        removeNotification(params['remove_notification']);
    }
    else if ('clear_notifications' in params) {
        clearNotifications();
    }
    else if ('rgb' in params || 'brightness' in params ||
            'r' in params || 'g' in params || 'b' in params) {
        try {
            const partialRgb = format('{} {} {}', safeRead(params, 'r', 0), safeRead(params, 'g', 0), safeRead(params, 'b', 0));
            setRgbColor(ai, safeRead(params, 'rgb', partialRgb), parseInt(safeRead(params, 'brightness', -1)));
        }
        catch(e) {
            console.error('Error setting color: ' + e);
        }
    }
    else if (safeRead(params, 'set_preferences')) {
        setPreferences(params['set_preferences']);
    }
    else {
        console.error('unrecognised params: ' + JSON.stringify(params));
        // If no parameters given, return a GUI for manual control;
        serveGui(response);
        return;
    }
    callback(200, 'ok');
}

function serveStatic(url, response) {
    url = url.replace(/^\//, '');
    if (!url) {
        serveGui(response);
        return;
    }
    if (url == 'test_connection') {
        response.statusCode = 200;
        response.end('ok');
        return;
    }
    if (staticFilesWhitelist.indexOf(url) >= 0) {
        if (url in staticFilesRedirects) {
            console.log(format('redirected {} to {}', url, staticFilesRedirects[url]));
            url = staticFilesRedirects[url];
        }
    }
    fs.stat(url, function(err, fstats) {
        if (err) {
            genErr(err);
            serveGui(response);
        }
        else {
            if (fstats.isFile()) {
                fs.readFile(url, function(err, data) {
                    const m = /\.(\w+)$/.exec(url);
                    if (m) {
                        const ext = m[1];
                        response.setHeader('Content-type', mimeTypes[ext] || 'text/plain');
                    }
                    else {
                        response.setHeader('Content-type', 'text/plain');
                    }
                    response.statusCode = 200;
                    response.end(data);
                });
            }
            else {
                console.error(format('Not a file: "{}"', url));
                serveGui(response);
            }
        }
    });
}

function serveGui(response) {
    fs.readFile('index.html', function(err, data) {
        if (err) {
            response.statusCode = 404;
            response.end('Error');
        }
        else {
            response.setHeader('Content-type', 'text/html');
            response.end(data);
        }
    });
}

function safeRead(obj, key) {
    if (key in obj) {
        return obj[key];
    }

    if (arguments.length == 3) {
        return arguments[2];
    }
    return null;
}

function addNotification(packageName, rgb) {
    var j = {
        'package': packageName,
        'rgb': rgb
    };

    fs.readFile(FILE_NOTIFICATIONS, function(err, data) {
        if (err) genErr(err);

        var obj;
        if (data) obj = JSON.parse(data);
        
        if (!obj) {
            obj = [];
        }
        if (Array.isArray(obj)) {
            var alreadyExists = false;
            // Update color if entry already exists
            for (var i=0; i < obj.length; i++) {
                const item = obj[i];

                if (item['package'] == packageName) {
                    item['rgb'] = rgb;
                    alreadyExists = true;
                }
            }
            // Otherwise add it to the list
            if (!alreadyExists) {
                obj.push(j);
            }
        }
        else {
            console.error('Notifications object is not an array: ' + JSON.stringify(obj));
        }

        fs.writeFile(FILE_NOTIFICATIONS, JSON.stringify(obj), genErr);
    })
}

function removeNotification(packageName) {
    fs.readFile(FILE_NOTIFICATIONS, function(err, data) {
        if (err) console.error(err);
        var obj;
        if (data) obj = JSON.parse(data);

        if (!obj) {
            return;
        }

        var out = []
        if (Array.isArray(obj)) {
            for (var i=0; i < obj.length; i++) {
                var item = obj[i];
                if (item['package'] != packageName) {
                    out.push(item);
                }
            }
        }
        console.log('Saving notifications:\n' + JSON.stringify(out, null, 2));

        fs.writeFile(FILE_NOTIFICATIONS, JSON.stringify(out), genErr);
    });
}

function clearNotifications() {
    fs.writeFile(FILE_NOTIFICATIONS, JSON.stringify([]), genErr);
}

function setPreferences(preferences) {
    fs.writeFileSync(FILE_PREFERENCES, preferences);
    console.log('Wrote preferences: ' + preferences);
}

function setRgbColor(ai, color, brightness) {
    console.log('color:"' + color + '" + brightness:"' + brightness + '"');
    var rgb = '';
    if (color == null) {
        color = fs.readFileSync(FILE_AMBIENT);
        if (color == null) {
            console.error('Could not read color from file');
        }
        else {
            rgb = String(color).split('\n')[0].trim();
        }
    }
    else {
        const colors = {
            'red': '255 0 0',
            'green': '0 255 0',
            'blue': '0 0 255',
            'yellow': '255 255 0',
            'cyan': '0 255 255',
            'light blue': '0 255 255',
            'magenta': '255 0 255',
            'purple': '255 0 255',
            'orange': '255 10 0',
            'pink': '255 0 10',
            'white': '255 255 255',
            'black': '0 0 0',
            'off': '0 0 0'
        }
        rgb = safeRead(colors, color, color);
    }

    if (!rgb) {
        console.error('Error getting RGB values');
        return;
    }
    if (brightness < 0) {
        writeAmbient(ai, rgb, genErr);
        console.log('Setting color to "' + rgb + '"');
    }
    else {
        var rgbComponentsStr = rgb.split(' ');
        var r = parseInt(rgbComponentsStr[0]);
        var g = parseInt(rgbComponentsStr[1]);
        var b = parseInt(rgbComponentsStr[2]);
        var hsv = colorsys.rgbToHsv(r, g, b)[0];
        
        hsv['v'] = brightness;
        rgb = colorsys.hsvToRgb(hsv);

        writeAmbient(ai, format('{} {} {}', rgb['r'], rgb['g'], rgb['b']), genErr);
        console.log('Setting color to "' + JSON.stringify(rgb) + '"');
    }
}

// Generic error handler
function genErr(err) {
    console.error(err);
}

/**
 * @param  {boolean}    Whether this command was initiated by an AI entity or not
 * @param  {string}     Text to be written to file
 * @param  {function}   Error handler callback
 */
function writeAmbient(ai, content, errorCallback) {
    const filename = ai ? FILE_AI : FILE_AMBIENT;
    fs.writeFile(filename, content + '\n' + parseInt((Date.now() / 1000)), errorCallback);
}

/**
 * Replicates basic positional string formatting from Python
 * 
 * @param  {[string,object]}    The first argument is the string to be formatted
 *                              Any following arguments are used to replace '{}'
 *                              in the main string.
 * @return {[string]}           The given text with arguments inserted
 */
function format(text) {
    if (arguments.length > 1) {
        for (var i = 1; i < arguments.length; i++) {
            text = text.replace(/({}){1}/, arguments[i]);
        }
    }
    return text;
}
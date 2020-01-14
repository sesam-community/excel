from functools import wraps
from flask import Flask, request, Response,abort

import json
from filehandling import get_file_by_row, get_file_by_col, valid_request


import logging
import threading
import os

app = Flask(__name__)
config = {}
config_since = None

logger = None
format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger('excelms')
# Log to stdout
stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(logging.Formatter(format_string))
logger.addHandler(stdout_handler)
logger.setLevel(logging.getLevelName(os.environ.get('log_level', 'DEBUG')))

_lock_config = threading.Lock()


requiredVars = ['file_url']
optionalVars = ['sheet', 'start','direction','names','ids','since']


## Helper functions

# def check_env_variables(required_env_vars, missing_env_vars):
#     for env_var in required_env_vars:
#         value = os.getenv(env_var)
#         if not value:
#             missing_env_vars.append(env_var)
#
#     if len(missing_env_vars) != 0:
#         app.logger.error(f"Missing the following required environment variable(s) {missing_env_vars}")
#         sys.exit(1)

def datetime_format(dt):
    return '%04d' % dt.year + dt.strftime("-%m-%dT%H:%M:%SZ")


def to_transit_datetime(dt_int):
    return "~t" + datetime_format(dt_int)

def stream_as_json(generator_function):
    """
    Stream list of objects as JSON array
    :param generator_function:
    :return:
    """
    first = True

    yield '['

    for item in generator_function:
        if not first:
            yield ','
        else:
            first = False
        yield json.dumps(item)

    yield ']'






def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_method = "none"
        if auth_method != "none":
            auth = request.authorization
            if not auth:
                return authenticate()
            return f(*args, **kwargs)
        else:
            return f(*args, **kwargs)

    return decorated


@app.route('/<string:url>',methods=['GET', 'POST'])
@requires_auth
def get_entities(file_url):
    logger.debug("Start", file_url)
    print("start", file_url)
    requestData = json.loads(str(request.get_data().decode("utf-8")))[0]
    logger.debug(requestData)
    print(requestData)
    if valid_request(requestData, requiredVars, optionalVars):
        ids = requestData.get("ids") or ["-1"]
        names = requestData.get("names") or [0]
        start = requestData.get("start") or {"row" : 1, "col": 0}
        sheets = requestData.get("sheets")
        logger.info("Get %s using request: %s" % (file_url, request.url))
        since = requestData.get("since") or "0001-01-01"
        if requestData.get("direction") == "col":
            return Response(stream_as_json(get_file_by_col(file_url, ids, names, start, since,sheets)))
        else:
            return Response(stream_as_json(get_file_by_row(file_url, ids, names, start, since,sheets)))
    else:
        return("400")


def create_response(fileUrl, ids, names, start, since):
    yield from stream_as_json(get_file_by_row(fileUrl, ids, names, start, since))

if __name__ == '__main__':
    # Set up logging


    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)

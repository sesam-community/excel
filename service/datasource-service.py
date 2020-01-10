from functools import wraps
from flask import Flask, request, Response, abort
import xlrd
import json
import os
import requests
# from requests_ntlm import HttpNtlmAuth
# from requests.auth import HTTPBasicAuth
# from requests.auth import HTTPDigestAuth
from filehandling import get_file_by_row, get_file_by_col


import logging
import threading
import datetime

app = Flask(__name__)
config = {}
config_since = None

logger = None

_lock_config = threading.Lock()


required_env_vars = ['file_url', 'client_secret', 'tenant_id']
missing_env_vars = list()

## Helper functions
def check_env_variables(required_env_vars, missing_env_vars):
    for env_var in required_env_vars:
        value = os.getenv(env_var)
        if not value:
            missing_env_vars.append(env_var)

    if len(missing_env_vars) != 0:
        app.logger.error(f"Missing the following required environment variable(s) {missing_env_vars}")
        sys.exit(1)

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
            print(",")
            yield ','
        else:
            first = False
        print(item)
        print(type(item))
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


@app.route('/')
@requires_auth
def get_entities():
    
    fileUrl = "https://www.bring.no/radgivning/sende-noe/adressetjenester/postnummer/_/attachment/download/c0300459-6555-4833-b42c-4b16496b7cc0:1127fa77303a0347c45d609069d1483b429a36c0/Postnummerregister-Excel.xlsx"## get_var('file')
    ids = "0"
    ids = [int(x)-1 for x in ids.split(',')]
    print(ids)
    names = "1"
    names = [int(x)-1 for x in names.split(',')]
    start = "2,1"
    start = [int(x)-1 for x in start.split(',')]
    #logger.info("Get %s using request: %s" % (fileUrl, request.url))
    since = "0001-01-01"


    # if auth_method != "none":
    #     auth = request.authorization
    #     if auth_method == "ntlm":
    #         request_auth = HttpNtlmAuth(auth.username, auth.password)
    #     elif auth_method == "basic":
    #         request_auth = HTTPBasicAuth(auth.username, auth.password)
    #     elif auth_method == "digest":
    #         request_auth = HTTPDigestAuth(auth.username, auth.password)
    print(get_file_by_row(fileUrl, ids, names, start, since))

    return Response(stream_as_json(get_file_by_row(fileUrl, ids, names, start, since)))

def create_response(fileUrl, ids, names, start, since):
    yield from stream_as_json(get_file_by_row(fileUrl, ids, names, start, since))

if __name__ == '__main__':
    # Set up logging
    format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logger = logging.getLogger('sharepoint-microservice')

    # Log to stdout
    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(stdout_handler)

    logger.setLevel(logging.DEBUG)

    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
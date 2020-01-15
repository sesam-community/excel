from functools import wraps
from flask import Flask, request, Response,abort

import json
from filehandling import stream_file_by_row, stream_file_by_col
from sesamutils import sesam_logger


import threading
import os

app = Flask(__name__)


logger = sesam_logger("datasource-service", app=app)

_lock_config = threading.Lock()

requiredVars = ['file_url']
optionalVars = ['sheet', 'start','direction','names','ids','since']
logger.info(f"------Starting MS------- {requiredVars}")

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


@app.route("/get_excel", methods=["GET", "POST"])
@requires_auth
def get_entities():
    logger.info("------Starting app-------")
    file_url = request.args.get("file_url")
    if not file_url:
        logger.error(f"No file_url specified, stopping service")
        return ("404")
    ids = request.args.get("ids") or "-1"
    ids = [int(x) for x in ids.split(',')]
    names = request.args.get("names") or "0"
    names = [int(x) for x in names.split(',')]
    start = request.args.get("start") or {"row" : 1, "col": 0}
    sheets = request.args.get("sheets")
    since = request.args.get("since") or "0001-01-01"
    request_auth = None
    auth_method = get_var('auth') or "none"
    logger.debug(f"variables set: file_url = {file_url} names = {names} ids =  {ids} start = {start} since = {since} sheets = {sheets}")
    if request.args.get("direction") == "col":
        logger.info("calling stream by col")
        return Response(stream_as_json(stream_file_by_col(file_url, ids, names, start, since,sheets,request_auth)))
    else:
        logger.info("calling stream by row")
    return Response(stream_as_json(stream_file_by_row(file_url, ids, names, start, since,sheets,request_auth)))



if __name__ == '__main__':
    # Set up logging

    app.run(threaded=True, debug=True, host='0.0.0.0')

from functools import wraps
from flask import Flask, request, Response, abort
import xlrd
import json
import os
import requests
from requests_ntlm import HttpNtlmAuth
from requests.auth import HTTPBasicAuth
from requests.auth import HTTPDigestAuth

import logging
import threading
import datetime

app = Flask(__name__)
config = {}
config_since = None

logger = None

_lock_config = threading.Lock()


def datetime_format(dt):
    return '%04d' % dt.year + dt.strftime("-%m-%dT%H:%M:%SZ")


def to_transit_datetime(dt_int):
    return "~t" + datetime_format(dt_int)


def getColNames(sheet,names,start):
    rowSize = max([sheet.row_len(rowstart) for rowstart in names])
    rowValues = [sheet.row_values(x, start[0], rowSize) for x in names]
    return  ['-'.join(row) for row in map(lambda *a: list(a), *rowValues)]


def getRowNames(sheet,names,start):
    colValues = [sheet.col_values(x, start[1], sheet.nrows) for x in names]
    return  ['-'.join(row) for row in map(lambda *a: list(a), *colValues)]



def getRowData(row, columnNames, start, ids, idx, lastmod, datemode):
    rowData = {}
    counter = 0
    id = None

    for cell in row:
        if counter in ids:
            if id:
                id = id + "-" + str(cell.value, datemode)
            else:
                id = str(cell.value)
        if counter>=start:
            value = to_transit_cell(cell, datemode)
            if value:
                rowData[columnNames[counter - start]] = value
        counter += 1
    rowData["_id"] = id or str(idx+1)
    rowData["_updated"] = lastmod
    return rowData

def getColData(col, rowNames, start, ids, idx, lastmod, datemode):
    colData = {}
    counter = 0
    id = None

    for cell in col:
        if counter in ids:
            if id:
                id = id + "-" + str(cell.value)
            else:
                id = str(cell.value)
        if counter>=start:
            value = to_transit_cell(cell, datemode)
            if value:
                colData[rowNames[counter - start]] = value


        counter += 1
    colData["_id"] = id or str(idx)+1
    colData["_updated"] = lastmod
    return colData


def to_transit_cell(cell, datemode):
    value = None
    if cell.ctype in [1]:
        value = cell.value
    if cell.ctype in [2]:
        value = "~f" + str(cell.value)
    if cell.ctype == 3:
        year, month, day, hour, minute, second = xlrd.xldate_as_tuple(cell.value, datemode)
        py_date = datetime.datetime(year, month, day, hour, minute, second)
        value = to_transit_datetime(py_date)
    if cell.ctype == 4:
        if cell.value == 1:
            value = "~?t"
        else:
            value = "~?f"
    return value


def getSheetRowData(sheet, columnNames, start, ids, lastmod, datemode):
    nRows = sheet.nrows
    sheetData = []

    for idx in range(start[1], nRows):
        row = sheet.row(idx)
        rowData = getRowData(row, columnNames, start[0], ids, idx, lastmod, datemode)
        sheetData.append(rowData)

    return sheetData

def getSheetColData(sheet, rowNames, start, ids, lastmod, datemode):
    nCols = sheet.row_len(start[0])
    sheetData = []

    for idx in range(start[0], nCols):
        col = sheet.col(idx)
        colData = getColData(col, rowNames, start[1], ids, idx, lastmod, datemode)
        sheetData.append(colData)

    return sheetData

def get_var(var):
    envvar = None
    if var.upper() in os.environ:
        envvar = os.environ[var.upper()]
    else:
        envvar = request.args.get(var)
    logger.info("Setting %s = %s" % (var, envvar))
    return envvar

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_method = get_var('auth') or "none"
        if auth_method != "none":
            auth = request.authorization
            if not auth:
                return authenticate()
            return f(*args, **kwargs)
        else:
            return f(*args, **kwargs)

    return decorated


@app.route('/<path:path>', methods=["GET"])
@requires_auth
def get_entities(path):

    file = get_var('base_url')+path
    sheet = int(get_var('sheet') or 1) - 1
    ids = get_var('ids') or "0"
    ids = [int(x)-1 for x in ids.split(',')]
    names = get_var('names') or "1"
    names = [int(x)-1 for x in names.split(',')]
    direction = get_var('direction') or "row"
    start = get_var('start')
    if not start and direction=="row":
        start="1,2"
    elif not start:
        start = "2,1"
    start = [int(x)-1 for x in start.split(',')]
    logger.info("Get %s using request: %s" % (file, request.url))
    since = request.args.get('since') or "0001-01-01"

    request_auth = None
    auth_method = get_var('auth') or "none"

    if auth_method != "none":
        auth = request.authorization
        if auth_method == "ntlm":
            request_auth = HttpNtlmAuth(auth.username, auth.password)
        elif auth_method == "basic":
            request_auth = HTTPBasicAuth(auth.username, auth.password)
        elif auth_method == "digest":
            request_auth = HTTPDigestAuth(auth.username, auth.password)

    try:
        logger.info("Reading entities...")

        logger.info("Reading file: %s" % (file))
        r = requests.get(file, auth=request_auth)
        r.raise_for_status()
        logger.debug("Got file data")
        workbook = xlrd.open_workbook("sesm.xsls", file_contents=r.content)
        sheetdata = []
        if workbook.props["modified"] > since:
            worksheet = workbook.sheet_by_index(sheet)
            if direction == "row":
                columnNames = getColNames(worksheet, names, start)
                sheetdata = getSheetRowData(worksheet, columnNames, start, ids, workbook.props["modified"], workbook.datemode)
            else:
                rowNames = getRowNames(worksheet, names, start)
                sheetdata = getSheetColData(worksheet, rowNames, start, ids, workbook.props["modified"], workbook.datemode)

        return Response(json.dumps(sheetdata), mimetype='application/json')

    except BaseException as e:
        logger.exception("Failed to read entities!")
        return Response(status=500, response="An error occured during generation of entities: %s" )


if __name__ == '__main__':
    # Set up logging
    format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logger = logging.getLogger('sharepoint-microservice')

    # Log to stdout
    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(stdout_handler)

    logger.setLevel(logging.DEBUG)

    app.run(threaded=True, debug=True, host='0.0.0.0', port=int(get_var('port') or 5000))

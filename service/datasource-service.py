from functools import wraps
from flask import Flask, request, Response, abort
import xlrd
import json
import os
import requests

import logging
import threading
import datetime
import base64

from sesamutils.flask import serve
from sesamutils import sesam_logger

app = Flask(__name__)
config_since = None

logger = sesam_logger('excel-datasource-service', app=app)

_lock_config = threading.Lock()


def datetime_format(dt):
    return '%04d' % dt.year + dt.strftime("-%m-%dT%H:%M:%SZ")


def to_transit_datetime(dt_int):
    return "~t" + datetime_format(dt_int)


def get_col_names(sheet,names,start):
    row_size = max([sheet.row_len(rowstart) for rowstart in names])
    row_values = [sheet.row_values(x, start[0], row_size) for x in names]
    return ['-'.join(row) for row in map(lambda *a: list(a), *row_values)]


def get_row_names(sheet,names,start):
    col_values = [sheet.col_values(x, start[1], sheet.nrows) for x in names]
    return ['-'.join(row) for row in map(lambda *a: list(a), *col_values)]


def get_row_data(row, column_names, start, ids, idx, lastmod, datemode, id_prefix):
    row_data = {}
    counter = 0
    id = None

    for cell in row:
        if counter in ids:
            if id:
                if isinstance(datemode, int):
                    id = id + "-" + str(cell.value)
                else:
                    id = id + "-" + str(cell.value, datemode)
            else:
                id = str(cell.value)
        if counter >= start:
            value = to_transit_cell(cell, datemode)
            row_data[column_names[counter - start]] = value
        counter += 1

    row_data["_id"] = id_prefix + (id or str(idx+1))
    if lastmod:
        row_data["_updated"] = lastmod
    return row_data


def get_col_data(col, row_names, start, ids, idx, lastmod, datemode, id_prefix):
    col_data = {}
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
            col_data[row_names[counter - start]] = value

        counter += 1

    col_data["_id"] =  id_prefix + (id or str(idx+1))
    if lastmod:
        col_data["_updated"] = lastmod
    return col_data


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
        logger.debug("Cell type Boolean with value: %s" % cell.value)
        if cell.value == 1:
            value = True
        elif cell.value == 0:
            value = False
    return value


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


def get_sheet_row_data(sheet, column_names, start, ids, lastmod, datemode, id_prefix):
    nrows = sheet.nrows
    for idx in range(start[1], nrows):
        row = sheet.row(idx)
        row_data = get_row_data(row, column_names, start[0], ids, idx, lastmod, datemode, id_prefix)
        yield row_data


def get_sheet_col_data(sheet, row_names, start, ids, lastmod, datemode, id_prefix):
    ncols = sheet.row_len(start[0])
    for idx in range(start[0], ncols):
        col = sheet.col(idx)
        col_data = get_col_data(col, row_names, start[1], ids, idx, lastmod, datemode, id_prefix)
        yield col_data


def get_envvar(var):
    envvar = os.getenv(var.upper()) or os.getenv(var.upper())
    logger.debug("Setting %s = %s" % (var, envvar))
    return envvar


def get_var(var):
    envvar = request.args.get(var)
    if not envvar:
        envvar = os.getenv(var.upper()) or os.getenv(var.upper())
    logger.debug("Setting %s = %s" % (var, envvar))
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


def generate_sheetdata(workbook, vars):
    sheet = vars.get('sheet', get_envvar('sheet')) or '1'
    sheets = [int(x) - 1 for x in sheet.split(',')]
    ids = vars.get('ids', get_envvar('ids')) or "0"
    ids = [int(x) - 1 for x in ids.split(',')]
    names = vars.get('names', get_envvar('names')) or "1"
    names = [int(x) - 1 for x in names.split(',')]
    direction = vars.get('direction', get_envvar('direction')) or "row"
    start = vars.get('start', get_envvar('start'))
    since = vars.get('since', "0001-01-01")

    if not start and direction == "row":
        start = "1,2"
    elif not start:
        start = "2,1"

    start = [int(x) - 1 for x in start.split(',')]
    modified = "modified" in workbook.props

    if modified:
        modified = workbook.props["modified"]

    if not modified or modified > since:
        iterable_sheets = sheets or range(0, workbook.nsheets)
        for sheet_index in iterable_sheets:
            worksheet = workbook.sheet_by_index(sheet_index)
            id_prefix = str(sheet_index+1) + "-" if len(iterable_sheets) > 1 else ""
            if direction == "row":
                column_names = get_col_names(worksheet, names, start)
                yield from get_sheet_row_data(worksheet, column_names, start, ids, modified, workbook.datemode, id_prefix)
            else:
                row_names = get_row_names(worksheet, names, start)
                yield from get_sheet_col_data(worksheet, row_names, start, ids, modified, workbook.datemode, id_prefix)


@app.route('/transform')    # add POST after done testing
def receiver():
    # For testing with source running locally:
    entities = requests.get("http://localhost:5000/entities").json()
    decoded = base64.b64decode(entities["content"])

    # encoded_bytes = request.json["content"]
    # decoded = base64.b64decode(encoded_bytes)

    vars = request.args
    do_stream = vars.get('do_stream', get_envvar('do_stream')) or 'true'
    do_stream = do_stream.lower() == 'true'

    workbook = xlrd.open_workbook('sesam.xsls', file_contents=decoded)
    try:
        response_data = []
        response_data_generator = stream_as_json(generate_sheetdata(workbook, vars))
        if do_stream:
            response_data = response_data_generator
        else:
            for entity in response_data_generator:
                response_data.append(entity)
        return Response(response=response_data, mimetype='application/json')

    except BaseException as e:
        logger.error("Failed to read entities!")
        logger.exception(e)
        return Response(status=500, response=str(e))


@app.route('/', methods=["GET"])
@app.route('/bypath/<path:path>', methods=["GET"])
@requires_auth
def get_entities(path=None):
    url = get_var('file')
    headers, params, auth = None, None, None
    if not url:
        download_request_spec = get_var('download_request_spec')
        if download_request_spec:
            download_request_spec = json.loads(download_request_spec)
            base_url = download_request_spec.get('base_url')
            headers = download_request_spec.get('headers')
            params = download_request_spec.get('params')
            auth = request.authorization
            if base_url:
                url = base_url
                if path or request.args.get('path'):
                    path_to_append = (path or request.args.get('path') or "")
                    path_to_append = path_to_append[1:] if path_to_append[0] == '/' else path_to_append
                    url = url[:-1] if url[-1] == '/' else url
                    url += '/' + path_to_append
                service_variables = ['file','sheet', 'ids','names','direction','start','since','do_stream', 'limit', 'path']
                for k, v in request.args.items():
                    if k not in service_variables:
                        params[k] = v
    if not url:
        abort(400, 'cannot figure out url to the file')

    logger.info("downloading from url=%s with params=%s" % (url, params))
    r = requests.get(url, auth=auth, headers=headers, params=params)
    r.raise_for_status()
    logger.debug("Got file data")
    workbook = xlrd.open_workbook("sesam.xsls", file_contents=r.content)

    vars = request.args
    do_stream = vars.get('do_stream', get_envvar('do_stream')) or 'true'
    do_stream = do_stream.lower() == 'true'

    try:
        response_data = []
        response_data_generator = stream_as_json(generate_sheetdata(workbook, vars))
        if do_stream:
            response_data = response_data_generator
        else:
            for entity in response_data_generator:
                response_data.append(entity)
        return Response(response=response_data, mimetype='application/json')

    except BaseException as e:
        logger.error("Failed to read entities!")
        logger.exception(e)
        return Response(status=500, response=str(e))


if __name__ == '__main__':
    serve(app, port=int(os.environ.get('PORT', "5001")))

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


def getColNames(sheet,names,start):
    rowSize = max([sheet.row_len(rowstart) for rowstart in names])
    rowValues = [sheet.row_values(x, start[0], rowSize) for x in names]
    return  ['-'.join(row) for row in map(lambda *a: list(a), *rowValues)]


def getRowNames(sheet,names,start):
    colValues = [sheet.col_values(x, start[1], sheet.nrows) for x in names]
    return  ['-'.join(row) for row in map(lambda *a: list(a), *colValues)]


def getRowData(row, columnNames, start, ids, idx, lastmod, datemode, id_prefix):
    rowData = {}
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
        if counter>=start:
            value = to_transit_cell(cell, datemode)
            rowData[columnNames[counter - start]] = value
        counter += 1
    rowData["_id"] = id_prefix + (id or str(idx+1))
    if lastmod:
        rowData["_updated"] = lastmod
    return rowData


def getColData(col, rowNames, start, ids, idx, lastmod, datemode, id_prefix):
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
            colData[rowNames[counter - start]] = value


        counter += 1
    colData["_id"] =  id_prefix + (id or str(idx+1))
    if lastmod:
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


def getSheetRowData(sheet, columnNames, start, ids, lastmod, datemode, id_prefix):
    nRows = sheet.nrows
    for idx in range(start[1], nRows):
        row = sheet.row(idx)
        rowData = getRowData(row, columnNames, start[0], ids, idx, lastmod, datemode, id_prefix)
        yield rowData

def getSheetColData(sheet, rowNames, start, ids, lastmod, datemode, id_prefix):
    nCols = sheet.row_len(start[0])
    for idx in range(start[0], nCols):
        col = sheet.col(idx)
        colData = getColData(col, rowNames, start[1], ids, idx, lastmod, datemode, id_prefix)
        yield colData


def get_envvar(var):
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
        auth_method = request.args.get("auth", get_envvar('auth')) or "none"

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
                column_names = getColNames(worksheet, names, start)
                yield from getSheetRowData(worksheet, column_names, start, ids, modified, workbook.datemode, id_prefix)
            else:
                row_names = getRowNames(worksheet, names, start)
                yield from getSheetColData(worksheet, row_names, start, ids, modified, workbook.datemode, id_prefix)


def extract_content(entity):
    """
    Given an entity, attempt to find "content" (encoded bytes) and "content-type" (Mime type of file).
    """

    content = None
    content_type = None

    for key in entity.keys():
        if "content" in key.split(":"):
            content = entity[key]
        if "content-type" in key.split(":"):
            content_type = entity[key]

    return content, content_type


@app.route('/transform', methods=["POST"])
def receiver():
    """
    Decode encoded bytes from a POST request back into an Excel sheet and return as a JSON.
    """

    valid_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    encoded_bytes, file_type = extract_content(request.json[0])

    if file_type != valid_type:
        logger.warning("Content type does not match that of an Excel sheet: got '%s', expected '%s'."
                       "Decoded content may not be correct." % (file_type, valid_type))

    if encoded_bytes is None:
        return Response(status=404, response="Unable to extract content. Incoming POST request must contain a single "
                                             "entity with a field on the form 'namespace:content': '<encoded bytes>'")

    decoded = base64.b64decode(encoded_bytes)

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
    vars = request.args
    url = vars.get('file', get_envvar('file'))
    headers, params, auth = None, None, None
    if not url:
        download_request_spec = vars.get('download_request_spec', get_envvar('download_request_spec'))
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
    serve(app, port=int(os.environ.get('PORT', "5000")))

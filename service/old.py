file = get_var('file')
sheet = int(get_var('sheet') or 1) - 1
ids = get_var('ids') or "0"
ids = [int(x) - 1 for x in ids.split(',')]
names = get_var('names') or "1"
names = [int(x) - 1 for x in names.split(',')]
direction = get_var('direction') or "row"
start = get_var('start')
if not start and direction == "row":
    start = "1,2"
elif not start:
    start = "2,1"
start = [int(x) - 1 for x in start.split(',')]
logger.info("Get %s using request: %s" % (file, request.url))
since = request.args.get('since') or "0001-01-01"

request_auth = None
auth_method = get_var('auth') or "none"

# if auth_method != "none":
#     auth = request.authorization
#     if auth_method == "ntlm":
#         request_auth = HttpNtlmAuth(auth.username, auth.password)
#     elif auth_method == "basic":
#         request_auth = HTTPBasicAuth(auth.username, auth.password)
#     elif auth_method == "digest":
#         request_auth = HTTPDigestAuth(auth.username, auth.password)

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
            sheetdata = getSheetRowData(worksheet, columnNames, start, ids, workbook.props["modified"],
                                        workbook.datemode)
        else:
            rowNames = getRowNames(worksheet, names, start)
            sheetdata = getSheetColData(worksheet, rowNames, start, ids, workbook.props["modified"], workbook.datemode)

    return Response(json.dumps(sheetdata), mimetype='application/json')

except BaseException as e:
    logger.exception("Failed to read entities!")
    return Response(status=500, response="An error occured during generation of entities: %s")
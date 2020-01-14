
import xlrd
import requests
import logging
import datetime

logging = logging.getLogger('filehandling')
def get_file_by_row(file_url,ids,names,start,since,sheets):
    """
    opens the workbook on_demand, one sheet at a time and releases each sheet after reading
    itterates over each sheet, store a sheet id and sheet names - names of colums
    yields a row at a time with sheet_id, sheet_name as a list

    """
    logging.info("get file by row")
    r = requests.get(file_url, auth=None)
    r.raise_for_status()
    with xlrd.open_workbook("sesam.xsls", file_contents=r.content, on_demand=True) as Workbook:
        try:
            if Workbook.props["modified"] > since:
                for sheet in sheets or range(0,Workbook.nsheets):
                    logging.debug("opening sheet: ", sheet)
                    workSheet = Workbook.sheet_by_index(sheet)
                    sheetNames = get_col_names(workSheet,names,start["col"])
                    for row in range(start["row"],workSheet.nrows):
                        yield get_row_data(workSheet.row(row), sheetNames, ids, row, Workbook.props["modified"],  Workbook.datemode,sheet)
                    Workbook.unload_sheet(sheet)
            Workbook.release_resources()
        except Exception as e:
            logging.error("Failed when opening workbook, error -", {e})
            Workbook.release_resources()

def get_file_by_col(file_url,ids,names,start,since,sheets):
    logging.info("get file by col")
    r = requests.get(file_url, auth=None)
    r.raise_for_status()
    with xlrd.open_workbook("sesm.xsls", file_contents=r.content, on_demand=True) as Workbook:
        try:
            if Workbook.props["modified"] > since:
                for sheet in sheets or range(0,Workbook.nsheets):
                    logging.debug("opening sheet: ", sheet)
                    workSheet = Workbook.sheet_by_index(sheet)
                    sheetNames = get_row_names(workSheet,names,start["row"])
                    for col in range(start["col"],workSheet.ncols):
                        yield get_col_data(workSheet.col(col), sheetNames, start["col"], ids, col,Workbook.props["modified"],  Workbook.datemode,sheet)
                    Workbook.unload_sheet(sheet)
        except:
            logging.error("Error in opening workbook, error - " ,{e})
            Workbook.release_resources()

def get_col_names(workSheet,names,start):
    """
    Returns the name field in the specified worksheet
    """
    rowSize = max([workSheet.row_len(rowstart) for rowstart in names])
    rowValues = [workSheet.row_values(x, start, rowSize) for x in names]
    return  rowValues[0]


def get_row_names(sheet,names,start):
    colValues = [sheet.col_values(x, start, sheet.nrows) for x in names]
    print(colValues)
    return  colValues[0]



def get_row_data(row, columnNames, ids, col,lastmod,  datemode,sheet):
    rowData={}

    id = None
    counter=0
    for cell in row:
        if counter in ids:
            if id:
                id = id + "-" + str(cell.value, datemode)
            else:
                id = str(cell.value)
        value = to_transit_cell(cell, datemode)
        rowData[columnNames[counter]] = value
        counter += 1
    rowData["_id"] =  set_id(id,col,sheet)
    rowData["_updated"] = lastmod

    return rowData



def get_col_data(col, rowNames, start, ids, idx, lastmod, datemode,sheet):
    """
    get all data from colums specified by start
    """
    counter = 0
    colData={}
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
        colData["_id"] = set_id(id,idx,sheet)
        colData["_updated"] = lastmod
        return colData

def set_id(id, col, sheet):
    if id:
        return id + "-" + str(sheet)
    else:
        return str(col) + "-" + str(sheet)

def to_transit_cell(cell, datemode):
    """
    returns the value of the specified cell based on cell type- convert to correct format
    """
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
            value = True
        elif cell.value == 0:
            value = False
    return value


def get_sheet_row_data(sheet, columnNames, start, ids, lastmod, datemode):
    nRows = sheet.nrows


    for idx in range(start[1], nRows):
        row = sheet.row(idx)
        rowData = getRowData(row, columnNames, start[0], ids, idx, lastmod, datemode)
        yield rowData



def getSheetColData(sheet, rowNames, start, ids, lastmod, datemode):
    nCols = sheet.row_len(start[0])


    for idx in range(start[0], nCols):
        col = sheet.col(idx)
        colData = getColData(col, rowNames, start[1], ids, idx, lastmod, datemode)
        yield colData


def valid_request(requestData,requiredVars,optionalVars):
    """
    Check that all the required data is in the request,
    """
    required = 0
    start = requestData.get("start")
    if start:
            if start.get("row") != None and start.get("col") != None:
                pass
            else:
                logging.error("row or col not defined in start")
                return False
    for var in requestData:
        if var in requiredVars:
            required += 1
        elif var in optionalVars:
            pass
        else:
            logging.error("variable, {var},  not known ")
    if required >= len(requiredVars):
        return True
    else:
        logging.error("Missing required Variable")
        return False

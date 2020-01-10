from functools import wraps
from flask import Flask, request, Response, abort
import xlrd
import json
import os
import requests
# from requests_ntlm import HttpNtlmAuth
# from requests.auth import HTTPBasicAuth
# from requests.auth import HTTPDigestAuth

import logging

logging = logging.getLogger('filehandling')
def get_file_by_row(fileUrl,ids,names,start,since):
    """
    Open the whole file a sheet at the time
    itterates over each sheet, store a sheet id and sheet names - names of colums
    yields a row at a time with sheet_id, sheet_name as a list

    """
    print("get file by row")
    r = requests.get(fileUrl, auth=None)
    print(r.status_code)
    r.raise_for_status()
    with xlrd.open_workbook("sesm.xsls", file_contents=r.content, on_demand=True) as Workbook:
        if Workbook.props["modified"] > since:
            try:
                for sheet in range(0,Workbook.nsheets):
                    print("opening sheet")
                    workSheet = Workbook.sheet_by_index(sheet)
                    sheetNames = get_col_names(workSheet,names,start)
                    #print(type(sheetNames))
                    sheetNames.append('_sheet-nr')
                    print(sheetNames)
                    for row in range(workSheet.nrows):
                        yield get_row_data(workSheet.row(row), sheetNames, start[0], ids, row,since,  Workbook.datemode,sheet)
                    ###close sheet after reading
                    print("Closing sheet")
                    Workbook.unload_sheet(sheet)
            except:
                print(type(sheetNames))

def get_file_by_col():
    r = request.get(file_url, auth=request_auth)

    r.raise_for_status()
    with xlrd.open_workbook("sesm.xsls", file_contents=r.contents, on_demand=True) as Workbook:
        if Workbook.props["modified"] > since:
            for sheet in range(0,Workbook.nsheets):

                workSheet = Workbook.sheet_by_index(sheet)
                sheetNames = get_row_names(sheet,names,start)
                #print(sheetNames)
                for col in range(sheetData.ncols):
                    sheetData = get_col_data(workSheet, sheetNames, start, ids,col, Workbook.props["modified"], Workbook.datemode,sheet)
                    print(type(sheetData))
                    yield sheetData
                ###close sheet after reading
                Workbook.unload_sheet(sheet)


def get_col_names(workSheet,names,start):
    rowSize = max([workSheet.row_len(rowstart) for rowstart in names])
    rowValues = [workSheet.row_values(x, start[0], rowSize) for x in names]
    return  ['-'.join(row) for row in map(lambda *a: list(a), *rowValues)]


def get_row_names(sheet,names,start):
    colValues = [sheet.col_values(x, start[1], sheet.nrows) for x in names]
    return  ['-'.join(row) for row in map(lambda *a: list(a), *colValues)]



def get_row_data(row, columnNames, start, ids, idx,lastmod,  datemode,sheet):
    rowData={}
    id = None
    counter=0

    for cell in row:
        if counter in ids:
            if id:
                id = id + "-" + str(cell.value, datemode)
            else:
                id = str(cell.value)
        if counter>=start:
            value = to_transit_cell(cell, datemode)
            rowData[columnNames[counter - start]] = value
        counter += 1
    rowData["_id"] = id or str(idx+1)
    rowData["_updated"] = lastmod
    rowData["sheet_nr"] = sheet
    return rowData

def get_col_data(col, rowNames, start, ids, idx, lastmod, datemode,sheet):
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
        colData["_id"] = id or str(idx)+1
        colData["_updated"] = lastmod
        colData["sheet_nr"] = sheet
        yield colData


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


def get_full_file():
    """
    Open the whole file a sheet at the time
    itterates over each sheet, store a sheet id and sheet names - names of colums or rows
    yields a row/col at a time with row/col data, sheet_id, sheet_name as a list

    """
    r = request.get(file_url, auth=request_auth)
    r.raise_for_status()
    logger.debug("got file data")
    with xlrd.open_workbook("sesm.xsls", file_contents=r.contents, on_demand=True) as Workbook:
        if Workbook.props["modified"] > since:
            for sheet in range(0,Workbook.nsheets):
                sheetdata = Workbook.sheet_by_index(i)
                sheet_names = get_col_names() if dir == "row" else get_row_names()
                for rows in range(sheet_data.nrows)
                    sheet_row_data = get_row_data() if dir == "row" else get_col_data()
                    yield sheet_row_data
                ###close sheet before opening next







def get_sheet():
    pass



def sheet_gen(sheetdata,Workbook):
    if direction == "row":
                columnNames = getColNames(worksheet, names, start)
                yield getSheetRowData(worksheet, columnNames, start, ids, workbook.props["modified"], Workbook.datemode)
            else:
                rowNames = getRowNames(worksheet, names, start)
                yield = getSheetColData(worksheet, rowNames, start, ids, workbook.props["modified"], Workbook.datemode)

def get_col_names():
    pass

def get_row_names():
    pass

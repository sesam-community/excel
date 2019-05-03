# sesam-datasource-excel
Sample Excel REST datasource for Sesam

[![Build Status](https://travis-ci.org/sesam-community/excel.svg?branch=master)](https://travis-ci.org/sesam-community/excel)

The service tekes the following parameters:

`file = Full URL for the file supporting HTTP get and NTLM security`

`sheet = What sheet in the workbook to use, starting from 1 (Default = 1)`

`start = What row and column in the sheet to start fetching data, comma separated. Firt row/column = 1 (Default = 1,1)`

`direction = What direction the data is stored; row, og col. (Default = row)`

`ids = The rows or columns containg id values, comma separated. (Default = row- or column-number)`

`names = The rows or columns containg property names, comma separated. (Default = 1)`

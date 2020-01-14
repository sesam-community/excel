# sesam-datasource-excel
Sample Excel REST datasource for Sesam

[![Build Status](https://travis-ci.org/sesam-community/excel.svg?branch=master)](https://travis-ci.org/sesam-community/excel)

The service tekes the following parameters:

`file = Full URL for the file supporting HTTP get and NTLM security`

`sheet = List of the sheets to be read, default to None. first sheet is [0]`

`start = What row and column in the sheet to start fetching data, takes an input as a dictionary {"row":<row>,"col" :<col>} default {"row":1,"col":0}`

`direction = What direction the data is stored; row, or col. (Default = row)`

`ids = The rows or columns containg id values, as a list of str (Default ids= ["-1"]) not defined`

`names = The rows or columns containg property names, as a list of ints, default, names= [0]


If ids is not set in document, _id will be set as the row/col number with the sheet number attached. ex ("_id":"1-0"), data from second row first sheet.



For further update of the MS check out Pandas https://pandas.pydata.org/pandas-docs/stable/user_guide/io.html#excel-files

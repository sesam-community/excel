
# sesam-datasource-excel
Sample Excel REST datasource for Sesam


[![Build Status](https://travis-ci.org/sesam-community/excel.svg?branch=master)](https://travis-ci.org/sesam-community/excel)

_id is set as "<row_number> - <sheet_nr>" example id: excel:5093-0
all sheets/row/col are 0 indexed. 

The service takes the following parameters:
app.route is set to /get_excel and all parameters is added in pipe after the query string set in url file_url is required
ex in pipe config:

"url": "get_excel?file_url=<file_url>"

`file_url = Full URL for the file supporting HTTP get and NTLM security, currently auth is set to None`

`sheet = List of the sheets to be read, default to None. first sheet is [0]`

`start = What row and column in the sheet to start fetching data, takes an input as a dictionary {"row":<row>,"col" :<col>} default {"row":1,"col":0}`

`direction = What direction the data is stored; row, or col. (Default = row)`

`ids = The rows or columns containg id values, as a list of str (Default ids= ["-1"]) not defined`

`names = The rows or columns containg property names, as a list of ints, default, names= [0]`


If ids is not set in document, _id will be set as the row/col number with the sheet number attached. ex ("_id":"1-0"), data from second row first sheet.

### Running the app in Sesam.
***Example of system config:***

```
{
  "_id": "<name_of_microservice>",
  "type": "system:microservice",
  "docker": {
    "environment": {
      "log_level": "DEBUG"
    },
    "image": "<docker_image>",
    "port": <port>
  },
  "verify_ssl": true
}
```


**Example of pipe config:**

```
{
  "_id": "<name>",
  "type": "pipe",
  "source": {
    "type": "json",
    "system": "<system_id>",
    "is_chronological": true,
    "is_since_comparable": true,
    "supports_since": true,
    "url": "get_excel?file_url=<file_url> & ids = <ids>
  },
  "transform": {
    "type": "dtl",
    "rules": {
      "default": [
        ["copy", "*"]
      ]
    }
  }
}
```



For further update of the MS check out Pandas https://pandas.pydata.org/pandas-docs/stable/user_guide/io.html#excel-files

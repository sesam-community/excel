# sesam-datasource-excel
Sample Excel REST datasource for Sesam

[![Build Status](https://travis-ci.org/sesam-community/excel.svg?branch=master)](https://travis-ci.org/sesam-community/excel)


### Service parameters:

#### Either as query parameter or env var:

| CONFIG_NAME        | DESCRIPTION           | DEFAULT_VALUE|
| -------------------|---------------------|:-----------------------:|
| file | Full URL for the file supporting HTTP get| n/a |
| sheet¹|  What sheet(s) in the workbook to use, comma separated, starting from 1 | 1 |
| start | What row and column in the sheet to start fetching data, comma separated. Firt row/column = 1| 1,1 |
| direction | What direction the data is stored; row, og col. | row |
| ids | The rows or columns containing id values, comma separated |1 |
| names | The rows or columns containg property names, comma separated. | 1 |
| do_stream | boolean flag to toggle streamed response | "true" |

¹:when specified as csv, entity id will be prefixed by sheet number (starting from 1) and "-"
#### Only as env var:
| CONFIG_NAME        | DESCRIPTION           | DEFAULT_VALUE|
| -------------------|---------------------|:-----------------------:|
| DOWNLOAD_REQUEST_SPEC | dict to configure the file fetching request. Properties: _base_url_ = string of base url for the download, _headers_ = dict of headers, _params_ = dict of params that is common to all requests| n/a |
| PORT |  port number for the service to run on |5000 |
| LOG_LEVEL | log level | "INFO" |

#### Only as query params:
| CONFIG_NAME        | DESCRIPTION           | IS_REQUIRED  |DEFAULT_VALUE|
| -------------------|---------------------|:------------:|:-----------:|
| path | string of url path,optionally with query params, that will be appended to download_request_spec.base_url to constitute the final url| no | n/a |

## Notes
* Url to the file is figured out by _i)_ _FILE_ env var, _ii)_ _FILE_ query param, _iii)_ _DOWNLOAD_REQUEST_SPEC_ env var combine with the path in the request to the service or _iv)_ DOWNLOAD_REQUEST_SPEC_ env var combine with the _path_ query param.

## Example setups:

system:
```
{
    "_id": "my_excel_datasource",
    "type": "system:microservice",
    "connect_timeout": 60,
    "docker": {
        "environment": {
            "DOWNLOAD_REQUEST_SPEC": {
                "base_url": "http://my_domain/my_apiversion",
                "headers": {
                    "my_header": "my_headervalue"
                },
                "params": {
                    "my_queryparam_common_to_all_requests": "some value"
                }
            }
        },
        "image": "sesamcommunity/excel:<version>",
        "port": 5000
    },
    "read_timeout": 7200
}
```
pipe:
```
...
    {
      "type": "json",
      "system": "myexceldatasource",
      "url": "/mypath1/myexcelfile.xlsx?sheet=1&direction=col&do_stream=true&my_queryparam_specific_to_this_request=somevalue"
    },
...
```

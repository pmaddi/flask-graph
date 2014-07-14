# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json, urllib, httplib
import datetime, time
from optparse import OptionParser
import sys
import os

SERVER = 'graphs.mozilla.org'
selector = '/api/test/runs'

debug = 1

def getGraphData(testid, branchid, platformid):
    body = {"id": testid, "branchid": branchid, "platformid": platformid}
    if debug >= 3:
        print "Querying graph server for: %s" % body
    params = urllib.urlencode(body)
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    conn = httplib.HTTPConnection(SERVER)
    conn.request("POST", selector, params, headers)
    response = conn.getresponse()
    data = response.read()

    if data:
        try:
            data = json.loads(data)
        except:
            print "NOT JSON: %s" % data
            return None

    if data['stat'] == 'fail':
        return None
    return data

if __name__ == '__main__':
    print getGraphData(83,1,33)
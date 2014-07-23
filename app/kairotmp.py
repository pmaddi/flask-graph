from urlparse import urljoin
import requests
from bs4 import BeautifulSoup
import re
import datetime
import time





def addDictsTotal (x, y):
    return {'total':int(x.get('total', 0)) + int(y.get('total', 0))}

def mergeDictsTotal (x, y):
    return { k: addDictsTotal(x.get(k, {}), y.get(k, {})) for k in set(x) | set(y) }

def sumDictsTotal (dictList):
    return reduce (mergeDictsTotal, dictList, {})

def startupCrashes(version):
    u1 = "https://crash-analysis.mozilla.com/rkaiser/"
    r = requests.get("https://crash-analysis.mozilla.com/rkaiser/").text
    s = BeautifulSoup (r)

    hrefs = s.find_all(href=True)
    sums = sumDictsTotal ( [ \
        requests.get(urljoin(u1,f['href'])).json() \
        for f \
        in hrefs \
        if re.search('ff-.*'+str(version)+'.*startup.*json', str(f))] )
    return { k: sums[k]['total'] for k in sums.keys() }




def daysList(day1, day2):
    # Both days are ymd strings
    day1 = datetime.datetime.strptime(str(day1), "%Y-%m-%d")
    day2 = datetime.datetime.strptime(str(day2), "%Y-%m-%d")

    days = []

    while day1 < day2:
        days.append( day1.isoformat()[0:10] )
        day1 += datetime.timedelta(days=1)
    return days

print daysList('2014-01-03', '2014-04-22')

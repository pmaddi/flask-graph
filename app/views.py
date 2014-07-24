from flask import render_template, flash, redirect, session, url_for, request, g, jsonify
from app import app
import time
import datetime
import requests
import concurrent.futures 
import numpy as nm
import json
from flask_cors import cross_origin
from urlparse import urljoin
from bs4 import BeautifulSoup
import re

import urllib
import httplib
# import datetime, time
from optparse import OptionParser
# import sys
# import os
# import json

# The URL :kaiRo maintains that stores ADI and crashes per version
CrashdataURL = "https://crash-analysis.mozilla.com/rkaiser/Firefox-daily.json"

# The URL for the API of talos refrences of talos maintained in the datazilla format
TalosURL = 'https://datazilla.mozilla.org/refdata/pushlog/list/'

def unixTime(dtime):
	"""Convert a given year-month-date string into a unix time""" 
	if dtime:
		return time.mktime(datetime.datetime.strptime(str(dtime), "%Y-%m-%d").timetuple())
	else:
		return 0

def ymdTime(utime):
	"""Convert a given a unix time into a year-month-date string""" 
	return datetime.date.fromtimestamp(utime/1000).isoformat()

def daysList(day1, day2):
	# Both days are ymd strings
	day1 = datetime.datetime.strptime(str(day1), "%Y-%m-%d")
	day2 = datetime.datetime.strptime(str(day2), "%Y-%m-%d")
	
	days = []

	while day1 < day2:
		days.append( day1.isoformat()[0:10] )
		day1 += datetime.timedelta(days=1)
	return days

def addDicts (x, y):
	return { k: x.get(k, 0) + y.get(k, 0) for k in set(x) | set(y) }

def mergeDicts (x, y):
	return { k: addDicts(x.get(k, {}), y.get(k, {})) for k in set(x) | set(y) }

def sumDicts (dictList):
	return reduce (mergeDicts, dictList, {})

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


def getGraphData(testid, branchid, platformid):
	SERVER = 'graphs.mozilla.org'
	selector = '/api/test/runs'
	debug = 1
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
	return { i[2] : i[3] for i in data['test_runs'] }



@app.route('/_get_data', methods=['POST'])
@cross_origin()
# The endpoint where the data from each source can be accessed
def get_graph():

	if request.form['source'] == 'graphs':
		# Define default params for the API
		request_params = {
			'end_date':'2020-07-01',
			'start_date':'2000-01-01',
			'branch':83,
			'test':1,
			'platform':33,
		}

		# Update defaults with user specified data
		form_data = json.loads(request.form['data'])
		request_params.update(form_data)

		# Convert the soft tags into the correct format
		if len(str(request_params['end_date'])) > 10:
			request_params['end_date'] = ymdTime( int (request_params['end_date']) );

		if len(str(request_params['start_date'])) > 10:
			request_params['start_date'] = ymdTime( int (request_params['start_date']) );	

		# Select the version from the data
		data = []
		days = daysList(request_params['start_date'], request_params['end_date'])

		graphdata = getGraphData (request_params['branch'], request_params['test'], request_params['platform'])
		# Only use if falls in daterange
		for day in graphdata.keys():
			if (unixTime(request_params['start_date']) <=  int(day) and unixTime(request_params['end_date']) >=  int(day) ):
				data.append({ \
					'x':int(day), \
					'y':float(graphdata[day])
				})

		# TODO try this out!!!
		data.sort(key=lambda v: v['x'])

		return jsonify(series_data = data, request_params = request_params)


	if request.form['source'] == 'crash-stats':

		# Define default params for the API
		request_params = {
			'end_date':'2020-07-01',
			'product':'Firefox',
			'start_date':'2000-01-01',
			'version':'32',
			'query':'crashesperadu' # crashesperadu, crashes, adu, startupcrashes
		}

		# Update defaults with user specified data
		form_data = json.loads(request.form['data'])
		request_params.update(form_data)

		# Convert the soft tags into the correct format
		if len(str(request_params['end_date'])) > 10:
			request_params['end_date'] = ymdTime( int (request_params['end_date']) );

		if len(str(request_params['start_date'])) > 10:
			request_params['start_date'] = ymdTime( int (request_params['start_date']) );	

		# Select the version from the data
		data = []

		days = daysList(request_params['start_date'], request_params['end_date'])


		# Pull in the data from the crash-stats pages
		crashdata = requests.get(CrashdataURL).json()

		# Get all valid versions
		request_crashdata = sorted([ crashdata[k] for k in crashdata.keys() if k[0:2] == str(request_params['version'])])
		crashdata_version = sumDicts (request_crashdata)


		if request_params['query'] == 'startupcrashes':
			crashdata_version = startupCrashes (request_params['version'])
			# Only use if falls in daterange
			for day in days:
				# If we have data for it
				if (day in crashdata_version.keys()):
					data.append({ \
						'x':unixTime(day), \
						'y':float(crashdata_version[day])
					})
				else:
					data.append({ \
						'x':unixTime(day), \
						'y':0
					})
		elif request_params['query'] == 'crashesperadu':
			for day in days:
				# If we have data for it
				if (day in crashdata_version.keys()):
					data.append({ \
						'x':unixTime(day), \
						# Divide by ADI when specified.
						'y':float(crashdata_version[day]['crashes'])/float(crashdata_version[day]['adu'])
					})
				else:
					data.append({ \
						'x':unixTime(day), \
						'y':0
					})
		elif request_params['query'] == 'adu':
			for day in days:
				# If we have data for it
				if (day in crashdata_version.keys()):
					data.append({ \
						'x':unixTime(day), \
						'y':crashdata_version[day]['adu']
					})
				else:
					data.append({ \
						'x':unixTime(day), \
						'y':0
					})
		elif request_params['query'] == 'crashes':
			for day in days:
				# If we have data for it
				if (day in crashdata_version.keys()):
					data.append({ \
						'x':unixTime(day), \
						'y':crashdata_version[day]['crashes']
					})
				else:
					data.append({ \
						'x':unixTime(day), \
						'y':0
					})
		else:
			for day in days:
				data.append({ \
					'x':unixTime(day), \
					'y':0
				})

		# Organize data for the frontend
		data.sort(key=lambda v: v['x'])

		return jsonify(series_data = data, request_params = request_params)

	elif request.form['source'] == 'talos':
		# Define default params for the API
		request_params = {
			'days_ago':1,
			'product':'Firefox',
			'os_name':'linux',
			'os_version':'Ubuntu 12.04',
			'branch_version':'33.0a1',
			'processor':'x86',
			'build_type':'opt',
			'test_name':'ts_paint',
			'title':'talos',
			'version':' '
		}

		# Update defaults with user specified data
		form_data = json.loads(request.form['data'])
		request_params.update(form_data)

		# Get all the refrences
		r = requests.get(TalosURL+'?days_ago='+str(request_params['days_ago'])+'&branches=Mozilla-Inbound')
		refrences = []
		for elm in r.json():
			refrences.extend(r.json()[elm]['revisions'])

		def fetchData(elm):
			r = requests.get('https://datazilla.mozilla.org/talos/testdata/raw/Mozilla-Inbound/'+elm, params = request_params)
			return r.json()

		res = []
		# Run the queries cuncurrently to speed em up a bit
		# Use ThreadPool since its faster for network operations
		# We can use a with statement to ensure threads are cleaned up promptly
		with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
			# Start the load operations and mark each future with its URL
			future_to_url = {executor.submit(fetchData, url): url for url in refrences}
			for future in concurrent.futures.as_completed(future_to_url):
				url = future_to_url[future]
				try:
					data = future.result()
				except Exception as exc:
					print('%r generated an exception: %s' % (url, exc))
				else:
					if data:
						data = {'x':data[0]['testrun']['date'], 'y':nm.mean(data[0]['results'][request_params['test_name']])}
						res.append(data)
		data = res

		# Organize data for frontend
		data.sort(key=lambda v: v['x'])
		return jsonify(series_data = data, request_params = request_params)


@app.route('/')
@app.route('/index')
def index():
	return render_template('index.html')
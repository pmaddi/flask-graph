from flask import render_template, flash, redirect, session, url_for, request, g, jsonify
from app import app
import time
import datetime
import requests
import concurrent.futures 
import numpy as nm
import json
from flask_cors import cross_origin

# The URL :kaiRo maintains that stores ADI and crashes per version
CrashdataURL = "https://crash-analysis.mozilla.com/rkaiser/Firefox-daily.json"

# The URL for the API of talos refrences of talos maintained in the datazilla format
TalosURL = 'https://datazilla.mozilla.org/refdata/pushlog/list/'

def unixTime(dtime):
	"""Convert a given year-month-date string into a unix time""" 
	return time.mktime(datetime.datetime.strptime(str(dtime), "%Y-%m-%d").timetuple())

@app.route('/_get_data', methods=['POST'])
@cross_origin()
# The endpoint where the data from each source can be accessed
def get_graph():
	if request.form['source'] == 'crash-stats':

		# Pull in the data from the crash-stats pages
		crashdata = requests.get(CrashdataURL).json()

		# Define default params for the API
		request_params = {
			'end_date':'2020-07-01',
			'product':'Firefox',
			'start_date':'2000-01-01',
			'version':'32.0a1',
			'perADI':'1',
			'query':'CrashTrends'
		}

		# Update defaults with user specified data
		form_data = json.loads(request.form['data'])
		request_params.update(form_data)

		# Select the version from the data
		crashdata_version = crashdata[request_params['version']]
		data = []

		# Specify format based on "perADI"
		if request_params['perADI'] == '1':
			for day in crashdata_version.keys():
				# Only use if falls in daterange
				if (unixTime(day) < unixTime(request_params['end_date'])) \
				and (unixTime(day) > unixTime(request_params['start_date'])):
					data.append({ \
						'x':unixTime(day), \
						# Divide by ADI when specified.
						'y':float(crashdata_version[day]['crashes'])/float(crashdata_version[day]['adu'])
					})
		else:
			for day in crashdata_version.keys():
				# Only use if falls in daterange
				if (unixTime(day) < unixTime(request_params['end_date'])) \
				and (unixTime(day) > unixTime(request_params['start_date'])):
					data.append({ \
						'x':unixTime(day), \
						'y':crashdata_version[day]['crashes']
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
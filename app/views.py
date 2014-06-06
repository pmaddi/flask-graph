from flask import render_template, flash, redirect, session, url_for, request, g, jsonify
from app import app
import time
import datetime
import requests
import concurrent.futures 
import numpy as nm
from flask_cors import cross_origin

def unixTime(dtime):
	return time.mktime(datetime.datetime.strptime(str(dtime), "%Y-%m-%d").timetuple())

@app.route('/_add_numbers')
def add_numbers():
    a = request.args.get('a', 0, type=int)
    b = request.args.get('b', 0, type=int)
    return jsonify(result=a + b)

@app.route('/_get_data', methods=['POST'])
@cross_origin()
def get_graph():
	if request.form['api'] == 'crash-stats':
		request_params = {
				'end_date':'2014-07-01',
				'product':request.form['product'],
				'start_date':'2000-01-01',
				'version':request.form['version']
			}
		r = requests.get('https://crash-stats.mozilla.com/api/'+request.form['query']+'/',
			params = request_params)

		# Create an object to pass that indexes by report_date
		# each report_date key has a data and value object 
		# data is the bulid_date and number of crashes
		# value is the total number of crashes over all builds
		crashes = {}
		for crash in r.json()['crashtrends']:
			if unixTime(crash['report_date']) in crashes.keys():
				crashes[unixTime(crash['report_date'])]['data']\
				.update({unixTime(crash['build_date']): int(crash['report_count'])})
				crashes[unixTime(crash['report_date'])]['value'] = \
				crashes[unixTime(crash['report_date'])]['value'] + int(crash['report_count'])
			else:
				crashes[unixTime(crash['report_date'])] = \
				{'data': {unixTime(crash['build_date']): int(crash['report_count'])}
				, 'value':int(crash['report_count'])}
		
		# convert to proper rickshaw format
		# [{x:x,y:y,y0:0},...]
		data = []
		for key in crashes.keys():
			data.append({'x':key,'y':crashes[key]['value']})
		data.sort(key=lambda v: v['x'])

		return jsonify(series_data = data, request_params = request_params)

	elif request.form['api'] == 'talos':
		request_params = {
			'product':'potato',
			'version':'2345'
		}
		r = requests.get('https://datazilla.mozilla.org/refdata/pushlog/list/?days_ago=1&branches=Mozilla-Inbound')
		out = []
		for elm in r.json():
			out.extend(r.json()[elm]['revisions'])
		# print out

		def printRequest(elm):
			r = requests.get('https://datazilla.mozilla.org/talos/testdata/raw/Mozilla-Inbound/'+elm+'?product=Firefox&os_name=linux&os_version=Ubuntu%2012.04&branch_version=32.0a1&processor=x86&build_type=opt&test_name=ts_paint')
			return r.json()

		res = []
		# We can use a with statement to ensure threads are cleaned up promptly
		with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
		    # Start the load operations and mark each future with its URL
		    future_to_url = {executor.submit(printRequest, url): url for url in out}
		    for future in concurrent.futures.as_completed(future_to_url):
		        url = future_to_url[future]
		        try:
		            data = future.result()
		        except Exception as exc:
		            print('%r generated an exception: %s' % (url, exc))
		        else:
		            if data:
		                data = {'x':data[0]['testrun']['date'], 'y':nm.mean(data[0]['results']['ts_paint'])}
		                # print data
		                res.append(data)
		data = res
		data.sort(key=lambda v: v['x'])
		return jsonify(series_data = data, request_params = request_params)


@app.route('/')
@app.route('/index')
@cross_origin()
def index():
	return render_template('ts.html')
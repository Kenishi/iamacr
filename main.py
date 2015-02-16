"""
The MIT License (MIT)

Copyright (c) 2015 Jeremy May

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sys
sys.path.insert(0, 'libs')

import webapp2
import urllib2
import datetime
import json
import re
import cgi
import markdown
from bs4 import BeautifulSoup

"""Your Google Calendar API Key should go here"""
CALENDAR_API_KEY = "YOUR_API_KEY"

"""This is the page shown when you open up an RSS event"""
LINK_URL = "http://iamacrdemo.appspot.com/static/event.html"

"""
The domain the server rests on.

This is needed if you want to restrict the domain your API key
can be used from.

Example: "http://iamarss.appspot.com" 
Then you can set your API key to only allow "iamarss.appspot.com"
"""
REFERER_DOMAIN = "YOUR_PROJECT_DOMAIN"

class Util:

	"""
	Helper method which opens a URL using urllib2 and adds the referer
	domain to the request (Needed if you domain restrict the API key).

	Returns the response without reading it.
	"""
	@staticmethod
	def getURL(url):
		req = urllib2.Request(url)
		req.add_header("Referer", REFERER_DOMAIN)
		resp = urllib2.urlopen(req)
		return resp

	@staticmethod
	def getTextFromMarkdown(text):
		html = markdown.markdown(text)
		text = ''.join(BeautifulSoup(html).find_all(text=True))
		return text

	@staticmethod
	def getHTMLFromMarkdown(summary):
		html = markdown.markdown(summary)
		return html

	@staticmethod
	def getDateFromRFC(timestamp):
		try:
 			dt = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S-05:00")
			time = dt.time().strftime("%H:%M")
			date = dt.date()
 		except ValueError:
 			date, time = timestamp.split('T')

		return (str(date), str(time))		

# This exists because when I tested this using Feedly it cached some old links
# this is a redirect to fix the problem. Eventually it can be removed.
class LinkHandler(webapp2.RequestHandler):
	def get(self):
		id = self.request.get('id', None)
		if id:
			url = "/static/event.html?id=" + id
			self.redirect(url)
		else:
			self.response.set_status(404)

class QueryHandler(webapp2.RequestHandler):
	event_endpoint = "https://www.googleapis.com/calendar/v3/calendars/amaverify%40gmail.com/events/"

	def queryEvent(self, id):
		accessUrl = self.event_endpoint + id + "?key=" + CALENDAR_API_KEY
		url = Util.getURL(accessUrl)

		resData = {}
		if url and url.getcode() == 200:
			event = url.read()
			event = json.loads(event)

			resData['code'] = 200
			resData['summary'] = event['summary']
			resData['desc'] = event['description']
			
			date, time = Util.getDateFromRFC(event['start']['dateTime'])
			resData['start'] = {'dateTime': event['start']['dateTime']}
		else:
			resData = self.error()

		return resData

	"""
	The POST to /query/ is used to parse Markdown and get HTML back.

	POST Request expects 2 paramters:
	action=m  There are no other actions, always supply 'm'
	data=STRING  The string to be marked down

	POST Response:
	JSON Object on success
	{ 
		code: 200,
		data: (string) - The markdown in HTML
	}


	Most Javascript solutions for parsing Markdown required Node.js.
	Parsing this inside Python was the most reasonable compromise.
	"""
	def post(self):
		action = self.request.get('action', None)
		if action:
			if action == "m": #Markdown parse
				data = self.request.get('data', None)
				if data:
					html = Util.getHTMLFromMarkdown(data)
				
					data = {}
					data['code'] = "200"
					data['data'] = html
					j = json.dumps(data)
					self.response.out.write(j)
				else:
					self.response.set_status(400)
			else:
				self.response.set_status(400)
		else:
			self.response.set_status(400)

	"""
	The GET to /query/ is used to retrieve a JSON containing information
	on the event.

	GET Request expects 1 parameter:

	id=STRING  The event id

	GET Success (200) returns:
	{
		code: 200,
		summary: (string) - The summary of the event. This is usually the person's name.
		desc: (string) - The event description. This is usually 2 or 3 words describing the person.
		start: {
			dateTime: (string) - The time when the event starts in RFC 3339 format.
		}

	}

	GET Failure (404) returns:
	{
		code: 404,
		msg: "Event not found."
	}

	"""
	def get(self):
		id = self.request.get('id', None)
		if id:
			resData = self.queryEvent(id)
		else:
			self.response.set_status(404, "Event not found.")
			resData = self.error()

		resData = json.dumps(resData)
		self.response.out.write(resData)

	def error(self):
		error = {}
		error['code'] = 404
		error['msg'] = "Event not found."
		return error

class RSSHandler(webapp2.RequestHandler):
		IAMA_CALENDAR_URL = [
			"https://www.googleapis.com/calendar/v3/calendars/amaverify%40gmail.com/events?timeMin=",
			'',
			"&timeMax=",
			'',
			'&key=', CALENDAR_API_KEY]

		def parseJson(self, data):
			cal = json.loads(data)
			entry = cal["items"]
			
			events = []

			for e in entry:
				event = {}
				event['start'] = e['start']['dateTime']
				event['end'] = e['end']['dateTime']
				event['id'] = e['id']

				event['summary'] = Util.getTextFromMarkdown(e['summary'])
				event['keywords'] = Util.getTextFromMarkdown(e['description'])

				events.append(event)

			# Sort by date
			events = sorted(events, key=lambda e: e['start'])

			return events

		def genEntryXML(self, entry):
			date, time = Util.getDateFromRFC(entry["start"])

			xml = "<item>\n"
			xml += "<title>" + cgi.escape(entry['summary']) + " " + date "</title>\n"
			xml += "<link>" + LINK_URL + "?id=" + entry["id"] + "</link>\n"
			xml += "<description>" + cgi.escape(entry["keywords"]) + "</description>\n"
			xml += "<guid>" + entry["id"] + "</guid>\n"
			xml += "</item>\n"
			return xml

		def genXML(self, data):
			xml = ("<?xml version=\"1.0\"?>\n"
					"<rss version=\"2.0\">\n"
					"<channel>\n"
					"<title>IAmA Schedule</title>\n"
					"<link>https://www.google.com/calendar/embed?src=amaverify%40gmail.com</link>\n"
					"<description>IAmAs to come</description>\n"
					"<language>en-us</language>\n")

			for e in data:
				xml += self.genEntryXML(e)

			xml += "</channel>\n</rss>"
			return xml

			pass

		def getCal(self, days):
			# Determine time range 
			t_start = datetime.date.today()
			t_end = datetime.date.today() + datetime.timedelta(days)

			accessURL = self.IAMA_CALENDAR_URL
			accessURL[1] = str(t_start) + "T00:00:00-0400"
			accessURL[3] = str(t_end) + "T23:59:59-0400"
			accessURL = "".join(accessURL)

			logging.info(accessURL)
			data = Util.getURL(accessURL).read()
			return data

		def get(self):
			# Read in options, default time is next 7 days
			days = int(self.request.get('t','7'))

			# Verify range
			days = 1 if days < 0 else days
			days = 60 if days > 60 else days

			# Pull Calendar
			jsonData = self.getCal(days)
			if jsonData:
				events = self.parseJson(jsonData) # Convert JSON into list of events
				xml = self.genXML(events) # Create the RSS XML from events
				self.response.headers["Content-Type"] = "application/rss+xml"
				self.response.out.write(xml) 

			else: # Parsing failed
				self.response.set_status(500, "Error getting event calendar")
				self.response.out.write("Error getting event calendar")

			pass

app = webapp2.WSGIApplication([('/iamacrss', RSSHandler), (r'/link/.*', LinkHandler), (r'/query/.*', QueryHandler)], debug=True)

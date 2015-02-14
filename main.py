import sys
sys.path.insert(0, 'libs')

import webapp2
import logging
import urllib
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

LINK_PAGE_HTML = "/static/event.html"
ERROR_PAGE = "/static/error.htm"

class Util:
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
		
		"""Add Try-Catch for invalid time formats"""
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
		url = urllib.urlopen(accessUrl)

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

		def genXMLEntry(self, entry):
			date, time = Util.getDateFromRFC(entry["start"])

			xml = "<item>\n"
			xml += "<title>" + cgi.escape(entry['summary']) + "</title>\n"
			xml += "<link>" + LINK_URL + "?id=" + entry["id"] + "</link>\n"
			xml += "<description>" + cgi.escape(entry["keywords"]) + " \n&lt;br/&gt;" +  date + " " + time + "</description>\n"
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
				xml += self.genXMLEntry(e)

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
			data = urllib.urlopen(accessURL).read()
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

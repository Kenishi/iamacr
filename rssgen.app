import webapp2
import urllib
import datetime
import json
import re

LINK_URL = "http://iamacrdemo.appspot.com/link/"
CALENDAR_API_KEY = "YOUR_API_KEY"
LINK_PAGE_HTML = "http://iamacrdemo.appspot.com/static/event.html"

class LinkHandler(webapp2.RequestHandler):
	event_endpoint = "https://www.googleapis.com/calendar/v3/calendars/amaverify%40gmail.com/events/"

	def getNameAndLink(self, summary):
		match = re.search('\[(.*?)\]\((.*?)\)', summary)
		title = ()
		if match:
			title = (match.group(1), match.group(2))
		elif:
			title = (summary,None)
			pass
		return title

	def createPage(self, event):
		name, link = getNameAndLink(event['summary'])
		if event:
			url += "name={0}&desc={1}&start={2}".format(name, event['description'],event['start'])
			if link:
				url += "&link=" + link
			html = urllib.urlopen(url).read()
		else:
			html = ERROR_PAGE
		return html


	def get(self, eventId):
		id = self.request.get(('id', None))
		if id:
			accessUrl = event_endpoint + eventId + "?key=" + CALENDAR_API_KEY
			url = urllib.urlopen(accessUrl)
			if url and url.getcode() == 200:
				data = url.read()
				entry = json.loads(data)
				html = createPage(entry)
				self.response.set_status("200")
			else:
				html = createPage(None)
				self.response.set_status("404", "Event not found.")
		else:
			html = createPage(None)
			self.response.set_status("404", "Event not found.")

		self.response.out.write(html)

class RSSHandler(webapp2.RequestHandler):
		IAMA_CALENDAR_URL = [
			"https://www.google.com/calendar/feeds/amaverify%40gmail.com/public/embed?&singleevents=true&start-min=",
			'', # Start date range ex: 2015-01-25T00%3A00%3A00-05%3A00 OR 2015-01-25
			"&start-max=", 
			'', # End date range ex: 2015-02-01T00%3A00%3A00-05%3A00 OR 2015-02-02
			"&max-results=1056&alt=json"]

		def parseEntry(self, title, keywords, time, id):
			event = {}
			event["keywords"] = keywords
			event["start"] = time[0]
			event["stop"] = time[1]
			event["id"] = id

			# Parse title and link
			match = re.search('\[(.*?)\]\((.*?)\)', title)
			if match:
				event['name'] = match.group(1)
				event['link'] = match.group(2)
			elif:
				event['name'] = title

			return event
			pass

		def parseJson(self, data):
			cal = json.loads(data)
			entry = cal["cids"]["amaverify%40gmail.com/public/embed"]["gdata"]["feed"]["entry"]
			
			events = []

			for e in entry:
				title = e["title"]["$t"]
				keywords = e["content"]["$t"]
				time = (e["gd$when"][0]["startTime"], e["gd$when"][0]["endTime"])
				eventid = e["gCal$eventId"]["value"]

				newEvent = parseEntry(title, keywords, time, eventid)
				events.append(newEvent)


		def genXMLEntry(self, entry):
			xml = "<item>"
			xml += "<title>" + entry["name"] + "</title>"
			xml += "<link>" + LINK_URL + entry["id"] + "</link>"
			xml += "<description>AmA with: " + entry["name"] + " on " +  entry["start"]
			xml += "<guid>" + entry["id"] + "</guid>"
			xml += "</item>"
			return xml

		def genXML(self, data):
			xml = """
			<?xml version="1.0" ?>
			<rss version="2.0">
				<channel>
				<title>IAmA Schedule</title>
				<link></link>
				<description>IAmAs to come</description>
				<language>en-us</language>
			"""

			for e in data:
				xml += genXMLEntry(e)

			xml += "</channel></rss>"
			return xml

			pass

		def getCal(self, days):
			# Determine time range 
			t_start = datetime.date.today()
			t_end = datetime.date.today() + datetime.timedelta(days)

			accessURL = self.IAMA_CALENDAR_URL
			accessURL[1] = str(t_start)
			accessURL[3] = str(t_end)

			data = urllib.urlopen(accessURL).read()
			return data

		def get(self):
			# Read in options, default time is next 7 days
			days = int(self.request.get('t','7'))

			# Verify range
			days = 1 if days < 0 else days
			days = 60 if days > 60 else days

			# Pull Calendar
			jsonData = getCal(days)
			if jsonData:
				events = parseJson(jsonData) # Convert JSON into list of events
				xml = genXML(events) # Create the RSS XML from events
				self.response.out.write(xml) 

			else: # Parsing failed
				self.response.set_status(500, "Error getting event calendar")
				self.response.out.write("Error getting event calendar")

			pass


def main():
	application = webapp2.WSGIApplication([('/iamacrss'), RSSHandler), (r'/<eventId:.+?',LinkHandler)], debug=False)

if __name__ == '__main__':
	main()

ERROR_PAGE = """
<html>
	<head><title>Event not found</title></head>
	<body>
		Event not found!<br/>
	</body>
</html>"""


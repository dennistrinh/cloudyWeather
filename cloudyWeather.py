'''
Author: Dennis Trinh
Cloudy Weather
'''

from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext.webapp import template
import urllib
import webapp2
import json
import string
import random
import os
import logging


client_secret = ''
client_id = 'ihopeitssunny.apps.googleusercontent.com'
OWM_KEY = 'and not raining' # The OpenWeatherMap API Key
DEFAULT_ZIP = '97331'

'''
UserData entity with four properties: 
unique_id (corresponds to email id), first name,
last name, and email address.
'''

class UserData(ndb.Model):
	id = ndb.StringProperty()
	first_name = ndb.StringProperty()
	last_name = ndb.StringProperty()
	email = ndb.StringProperty()
	unique_id = ndb.StringProperty()

'''
WeatherData entity with five properties:
unique_id (links the user), zip code, city name,
weather forecast, and temperature.
'''

class WeatherData(ndb.Model):
	id = ndb.StringProperty()
	unique_id = ndb.StringProperty()
	zip = ndb.StringProperty()
	city = ndb.StringProperty()
	weather = ndb.StringProperty()
	temp = ndb.FloatProperty()
	


# Generates a random state variable depnding on the size the user inputs
def superSecretKey(size):
	return ''.join(random.choice(string.ascii_letters + string.digits) for x in range(size))

# Handles the main page to set up an account for the user
class MainPage(webapp2.RequestHandler):
    def get(self):
		client = "&client_id=" + client_id
		state = "&state=" + superSecretKey(24)
		redirect_uri = "&redirect_uri=https://dennis-cloud-only.appspot.com/oauth"

		url = "https://accounts.google.com/o/oauth2/v2/auth?"
		url = url + "response_type=code"
		url = url + client
		url = url +	"&scope=email" 
		url = url + state
		url = url + redirect_uri
		
		template_values = {'url': url}
		path = os.path.join(os.path.dirname(__file__), 'templates/home.html')
		self.response.write(template.render(path, template_values))

# Handles the authorization for the user as well as creates a default account for them (if they don't have an account)
class OAuthHandler(webapp2.RequestHandler):
	def get(self):
			google_code = self.request.get('code')
			state = self.request.get('state')
			
			# https://cloud.google.com/appengine/docs/standard/python/issue-requests
			# Sets up the request to POST, so we can get an access token.
			headers = {'Content-Type' : 'application/x-www-form-urlencoded'}
			form_data = {
				'code': google_code,
				'client_id': client_id,
				'client_secret': client_secret,
				'redirect_uri': 'https://dennis-cloud-only.appspot.com/oauth',
				'grant_type': 'authorization_code'
			}
			data = urllib.urlencode(form_data)
			
			result = urlfetch.fetch(
				url ="https://www.googleapis.com/oauth2/v4/token",
				payload=data,
				method=urlfetch.POST,
				headers=headers)
		
			post_results = json.loads(result.content)
			
			# Using the access token granted by google, access the user's google plus data.
			headers = {'Authorization': 'Bearer ' + post_results['access_token']}
			response = urlfetch.fetch(
				url = "https://www.googleapis.com/plus/v1/people/me",
				method = urlfetch.GET,
				headers = headers)
			
			google_data = json.loads(response.content)
			#logging.debug('What was sent back: ' + repr(google_data))
			
			# Print out the data by assigning to appropriate column.
			first_name = google_data['name']['givenName']
			last_name = google_data['name']['familyName']
			email = google_data['emails'][0]['value']
			unique_id = google_data['id']
			template_values = {
				'first_name': first_name,
				'last_name': last_name,
				'email': email,
				'unique_id': unique_id
			}
			
			# GET default information from the Openweathermap API to initialize data
			url = "https://api.openweathermap.org/data/2.5/weather?zip=" + DEFAULT_ZIP
			url = url + "&units=Imperial&appid=" + OWM_KEY
			
			result = urlfetch.fetch(url)
			weather_data = json.loads(result.content)
			
			# Set booleans for user and weather to see if data exists
			user_exists = False
			weather_exists = False
			
			# Check if the user exists in the database
			for x in UserData.query():
				if x.unique_id == unique_id:
					user_exists = True
			
			# If they don't add them to the database
			if not user_exists:
				new_user = UserData()
				new_user.first_name = first_name
				new_user.last_name = last_name
				new_user.email = email
				new_user.unique_id = unique_id
				new_user.put()
				new_user.id = new_user.key.urlsafe()
				new_user.put()
			
			# Check if the weather information for the user exists in the database
			for x in WeatherData.query():
				if x.unique_id == unique_id:
					weather_exists = True
					
			# If not, add default data (OSU's weather) to the database under their unique_id
			if not weather_exists:
				new_weath = WeatherData()
				new_weath.unique_id = unique_id
				new_weath.zip = DEFAULT_ZIP
				new_weath.city = weather_data['name']
				new_weath.weather = weather_data['weather'][0]['description']
				new_weath.temp = weather_data['main']['temp']
				new_weath.put()
				new_weath.id = new_weath.key.urlsafe()
				new_weath.put()
		
			path = os.path.join(os.path.dirname(__file__), 'templates/oauth.html')
			self.response.write(template.render(path, template_values))
			
# UserHandler handles all things related to the user and their information
class UserHandler(webapp2.RequestHandler):
	# Handle get requests (View User Data by ID only)
	def get(self, id = None):
		# If an id is provided check if it exists in the database
		if id:
			valid_id = False
			user_id = '0'
			for x in UserData.query():
				if x.unique_id == id:
					valid_id = True
					user_id = x.id
			# If it exists, display the corresponding data
			if valid_id:	
				user_key = ndb.Key(urlsafe=user_id).get()
				user_key_d = user_key.to_dict()
				user_key_d['self'] = "/user/" + id
				self.response.write(json.dumps(user_key_d))
			# If it doesn't exist, alert the user.
			else:
				self.response.status = 400
				self.response.write("This user does not exist.")
		else:
			self.response.status = 400
			self.response.write("Cannot request user data without an ID.")
			
	# Handle patch requests (Modify User Attribute Data by ID)
	def patch(self, id = None):
		if id:
			valid_id = False
			user_id = '0'
			for x in UserData.query():
				if x.unique_id == id:
					valid_id = True
					user_id = x.id
			if valid_id:		
				new_data = json.loads(self.request.body)
				user_key = ndb.Key(urlsafe=user_id).get()
				
				# Check to see if key:value pairs are valid before updating.
				okay_to_update = False
				for key in new_data:
					if key == "first_name" or key == "last_name" or key == "email":
						okay_to_update = True
					else:
						self.response.status = 400;
						self.response.write("One or more of your fields are invalid.")
						break
				if okay_to_update:		
					for key in new_data:
						if key == "first_name":
							user_key.first_name = new_data['first_name']
							user_key.put()
							self.response.write("First name updated. ")
						elif key == "last_name":
							user_key.last_name = new_data['last_name']
							user_key.put()
							self.response.write("Last name updated. ")
						elif key == "email":
							user_key.email = new_data['email']
							user_key.put()
							self.response.write("Email updated.")
							
		# Otherwise, inform the user an ID is necessary.
		else:
			self.response.status = 400
			self.response.write("Cannot modify data without a specific URL id")
	
	# Handle put requests (Modify Entities by ID)
	def put(self, id = None):
		if id:
			assign_data = json.loads(self.request.body)
			valid_id = False
			
			# Check for a valid id
			for x in UserData.query():
				if x.unique_id == id:
					valid_id = True
					user_id = x.id
			if valid_id:
				okay_to_put = 0
				user_key = ndb.Key(urlsafe=user_id).get()
				
				# Check to see if all fields have been entered
				for key in assign_data:
					if key == "first_name":
						okay_to_put += 1
					elif key == "last_name":
						okay_to_put += 1
					elif key == "email":
						okay_to_put += 1
					else:
						self.response.status = 400
						self.response.write("One or more of your field(s) are invalid. ")
						break
						
				# If all three fields are present, update the corresponding data
				if okay_to_put == 3:
					user_key.first_name = assign_data['first_name']
					user_key.last_name = assign_data['last_name']
					user_key.email = assign_data['email']
					user_key.put()
					self.response.write("All three user fields have been updated.")
				
				# Otherwise, alert the user they are missing fields.
				else:
					self.response.status = 400
					self.response.write("You are missing one or more field(s).")
		else:
			self.response.status = 400
			self.response.write("Cannot modify data without an unique id")
	
	# Handles delete (deletes all weather data associated with the unique id)
	def delete(self, id = None):
		if id:
			valid_id = False
			for x in UserData.query():
				if x.unique_id == id:
					valid_id = True
					user_id = x.id
			# If id is valid, continue.
			if valid_id:
				for y in WeatherData.query():
					if y.unique_id == id:
						weath_id = y.id
						ndb.Key(urlsafe=weath_id).delete()
				ndb.Key(urlsafe=user_id).delete()
				self.response.write("The user and associated weather data has been removed.")
			else:
				self.response.status = 400
				self.response.write("This unique id provided is invalid.")
		else:
			self.response.status = 400
			self.response.write("An id must be provided for delete to work.")
			
# Handler for the weather accounts linked to users
class WeatherHandler(webapp2.RequestHandler):
	# Handler for get requests (Viewing user's specific weather information)
	def get(self, id = None):
		if id:
			valid_id = False
			for x in UserData.query():
				if x.unique_id == id:
					valid_id = True
			if valid_id:
				weath_list = []
				valid_weath = 0
				weather_id = '0'
				for y in WeatherData.query():
					if y.unique_id == id:
						valid_weath += 1
						weather_id = y.id
						weath_key = ndb.Key(urlsafe=weather_id).get()
						weath_key_d = weath_key.to_dict()
						weath_key_d['self'] = "/user/" + id + "/weather"
						weath_list.append(weath_key_d)
				if valid_weath > 0:
					self.response.write(json.dumps(weath_list))
				else:
					self.response.status = 400
					self.response.write("Weather data for this id does not exist.")
			else:
				self.response.status = 400
				self.response.write("This user ID does not exist.")
		else:
			self.response.status = 400
			self.response.write("A unique id must be provided.")
	
	# Handler for post requests (Adding other weather locations to a user's account)
	def post(self, id = None):
		if id:
			valid_id = False
			for x in UserData.query():
				if x.unique_id == id:
					valid_id = True
			# If id is valid, continue.
			if valid_id:
				weath_data = json.loads(self.request.body)
				okay_to_post = False
				# Check for zip code field
				for key in weath_data:
					if key == "zip":
						okay_to_post = True
				if okay_to_post:
					# Check if zip code exists already for user
					zip_exists = False
					for y in WeatherData.query():
						if y.unique_id == id:
							if y.zip == weath_data['zip']:
								zip_exists = True
								self.response.status = 403
								self.response.write("This zip code is already in your profile.")
					
					# Make sure the zip code is a valid number
					zip_valid = True
					zip = int(weath_data['zip'])
					if zip - 1 <= 0 or zip + 1 > 99999:
						zip_valid = False
					
					# If the id is valid and zip code does not exist in the user's data, fetch the data.
					if not zip_exists and zip_valid:
						url = "https://api.openweathermap.org/data/2.5/weather?zip=" + weath_data['zip']
						url = url + "&units=Imperial&appid=" + OWM_KEY	
						result = urlfetch.fetch(url)
						weather_data = json.loads(result.content)
					
					# If the zip code is present, create the new weather entity.
						new_weath = WeatherData()
						new_weath.unique_id = id
						new_weath.zip = weath_data['zip']
						new_weath.city = weather_data['name']
						new_weath.weather = weather_data['weather'][0]['description']
						new_weath.temp = weather_data['main']['temp']
						new_weath.put()
						new_weath.id = new_weath.key.urlsafe()
						new_weath.put()
						self.response.write("New weather data added for specified id.")
					# If the zip code is not a valid number, alert the user.
					elif not zip_valid:
						self.response.status = 400
						self.response.write("This zip code is invalid (too small/big).")
				else:
					self.response.status = 400
					self.response.write("The field in your body is not a valid zip code.")
			else:
				self.response.status = 400
				self.response.write("Posting data to a user an account requires a valid unique id.")
		else:
			self.response.status = 400
			self.response.write("No id was given. A unique id is required.")
	
	# Patch handler for updating zip code, which in turn updates the rest of the data.
	def patch(self, id = None):
		if id:
			valid_id = False
			for x in UserData.query():
				if x.unique_id == id:
					valid_id = True
			# If id is valid, continue.
			if valid_id:
				weath_data = json.loads(self.request.body)
				okay_to_patch = 0
				# Check for zip code field
				for key in weath_data:
					if key == "zip":
						okay_to_patch += 1
					elif key == "old_zip":
						okay_to_patch += 1
				if okay_to_patch == 2:
					# Check if zip code exists already for user
					zip_exists = False
					old_zip_exists = False
					for y in WeatherData.query():
						if y.unique_id == id:
							if y.zip == weath_data['zip']:
								zip_exists = True
								self.response.status = 403
								self.response.write("This zip code is already in your profile.")
							elif y.zip == weath_data['old_zip']:
								old_zip_exists = True
								weath_id = y.id

					# Make sure the zip code is a valid number
					zip_valid = True
					zip = int(weath_data['zip'])
					if zip - 1 <= 0 or zip + 1 > 99999:
						zip_valid = False
					
					# Get the key for weath_id
					if old_zip_exists:
						weath_key = ndb.Key(urlsafe=weath_id).get()
					# If the id is valid and zip code does not exist in the user's data, fetch the data.
					if not zip_exists and zip_valid and old_zip_exists:
						url = "https://api.openweathermap.org/data/2.5/weather?zip=" + weath_data['zip']
						url = url + "&units=Imperial&appid=" + OWM_KEY	
						result = urlfetch.fetch(url)
						weather_data = json.loads(result.content)
					
					# If the zip code is present, update the weather entity.
						weath_key.zip = weath_data['zip']
						weath_key.city = weather_data['name']
						weath_key.weather = weather_data['weather'][0]['description']
						weath_key.temp = weather_data['main']['temp']
						weath_key.put()
						self.response.write("Weather data successfully updated.")
					# If the zip code is not a valid number, alert the user.
					elif not zip_valid:
						self.response.status = 400
						self.response.write("This zip code is invalid (too small/big).")
					
					# If the old zip code is non-existant, alert the user.
					elif not old_zip_exists:
						self.response.status = 400
						self.response.write("The old zip code provided does not exist.")
				else:
					self.response.status = 400
					self.response.write("The field in your body is not a valid zip code.")
			else:
				self.response.status = 400
				self.response.write("Updating data for a user requires an account with a valid unique id.")
		else:
			self.response.status = 400
			self.response.write("No id was given. A unique id is required.")
			
	# Handles delete (deletes all weather data associated with the unique id)
	def delete(self, id = None):
		if id:
			valid_id = False
			for x in UserData.query():
				if x.unique_id == id:
					valid_id = True
			# If id is valid, continue.
			if valid_id:
				for y in WeatherData.query():
					if y.unique_id == id:
						weath_id = y.id
						ndb.Key(urlsafe=weath_id).delete()
				self.response.write("All entries have been deleted for the specified id.")
			else:
				self.response.status = 400
				self.response.write("This unique id provided is invalid.")
		else:
			self.response.status = 400
			self.response.write("An id must be provided for delete to work.")
		
						
# Required for patch method to work
allowed_methods = webapp2.WSGIApplication.allowed_methods
new_allowed_methods = allowed_methods.union(('PATCH',))
webapp2.WSGIApplication.allowed_methods = new_allowed_methods
			

app = webapp2.WSGIApplication([
    ('/', MainPage),
	('/oauth', OAuthHandler),
	('/user/(.*)/weather', WeatherHandler),
	#('/weather', WeatherNoUserHandler),
	('/user', UserHandler),
	('/user/(.*)', UserHandler)
], debug=True)

import tweepy
from datetime import datetime
import dateutil.parser
from sodapy import Socrata
from credentials import *

# Access and authorize our Twitter credentials from credentials.py
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

try:
    api.verify_credentials()
    print("Authentication OK")
except:
    print("Error during authentication")

# Unauthenticated client only works with public data sets. Note 'None'
# in place of application token, and no username or password:
client = Socrata("opendata.camden.gov.uk", None)

# Example authenticated client (needed for non-public datasets):
# client = Socrata(opendata.camden.gov.uk,
#                  MyAppToken,
#                  userame="user@example.com",
#                  password="AFakePassword")

# First 2000 results, returned as JSON from API / converted to Python list of
# dictionaries by sodapy.
results = client.get(
    "2eiu-s2cw",
    limit=200,
    order="registered_date DESC"
)

for result in results:
    type = result['application_type']
    if 'applicant_name' in result:
        name = result['applicant_name']
    else:
        name = "Unknown"
    address = result['development_address']
    date = dateutil.parser.parse(result['registered_date'])
    formatted_date = date.strftime("%d %B %Y")
    link = result['full_application']['url']
    if 'location' in result:
        location = result['location']

    tweet_text = f"New {type} planning application from {name} at {address}. "
    tweet_text += f"Registered on {formatted_date}.\n\n{link}"
    print(tweet_text, len(tweet_text), "\n\n")

    tweet_data = {
        'status': tweet_text,
        'lat': location['latitude'],
        'long': location['longitude'],
        'display_coordinates': True
    }

    # api.update_status(tweet_data)

import tweepy
from datetime import datetime
import dateutil.parser
import pickle
from sodapy import Socrata
from credentials import *

PICKLEFILE = "planningapp-bot.dat"

try:
    data = pickle.load(open(PICKLEFILE, "rb"))
except IOError:
    data = {
        "last-modified": ""
    }

if "tweeted" not in data:
    data["tweeted"] = []

# Access and authorize our Twitter credentials from credentials.py
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

try:
    api.verify_credentials()
    print("Authentication OK")
except:
    print("Error during authentication")


def smart_truncate(content, length=100, suffix='…'):
    if len(content) <= length:
        return content
    else:
        return ' '.join(content[:length+1].split(' ')[0:-1]) + suffix

# Unauthenticated client only works with public data sets. Note 'None'
# in place of application token, and no username or password:
client = Socrata("opendata.camden.gov.uk", app_token)

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
    if result['pk'] in data['tweeted']:
        continue

    date = dateutil.parser.parse(result['registered_date'])

    if date < datetime(2020, 12, 24):
        data['tweeted'].append(result['pk'])
        continue

    type = result['application_type']
    if 'applicant_name' in result and result['applicant_name'].strip() != '':
        name = result['applicant_name']
    else:
        name = "Unknown"
    address = smart_truncate(result['development_address'], 36)
    formatted_date = date.strftime("%d %B %Y")
    link = result['full_application']['url']
    if 'location' in result:
        location = result['location']

    tweet_text = f"New {type} planning application from {name} at {address}. "
    tweet_text += f"Registered on {formatted_date}.\n\n{link}"

    tweet_data = {
        'status': tweet_text,
        'lat': location['latitude'],
        'long': location['longitude'],
        'display_coordinates': True
    }

    # send tweet
    api.update_status(tweet_data)
    data['tweeted'].append(result['pk'])
    print(f"That's it, that's the tweet: \"{tweet_text}\"", len(tweet_text), "\n\n")

pickle.dump(data, open(PICKLEFILE, "wb"))

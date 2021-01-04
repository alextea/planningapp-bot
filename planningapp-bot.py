from datetime import date, timedelta
import os
import pickle

import dateutil.parser
from decouple import config
from psycopg2 import connect, sql
from staticmap import StaticMap, IconMarker
from sodapy import Socrata
import tweepy

# connect to database
DATABASE_URL = config('DATABASE_URL')
conn = connect(DATABASE_URL)

# Access and authorize our Twitter credentials from environment variables
auth = tweepy.OAuthHandler(config('CONSUMER_KEY'), config('CONSUMER_SECRET'))
auth.set_access_token(config('ACCESS_TOKEN'), config('ACCESS_TOKEN_SECRET'))
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


def is_application_tweeted(conn, pk):
    cur = conn.cursor()
    cur.execute("SELECT pk FROM tweeted WHERE pk = %s", (pk,))
    return cur.fetchone() is not None


def update_application(conn, pk):
    cur = conn.cursor()
    cur.execute("INSERT INTO tweeted VALUES (%s)", (pk,))


def is_table_empty(conn, table):
    cur = conn.cursor()
    cur.execute(
        sql.SQL("SELECT CASE WHEN EXISTS(SELECT 1 FROM {table}) THEN 0 ELSE 1 END")
        .format(table=sql.Identifier(table))
    )
    return cur.fetchone()


def create_map(coords, filename):
    image_width = 1200
    image_height = 630

    m = StaticMap(
        width=image_width,
        height=image_height,
        url_template="http://tile.stamen.com/toner/{z}/{x}/{y}.png"
    )

    marker = IconMarker(
        coords,
        './location-marker.png',
        18, 30)

    m.add_marker(marker)

    image = m.render()
    image.save(filename+'.png')
    return filename+'.png'


def get_applications():
    # Unauthenticated client only works with public data sets. Note 'None'
    # in place of application token, and no username or password:
    client = Socrata("opendata.camden.gov.uk", config('APP_TOKEN'))

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

    return results


def create_tweets():
    if is_table_empty(conn, "tweeted"):
        # if nothing has been tweeted choose yesterday's date as the start date
        yesterday = date.today() - timedelta(days=1)

    results = get_applications()

    for result in results:
        if is_application_tweeted(conn, result['pk']):
            print(f"Skipping {result['pk']}: Already tweeted")
            continue

        registered_date = dateutil.parser.parse(result['registered_date']).date()
        if (registered_date < yesterday and yesterday is not None):
            # if application is older than yesterday, mark as tweeted and skip
            update_application(conn, result['pk'])
            print(f"Skipping {result['pk']}: Too old")
            continue

        type = result['application_type']
        if 'applicant_name' in result and result['applicant_name'].strip() != '':
            name = result['applicant_name']
        else:
            name = "Unknown"

        address = smart_truncate(result['development_address'], 36)
        formatted_date = registered_date.strftime("%d %B %Y")
        link = result['full_application']['url']
        media_ids = []

        if 'location' in result:
            location = result['location']
            coords = (float(location['longitude']), float(location['latitude']))
            media_filename = create_map(coords, result['pk'])
            # upload image
            media = api.media_upload(filename=f"./{media_filename}")
            media_ids.append(media.media_id_string)

        tweet_text = f"New {type} planning application from {name} at {address}. "
        tweet_text += f"Registered on {formatted_date}.\n\n{link}"

        # send tweet
        api.update_status(
            status=tweet_text,
            lat=location['latitude'],
            long=location['longitude'],
            display_coordinates="true",
            media_ids=media_ids
        )

        update_application(conn, result['pk'])
        print(f"Tweeted: \"{tweet_text}\"", len(tweet_text), "\n\n")

        if media_filename:
            os.remove(f"./{media_filename}")

    conn.commit()
    conn.close()


create_tweets()

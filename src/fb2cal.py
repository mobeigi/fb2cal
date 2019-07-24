#!/usr/bin/env python

""" 
    fb2cal
    Created by: mobeigi (mobeigi.com)
"""

import os
import sys
import re
import mechanicalsoup
import urllib.parse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import json
import ics
from ics import Calendar, Event
import configparser

from oauth2client import file, client, tools
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
from httplib2 import Http
from io import BytesIO

# Classes
class Birthday:
    def __init__(self, uid, name, day, month):
        self.uid = uid # Unique identififer for person (required for ics events)
        self.name = name
        self.day = day
        self.month = month

    def __str__(self):
        return f'{self.name} ({self.day}/{self.month})'
    
    def __unicode__(self):
        return u'{self.name} ({self.day}/{self.month})'

# Entry point
def main():

    # Set CWD to script directory
    os.chdir(sys.path[0])

    # Read config
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Authenticate with Google API early
    service = google_api_authenticate()

    # Init browser
    browser = mechanicalsoup.StatefulBrowser()
    init_browser(browser)

    # Attempt login
    response = login(browser, config['AUTH']['FB_EMAIL'], config['AUTH']['FB_PASS'])

    if response.status_code != 200:
        sys.exit(f'Failed to authenticate with Facebook. Status code: {response.status_code}.')

    # Check to see if login failed
    if '<link rel="canonical" href="https://www.facebook.com/login/"' in response.text:
        sys.exit('Failed to authenticate with Facebook. Please check provided email/password.')

    # Check to see if we hit Facebook security checkpoint
    if 'action="/checkpoint/?next"' in response.text:
        sys.exit('Hit Facebook security checkpoint. Please login to Facebook manually and follow prompts to authorize this device.')

    # Get birthday objects for all friends via async endpoint
    birthdays = get_async_birthdays(browser)

    if len(birthdays) == 0:
        sys.exit('Birthday list is empty. Failed to fetch any birthdays. Aborting.')

    # Create birthdays ICS file
    c = populate_birthdays_calendar(birthdays)

    # Remove blank lines
    ics_str = ''.join([line.rstrip('\n') for line in c])

    # Upload to drive
    metadata = {'name': config['DRIVE']['ICS_FILE_NAME']}
    UPLOAD_RETRY_ATTEMPTS = 3

    for attempt in range(UPLOAD_RETRY_ATTEMPTS):
        try:
            updated_file = upload_and_replace_file(service, config['DRIVE']['DRIVE_FILE_ID'], metadata, bytearray(ics_str, 'utf-8')) # Pass payload as bytes
            config.set('DRIVE', 'DRIVE_FILE_ID', updated_file['id'])
        except HttpError as err:
            if err.resp.status == 404: # file not found
                if config['DRIVE']['DRIVE_FILE_ID']:
                    config.set('DRIVE', 'DRIVE_FILE_ID', '') # reset stored file_id
                    print(f"HttpError 404 error. File not found: {config['DRIVE']['DRIVE_FILE_ID']}. Resetting stored file_id in config and trying again. Attempt: {attempt+1}", file=sys.stderr)
                    continue
                else:
                    print(f'HttpError 404 error. Unexpected error.', file=sys.stderr)
    
    # Update config file with updated file id for subsequent runs
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def init_browser(browser):
    """ Initialize browser as needed """
    browser.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36')

def login(browser, email, password):
    """ Authenticate with Facebook """
    
    FACEBOOK_LOGIN_URL = 'http://www.facebook.com/login.php'
    login_page = browser.get(FACEBOOK_LOGIN_URL)
    login_form = login_page.soup.find('form', {'id': 'login_form'})
    login_form.find('input', {'id': 'email'})['value'] = email
    login_form.find('input', {'id': 'pass'})['value'] = password
    return browser.submit(login_form, login_page.url)

def google_api_authenticate():
    """ Authenticate with google apis """
    SCOPES = 'https://www.googleapis.com/auth/drive'
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('drive', 'v3', http=creds.authorize(Http()))
    return service

def upload_and_replace_file(service, file_id, metadata, payload):
    mine_type = 'text/calendar'
    text_stream = BytesIO(payload) 
    media_body = MediaIoBaseUpload(text_stream, mimetype=mine_type, chunksize=1024*1024, resumable=True)

    # If file id is provided, update the file, otherwise we'll create a new file
    if file_id:
        updated_file = service.files().update(fileId=file_id, body=metadata, media_body=media_body).execute()
    else:
        updated_file = service.files().create(body=metadata, media_body=media_body).execute()

        # Need publically accessible ics file so Google calendar can read it
        permission = { "role": 'reader', 
                        "type": 'anyone'}
        service.permissions().create(fileId=updated_file['id'], body=permission).execute()

    return updated_file

__cached_async_token = None
def get_async_token(browser):
    """ Get async authorization token (CSRF protection token) that must be included in all async requests """
    
    global __cached_async_token

    if __cached_async_token:
        return __cached_async_token

    FACEBOOK_BIRTHDAY_EVENT_PAGE_URL = 'https://www.facebook.com/events/birthdays/' # async token is present on this page
    FACEBOOK_ASYNC_TOKEN_REGEXP_STRING = r'{\"token\":\".*?\",\"async_get_token\":\"(.*?)\"}'
    regexp = re.compile(FACEBOOK_ASYNC_TOKEN_REGEXP_STRING, re.MULTILINE)

    birthday_event_page = browser.get(FACEBOOK_BIRTHDAY_EVENT_PAGE_URL)
    
    if birthday_event_page.status_code != 200:
        sys.exit(f'Failed to retreive birthday event page. Status code: {response.status_code}.')

    matches = regexp.search(birthday_event_page.text)

    if not matches or len(matches.groups()) != 1:
        sys.exit('Unexpected number of regexp matches when trying to get async token')
    
    __cached_async_token = matches[1]
    
    return matches[1]

def get_async_birthdays(browser):
    """ Returns list of birthday objects by querying the Facebook birthday async page """
    
    FACEBOOK_BIRTHDAY_ASYNC_ENDPOINT = 'https://www.facebook.com/async/birthdays/?'

    birthdays = []

    next_12_months_epoch_timestamps = get_next_12_month_epoch_timestamps()

    for epoch_timestamp in next_12_months_epoch_timestamps:
        # Not all fields are required for response to be given, required fields are date, fb_dtsg_ag and __a
        query_params = {'date': epoch_timestamp,
                        'fb_dtsg_ag': get_async_token(browser),
                        '__a': '1'}
        
        response = browser.get(FACEBOOK_BIRTHDAY_ASYNC_ENDPOINT + urllib.parse.urlencode(query_params))
        
        if response.status_code != 200:
            sys.exit(f'Failed to get async birthday response. Params: {query_params}. Status code: {response.status_code}.')
        
        birthdays.extend(parse_birthday_async_output(browser, response.text))

    return birthdays

def get_next_12_month_epoch_timestamps():
    """ Returns array of epoch timestamps corresponding to the 1st day of the next 12 months starting from the current month.
        For example, if the current date is 2000-05-20, will return epoch for 2000-05-01, 2000-06-01, 2000-07-01 etc for 12 months """
    
    epoch_timestamps = []

    # Facebook timezone seems to use Pacific Standard Time locally for these epochs
    # So we have to convert our 00:00:01 datetime on 1st of month from Pacific to UTC before getting our epoch timestamps
    pdt = pytz.timezone('America/Los_Angeles')
    cur_date = datetime.now()

    # Loop for next 12 months
    for _ in range(12):
        # Reset day to 1 and time to 00:00:01
        cur_date = cur_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Convert from Pacific to UTC and store timestamp
        utc_date = pdt.localize(cur_date).astimezone(pytz.utc)
        epoch_timestamps.append(int(utc_date.timestamp()))
        
        # Move cur_date to 1st of next month
        cur_date = cur_date + relativedelta(months=1)
    
    return epoch_timestamps

def parse_birthday_async_output(browser, text):
    """ Parsed Birthday Async output text and returns list of Birthday objects """
    BIRTHDAY_STRING_REGEXP_STRING = r'class=\\\"_43q7\\\".*?href=\\\"https:\\/\\/www\.facebook\.com\\/(.*?)\\\".*?.*?data-tooltip-content=\\\".*? \((.*?)\)\\\">.*?alt=\\\"(.*?)\\\".*?/>'
    regexp = re.compile(BIRTHDAY_STRING_REGEXP_STRING, re.MULTILINE)
    
    birthdays = []
    
    for vanity_name, birthday_date_str, name in regexp.findall(text):
        # Check to see if user has no custom vanity name in which case we'll just take the id directly
        if vanity_name.startswith('profile.php?id='):
            uid = vanity_name[15:]
        else:
            uid = get_entity_id_from_vanity_name(browser, vanity_name)
        
        # Parse birthday date string into Day / Month
        day, month = parse_birthday_day_month(birthday_date_str)

        birthdays.append(Birthday(uid, name, day, month))

    return birthdays

def parse_birthday_day_month(birthday_date_str):
    """ Convert birthday date string to a day and month number. Facebook will use MM/DD format for all birthdays expect those in the following week compared to current date.
        Those will instead show day names such as 'Monday', 'Tuesday' etc for the next 7 days. """
    
    # Attempt regexp match
    BIRTHDAY_STRING_REGEXP_STRING = r'(\d+)\\/(\d+)'
    regexp = re.compile(BIRTHDAY_STRING_REGEXP_STRING)

    matches = regexp.search(birthday_date_str)

    if matches and len(matches.groups()) == 2:
        return (int(matches[2]), int(matches[1])) # day, month

    # Otherwise, have to convert day names to a day and month
    offset_dict = get_days_offset_dict()
    cur_date = datetime.now()

    if birthday_date_str in offset_dict:
        cur_date = cur_date + relativedelta(days=offset_dict[birthday_date_str])
        return (cur_date.day, cur_date.month)

    sys.exit(f'Failed to parse birthday day/month. Regexp match failed and {birthday_date_str} is not in the offset dict {offset_dict}')

__offset_dict = None
def get_days_offset_dict():
    """ The day name to offset dict maps a day to a numerical offset which can be used to add days to the current date. """

    global __offset_dict

    if __offset_dict:
        return __offset_dict

    __offset_dict = {}
    
    # todays birthdays will be shown normally (as date) so we can skip today
    cur_date = datetime.now() + relativedelta(days=1)
    
    # Iterate through the following 7 days
    for i in range(1, 8):
        __offset_dict[cur_date.strftime("%A")] = i
        cur_date = cur_date + relativedelta(days=1)

    return __offset_dict

def get_entity_id_from_vanity_name(browser, vanity_name):
    """ Given a vanity name (user/page custom name), get the unique identifier entity_id """

    COMPOSER_QUERY_ASYNC_ENDPOINT = "https://www.facebook.com/ajax/mercury/composer_query.php?"

    # Not all fields are required for response to be given, required fields are value, fb_dtsg_ag and __a
    query_params = {'value': vanity_name,
                    'fb_dtsg_ag': get_async_token(browser),
                    '__a': '1'}

    response = browser.get(COMPOSER_QUERY_ASYNC_ENDPOINT + urllib.parse.urlencode(query_params))
    
    if response.status_code != 200:
        sys.exit(f'Failed to get async composer query response. Params: {query_params}. Status code: {response.status_code}.')

    response = strip_ajax_response_prefix(response.text)
    json_response = json.loads(response)

    # Loop through entries to see if a valid match is found where alias matches provided vanity name
    for entry in json_response['payload']['entries']:
        # Skip other render types like commerce pages etc
        if entry['vertical_type'] != 'USER' and entry['render_type'] not in ['friend', 'non_friend']:
            continue

        if 'alias' in entry and entry['alias'] == vanity_name:
            # Match found!
            return entry['uid']

    sys.exit(f'Failed to get entity id for vanity_name. Params: {query_params}')
    return None

def strip_ajax_response_prefix(input):
    """ Strip the prefix that Facebook puts in front of AJAX responses """

    if input.startswith('for (;;);'):
        return input[9:]
    return input

def populate_birthdays_calendar(birthdays):
    """ Populate a birthdays calendar using birthday objects """

    c = Calendar()
    c.scale = 'GREGORIAN'
    c.method = 'PUBLISH'
    c.creator = 'fb2cal - https://git.io/fjMwr'
    c._unused.append(ics.parse.ContentLine(name='X-WR-CALNAME', params={}, value='Facebook Birthdays (fb2cal)'))
    c._unused.append(ics.parse.ContentLine(name='X-PUBLISHED-TTL', params={}, value='PT12H'))
    c._unused.append(ics.parse.ContentLine(name='X-ORIGINAL-URL', params={}, value='/events/birthdays/'))

    cur_date = datetime.now()

    for birthday in birthdays:
        e = Event()
        e.uid = birthday.uid
        e.name = f"{birthday.name}'s Birthday"

        # Calculate the year as this year or next year based on if its past current month or not
        # Also pad day, month with leading zeros to 2dp
        year = cur_date.year if birthday.month >= cur_date.month else (cur_date + relativedelta(years=1)).year
        month = '{:02d}'.format(birthday.month)
        day = '{:02d}'.format(birthday.day)
        e.begin = f'{year}{month}{day} 00:00:00'
        e.make_all_day()
        e.duration = timedelta(days=1)
        e._unused.append(ics.parse.ContentLine(name='RRULE', params={}, value='FREQ=YEARLY'))

        c.events.add(e)
    
    return c

if __name__ == "__main__":
    main()

__version__ = '1.0.0'
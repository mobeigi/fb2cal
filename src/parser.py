############### #!/usr/bin/env python # TODO

""" Facebook Birthdays to Calendar Parser """

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
    EMAIL = 'REDACTED'
    PASSWORD = 'REDACTED'

    # Init browser
    browser = mechanicalsoup.Browser()
    init_browser(browser)

    # Attempt login
    response = login(browser, EMAIL, PASSWORD)
    
    if response.status_code != 200:
        sys.exit('Failed to login.')

    # Get birthday objects for all friends via async endpoint
    birthdays = get_async_birthdays(browser)

    # Create birthdays ICS file
    c = populate_birthdays_calendar(birthdays)

    # Write to file stripping extra new lines away
    with open('birthday.ics', 'w') as f:
        f.writelines([line.rstrip('\n') for line in c])

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
        sys.exit('Failed to retreive birthday event page.')

    matches = regexp.search(birthday_event_page.text)

    if not matches or len(matches.groups()) != 1:
        sys.exit('Unexpected number of regexp matches when trying to get async token')
    
    __cached_async_token = matches[1]
    
    return matches[1]

def get_async_birthdays(browser):
    """ Returns list of birthday objects by querying the Facebook birthday async page """
    
    FACEBOOK_BIRTHDAY_ASYNC_ENDPOINT = 'https://www.facebook.com/async/birthdays/?'

    birthdays = []

    url = urllib.parse.urlparse(FACEBOOK_BIRTHDAY_ASYNC_ENDPOINT)

    next_12_months_epoch_timestamps = get_next_12_month_epoch_timestamps()

    for epoch_timestamp in next_12_months_epoch_timestamps:
        # Not all fields are required for response to be given, required fields are date, fb_dtsg_ag and __a
        query_params = {'date': epoch_timestamp,
                        'fb_dtsg_ag': get_async_token(browser),
                        '__a': '1'}
        
        response = browser.get(FACEBOOK_BIRTHDAY_ASYNC_ENDPOINT + urllib.parse.urlencode(query_params))
        
        if response.status_code != 200:
            sys.exit(f'Failed to get async birthday response. Params: {query_params}')
        
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
    for _ in range(0, 12):
        # Reset day to 1 and time to 00:00:01
        cur_date = cur_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Convert from Pacific to UTC and store timestamp
        utc_date = pdt.localize(cur_date).astimezone(pytz.utc)
        epoch_timestamps.append(int(utc_date.timestamp()))
        
        # Move cur_date to 1st of next month
        cur_date = cur_date + relativedelta(months=1)
    
    return epoch_timestamps[0:1] # TODO

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
    cur_date = datetime.now()
    
    # TODO: Check what this shows for today, check when last day cutoff is
    for i in range(0, 8):
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
        sys.exit(f'Failed to get async composer query response. Params: {query_params}')

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

    # TODO: Fallback to scraping users profile page directly here

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
    c.creator = '-//Facebook//NONSGML Facebook Events V1.0//EN' # TODO: Give myself some credit? 
    c._unused.append(ics.parse.ContentLine(name='X-WR-CALNAME', params={}, value='Friends\' Birthdays'))
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
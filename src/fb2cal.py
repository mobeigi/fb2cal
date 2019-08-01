#!/usr/bin/env python3

""" 
    fb2cal - Facebook Birthday Events to ICS file converter
    Created by: mobeigi

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
"""

from __init__ import *

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
    
    try:
        dataset = config.read('config.ini')
        if not dataset:
            print('config.ini does not exist. Please rename config-template.ini if you have not done so already.')
    except configparser.Error as e:
        print(f'ConfigParser error: {e}')

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
    if response.soup.find('link', {'rel': 'canonical', 'href': 'https://www.facebook.com/login/'}):
        sys.exit('Failed to authenticate with Facebook. Please check provided email/password.')

    # Check to see if we hit Facebook security checkpoint
    if response.soup.find('button', {'id': 'checkpointSubmitButton'}):
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

    # Confirm credentials.json exists
    if not os.path.isfile('credentials.json'):
        sys.exit(f'credentials.json file does not exist')

    SCOPES = 'https://www.googleapis.com/auth/drive.file'
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
        sys.exit(f'Failed to retreive birthday event page. Status code: {birthday_event_page.status_code}.')

    matches = regexp.search(birthday_event_page.text)

    if not matches or len(matches.groups()) != 1:
        sys.exit('Unexpected number of regexp matches when trying to get async token')
    
    __cached_async_token = matches[1]
    
    return matches[1]

__locale = None
def get_facebook_locale(browser):
    """ Returns users Facebook locale """

    global __locale
    
    if __locale:
        return __locale

    FACEBOOK_LOCALE_ENDPOINT = 'https://www.facebook.com/ajax/settings/language/account.php?'
    FACEBOOK_LOCALE_REGEXP_STRING = r'[a-z]{2}_[A-Z]{2}'
    regexp = re.compile(FACEBOOK_LOCALE_REGEXP_STRING, re.MULTILINE)

    # Not all fields are required for response to be given, required fields are fb_dtsg_ag and __a
    query_params = {'fb_dtsg_ag': get_async_token(browser),
                    '__a': '1'}

    response = browser.get(FACEBOOK_LOCALE_ENDPOINT + urllib.parse.urlencode(query_params))
    
    if response.status_code != 200:
        sys.exit(f'Failed to get Facebook locale. Params: {query_params}. Status code: {response.status_code}.')

    response = strip_ajax_response_prefix(response.text)
    json_response = json.loads(response)
    
    current_locale = json_response['jsmods']['require'][0][3][1]['currentLocale']

    # Validate locale
    if not regexp.match(current_locale):
        sys.exit(f'Invalid Facebook locale fetched: {current_locale}.')

    __locale = current_locale

    return __locale


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
    BIRTHDAY_STRING_REGEXP_STRING = r'class=\"_43q7\".*?href=\"https://www\.facebook\.com/(.*?)\".*?data-tooltip-content=\"(.*?)\">.*?alt=\"(.*?)\".*?/>'
    regexp = re.compile(BIRTHDAY_STRING_REGEXP_STRING, re.MULTILINE)
    
    birthdays = []

    # Fetch birthday card html payload
    response = strip_ajax_response_prefix(text)
    json_response = json.loads(response)
    birthday_card_html = json_response['domops'][0][3]['__html']
    locale = get_facebook_locale(browser)

    for vanity_name, tooltip_content, name in regexp.findall(birthday_card_html):
        # Check to see if user has no custom vanity name in which case we'll just take the id directly
        if vanity_name.startswith('profile.php?id='):
            uid = vanity_name[15:]
        else:
            uid = get_entity_id_from_vanity_name(browser, vanity_name)
        
        # Parse tooltip content into day/month
        day, month = parse_birthday_day_month(tooltip_content, name, locale)

        birthdays.append(Birthday(uid, name, day, month))

    return birthdays

def parse_birthday_day_month(tooltip_content, name, locale):
    """ Convert the Facebook birthday tooltip content to a day and month number. Facebook will use a tooltip format based on the users Facebook language (locale).
        The date will be in some date format which reveals the birthday day and birthday month.
        This is done for all birthdays expect those in the following week relative to the current date.
        Those will instead show day names such as 'Monday', 'Tuesday' etc for the next 7 days. """

    birthday_date_str = tooltip_content

    # List of strings that will be stripped away from tooltip_content
    # The goal here is to remove all other characters except the birthday day, birthday month and day/month seperator symbol
    strip_list = [
        name, # Full name of user which will appear somewhere in the string
        '(', # Regular left bracket
        ')', # Regular right bracket 
        '&#x200f;', # Remove right-to-left mark (RLM)
        '&#x200e;', # Remove left-to-right mark (LRM)
        '&#x55d;' # Backtick character name postfix in Armenian
    ]
    
    for string in strip_list:
        birthday_date_str = birthday_date_str.replace(string, '')

    birthday_date_str = birthday_date_str.strip()

    # Dict with mapping of locale identifier to month/day datetime format 
    locale_date_format_mapping = {
        'af_ZA': '%d-%m',
        'am_ET': '%m/%d',
        # 'ar_AR': '', # TODO: parse Arabic numeric characters
        # 'as_IN': '', # TODO: parse Assamese numeric characters
        'az_AZ': '%d.%m',
        'be_BY': '%d.%m',
        'bg_BG': '%d.%m',
        'bn_IN': '%d/%m',
        'br_FR': '%d/%m',
        'bs_BA': '%d.%m.',
        'ca_ES': '%d/%m',
        # 'cb_IQ': '', # TODO: parse Arabic numeric characters
        'co_FR': '%m-%d',
        'cs_CZ': '%d. %m.',
        'cx_PH': '%m-%d',
        'cy_GB': '%d/%m',
        'da_DK': '%d.%m',
        'de_DE': '%d.%m.',
        'el_GR': '%d/%m',
        'en_GB': '%d/%m',
        'en_UD': '%m/%d',
        'en_US': '%m/%d',
        'eo_EO': '%m-%d',
        'es_ES': '%d/%m',
        'es_LA': '%d/%m',
        'et_EE': '%d.%m',
        'eu_ES': '%m/%d',
        # 'fa_IR': '', # TODO: parse Persian numeric characters
        'ff_NG': '%d/%m',
        'fi_FI': '%d.%m.',
        'fo_FO': '%d.%m',
        'fr_CA': '%m-%d',
        'fr_FR': '%d/%m',
        'fy_NL': '%d-%m',
        'ga_IE': '%d/%m',
        'gl_ES': '%d/%m',
        'gn_PY': '%m-%d',
        'gu_IN': '%d/%m',
        'ha_NG': '%m/%d',
        'he_IL': '%d.%m',
        'hi_IN': '%d/%m',
        'hr_HR': '%d. %m.',
        'ht_HT': '%m-%d',
        'hu_HU': '%m. %d.',
        'hy_AM': '%d.%m',
        'id_ID': '%d/%m',
        'is_IS': '%d.%m.',
        'it_IT': '%d/%m',
        'ja_JP': '%m/%d',
        'ja_KS': '%m/%d',
        'jv_ID': '%d/%m',
        'ka_GE': '%d.%m',
        'kk_KZ': '%d.%m',
        'km_KH': '%d/%m',
        'kn_IN': '%d/%m',
        'ko_KR': '%m. %d.',
        'ku_TR': '%m-%d',
        'ky_KG': '%d-%m',
        'lo_LA': '%d/%m',
        'lt_LT': '%m-%d',
        'lv_LV': '%d.%m.',
        'mg_MG': '%d/%m',
        'mk_MK': '%d.%m',
        'ml_IN': '%d/%m',
        'mn_MN': '%m-&#x440; &#x441;&#x430;&#x440;/%d',
        # 'mr_IN': '', # TODO: parse Marathi numeric characters
        'ms_MY': '%d-%m',
        'mt_MT': '%m-%d',
        # 'my_MM': '', # TODO: parse Myanmar numeric characters
        'nb_NO': '%d.%m.',
        # 'ne_NP': '', # TODO: parse Nepali numeric characters
        'nl_BE': '%d/%m',
        'nl_NL': '%d-%m',
        'nn_NO': '%d.%m.',
        'or_IN': '%m/%d',
        'pa_IN': '%d/%m',
        'pl_PL': '%d.%m',
        # 'ps_AF': '', # TODO: parse Afghani numeric characters
        'pt_BR': '%d/%m',
        'pt_PT': '%d/%m',
        'ro_RO': '%d.%m',
        'ru_RU': '%d.%m',
        'rw_RW': '%m-%d',
        'sc_IT': '%m-%d',
        'si_LK': '%m-%d',
        'sk_SK': '%d. %m.',
        'sl_SI': '%d. %m.',
        'sn_ZW': '%m-%d',
        'so_SO': '%m/%d',
        'sq_AL': '%d.%m',
        'sr_RS': '%d.%m.',
        'sv_SE': '%d/%m',
        'sw_KE': '%d/%m',
        'sy_SY': '%m-%d',
        'sz_PL': '%m-%d',
        'ta_IN': '%d/%m',
        'te_IN': '%d/%m',
        'tg_TJ': '%m-%d',
        'th_TH': '%d/%m',
        'tl_PH': '%m/%d',
        'tr_TR': '%d/%m',
        'tt_RU': '%d.%m',
        'tz_MA': '%m/%d',
        'uk_UA': '%d.%m',
        'ur_PK': '%d/%m',
        'uz_UZ': '%d/%m',
        'vi_VN': '%d/%m',
        'zh_CN': '%m/%d',
        'zh_HK': '%d/%m',
        'zh_TW': '%m/%d',
        'zz_TR': '%m-%d'
    }

    # Ensure a supported locale is being used
    if locale not in locale_date_format_mapping:
        sys.exit(f"The locale {locale} is not supported.")
    
    try:
        # Try to parse the date using appropriate format based on locale
        parsed_date = datetime.strptime(birthday_date_str, locale_date_format_mapping[locale])
        return (parsed_date.day, parsed_date.month)
    except ValueError:
        # Otherwise, have to convert day names to a day and month
        offset_dict = get_days_offset_dict()
        cur_date = datetime.now()

        if birthday_date_str in offset_dict:
            cur_date = cur_date + relativedelta(days=offset_dict[birthday_date_str])
            return (cur_date.day, cur_date.month)

    sys.exit(f'Failed to parse birthday day/month. Parse failed with tooltip_content: "{tooltip_content}", locale: "{locale}". Day name "{birthday_date_str}" is not in the offset dict {offset_dict}')

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

def strip_ajax_response_prefix(payload):
    """ Strip the prefix that Facebook puts in front of AJAX responses """

    if payload.startswith('for (;;);'):
        return payload[9:]
    return payload

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
        e.begin = f'{year}-{month}-{day} 00:00:00'
        e.make_all_day()
        e.duration = timedelta(days=1)
        e._unused.append(ics.parse.ContentLine(name='RRULE', params={}, value='FREQ=YEARLY'))

        c.events.add(e)
    
    return c

if __name__ == "__main__":
    main()
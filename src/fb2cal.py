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
import platform
import re
import mechanicalsoup
import requests
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from babel import Locale
from babel.core import UnknownLocaleError
from babel.dates import format_date
import html
import locale
import pytz
import json
import ics
from ics import Calendar, Event
from ics.grammar.parse import ContentLine
import configparser
import logging
from distutils import util
import calendar

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
    CONFIG_FILE_NAME = 'config.ini'
    CONFIG_FILE_PATH = f'../config/{CONFIG_FILE_NAME}'
    CONFIG_FILE_TEMPLATE_NAME = 'config-template.ini'
    logger.info(f'Attemping to parse config file {CONFIG_FILE_NAME}...')
    config = configparser.RawConfigParser()
    
    try:
        dataset = config.read(CONFIG_FILE_PATH, encoding='UTF-8')
        if not dataset:
            logger.error(f'{CONFIG_FILE_PATH} does not exist. Please rename {CONFIG_FILE_TEMPLATE_NAME} if you have not done so already.')
            raise SystemExit
    except configparser.Error as e:
        logger.error(f'ConfigParser error: {e}')
        raise SystemExit

    logger.info('Config successfully loaded.')

    # Set logging level based on config
    try:
        logger.setLevel(getattr(logging, config['LOGGING']['level']))
        logging.getLogger().setLevel(logger.level) # Also set root logger level
    except AttributeError:
        logger.error(f'Invalid logging level specified. Level: {config["LOGGING"]["level"]}')
        raise SystemError
    
    logger.info(f'Logging level set to: {logging.getLevelName(logger.level)}')

    # Init browser
    browser = mechanicalsoup.StatefulBrowser()
    init_browser(browser)

    # Attempt login
    logger.info('Attemping to authenticate with Facebook...')
    facebook_authenticate(browser, config['AUTH']['FB_EMAIL'], config['AUTH']['FB_PASS'])
    logger.info('Successfully authenticated with Facebook.')

    # Get birthday objects for all friends via async endpoint
    logger.info('Fetching all Birthdays via async endpoint...')
    birthdays = get_async_birthdays(browser)

    if len(birthdays) == 0:
        logger.warning(f'Birthday list is empty. Failed to fetch any birthdays.')
        raise SystemError

    logger.info(f'A total of {len(birthdays)} birthdays were found.')

    # Create birthdays ICS file
    logger.info('Creating birthday ICS file...')
    c = populate_birthdays_calendar(birthdays)
    logger.info('ICS file created successfully.')
    
    # Remove blank lines
    ics_str = ''.join([line.rstrip('\n') for line in c])
    logger.debug(f'ics_str: {ics_str}')

    # Save to file system
    if util.strtobool(config['FILESYSTEM']['SAVE_TO_FILE']):
        logger.info(f'Saving ICS file to local file system...')

        if not os.path.exists(os.path.dirname(config['FILESYSTEM']['ICS_FILE_PATH'])):
            os.makedirs(os.path.dirname(config['FILESYSTEM']['ICS_FILE_PATH']), exist_ok=True)

        with open(config['FILESYSTEM']['ICS_FILE_PATH'], mode='w', encoding="UTF-8") as ics_file:
            ics_file.write(ics_str)
        logger.info(f'Successfully saved ICS file to {os.path.abspath(config["FILESYSTEM"]["ICS_FILE_PATH"])}')

    # Update config file with updated file id for subsequent runs
    logger.info('Saving changes to config file...')
    with open(CONFIG_FILE_PATH, 'w') as configfile:
        config.write(configfile)
    logger.info('Successfully saved changes to config file.')

    logger.info('Done! Terminating gracefully.')

def setup_custom_logger(name):
    """ Setup logger """
    LOGGING_FILE_PATH = './logs/fb2cal.log'

    if not os.path.exists(os.path.dirname(LOGGING_FILE_PATH)):
        os.makedirs(os.path.dirname(LOGGING_FILE_PATH), exist_ok=True)

    logging.basicConfig(
        format='[%(asctime)s] %(name)s %(levelname)s (%(funcName)s) %(message)s',
        level=logging.DEBUG,
        handlers=[logging.StreamHandler(),
                  logging.FileHandler(LOGGING_FILE_PATH, encoding='UTF-8')]
    )
    
    return logging.getLogger(name)


def init_browser(browser):
    """ Initialize browser as needed """
    browser.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36')

def facebook_authenticate(browser, email, password):
    """ Authenticate with Facebook setting up session for further requests """
    
    FACEBOOK_LOGIN_URL = 'http://www.facebook.com/login.php'
    FACEBOOK_DATR_TOKEN_REGEXP = r'\"_js_datr\",\"(.*?)\"'
    regexp = re.compile(FACEBOOK_DATR_TOKEN_REGEXP, re.MULTILINE)

    # Add 'datr' cookie to session for countries adhering to GDPR compliance
    login_page = browser.get(FACEBOOK_LOGIN_URL)
    
    if login_page.status_code != 200:
        logger.debug(login_page.text)
        logger.error(f'Failed to authenticate with Facebook with email {email}. Stage: Initial Request for datr Token, Status code: {login_page.status_code}.')
        raise SystemError

    matches = regexp.search(login_page.text)

    if not matches or len(matches.groups()) != 1:
        logger.debug(login_page.text)
        logger.error(f'Match failed or unexpected number of regexp matches when trying to get datr token.')
        raise SystemError
    
    _js_datr = matches[1]
    
    datr_cookie = requests.cookies.create_cookie(domain='.facebook.com', name='datr', value=_js_datr)
    _js_datr_cookie = requests.cookies.create_cookie(domain='.facebook.com', name='_js_datr', value=_js_datr)
    browser.get_cookiejar().set_cookie(datr_cookie)
    browser.get_cookiejar().set_cookie(_js_datr_cookie)

    # Perform main login now
    login_page = browser.get(FACEBOOK_LOGIN_URL)

    if login_page.status_code != 200:
        logger.debug(login_page.text)
        logger.error(f'Failed to authenticate with Facebook with email {email}. Stage: Main Login Attempt, Status code: {login_page.status_code}.')
        raise SystemError

    login_form = login_page.soup.find('form', {'id': 'login_form'})
    login_form.find('input', {'id': 'email'})['value'] = email
    login_form.find('input', {'id': 'pass'})['value'] = password
    login_response = browser.submit(login_form, login_page.url)

    if login_response.status_code != 200:
        logger.debug(login_response.text)
        logger.error(f'Failed to authenticate with Facebook with email {email}. Stage: Main Login Reponse, Status code: {login_response.status_code}.')
        raise SystemError

    # Check to see if login failed
    if login_response.soup.find('link', {'rel': 'canonical', 'href': 'https://www.facebook.com/login/'}):
        logger.debug(login_response.text)
        logger.error(f'Failed to authenticate with Facebook with email {email}. Please check provided email/password.')
        raise SystemError

    # Check to see if we hit Facebook security checkpoint
    if login_response.soup.find('button', {'id': 'checkpointSubmitButton'}):
        logger.debug(login_response.text)
        logger.error(f'Hit Facebook security checkpoint. Please login to Facebook manually and follow prompts to authorize this device.')
        raise SystemError

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
        logger.debug(birthday_event_page.text)
        logger.error(f'Failed to retreive birthday event page. Status code: {birthday_event_page.status_code}.')
        raise SystemError

    matches = regexp.search(birthday_event_page.text)

    if not matches or len(matches.groups()) != 1:
        logger.debug(birthday_event_page.text)
        logger.error(f'Match failed or unexpected number of regexp matches when trying to get async token.')
        raise SystemError
    
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
        logger.debug(response.text)
        logger.error(f'Failed to get Facebook locale. Params: {query_params}. Status code: {response.status_code}.')
        raise SystemError

    # Parse json response
    try:
        json_response = json.loads(strip_ajax_response_prefix(response.text))
        current_locale = json_response['jsmods']['require'][0][3][1]['currentLocale']
    except json.decoder.JSONDecodeError as e:
        logger.debug(response.text)
        logger.error(f'JSONDecodeError: {e}')
        raise SystemError
    except KeyError as e:
        logger.debug(json_response)
        logger.error(f'KeyError: {e}')
        raise SystemError

    # Validate locale
    if not regexp.match(current_locale):
        logger.error(f'Invalid Facebook locale fetched: {current_locale}.')
        raise SystemError

    __locale = current_locale

    return __locale


def get_async_birthdays(browser):
    """ Returns list of birthday objects by querying the Facebook birthday async page """
    
    FACEBOOK_BIRTHDAY_ASYNC_ENDPOINT = 'https://www.facebook.com/async/birthdays/?'

    birthdays = []

    next_12_months_epoch_timestamps = get_next_12_month_epoch_timestamps()

    for epoch_timestamp in next_12_months_epoch_timestamps:
        logger.info(f'Processing birthdays for month {datetime.fromtimestamp(epoch_timestamp).strftime("%B")}.')

        # Not all fields are required for response to be given, required fields are date, fb_dtsg_ag and __a
        query_params = {'date': epoch_timestamp,
                        'fb_dtsg_ag': get_async_token(browser),
                        '__a': '1'}
        
        response = browser.get(FACEBOOK_BIRTHDAY_ASYNC_ENDPOINT + urllib.parse.urlencode(query_params))
        
        if response.status_code != 200:
            logger.debug(response.text)
            logger.error(f'Failed to get async birthday response. Params: {query_params}. Status code: {response.status_code}.')
            raise SystemError
        
        birthdays_for_month = parse_birthday_async_output(browser, response.text)
        birthdays.extend(birthdays_for_month)
        logger.info(f'Found {len(birthdays_for_month)} birthdays for month {datetime.fromtimestamp(epoch_timestamp).strftime("%B")}.')

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
    
    logger.debug(f'Epoch timestamps are: {epoch_timestamps}')
    return epoch_timestamps

def parse_birthday_async_output(browser, text):
    """ Parsed Birthday Async output text and returns list of Birthday objects """
    BIRTHDAY_STRING_REGEXP_STRING = r'class=\"_43q7\".*?href=\"https://www\.facebook\.com/(.*?)\".*?data-tooltip-content=\"(.*?)\">.*?alt=\"(.*?)\".*?/>'
    regexp = re.compile(BIRTHDAY_STRING_REGEXP_STRING, re.MULTILINE)
    
    birthdays = []

    # Fetch birthday card html payload from json response
    try:
        json_response = json.loads(strip_ajax_response_prefix(text))
        logger.debug(json_response) # TODO: Remove once domops error fixed #32
        birthday_card_html = json_response['domops'][0][3]['__html']
    except json.decoder.JSONDecodeError as e:
        logger.debug(text)
        logger.error(f'JSONDecodeError: {e}')
        raise SystemError
    except KeyError as e:
        logger.debug(json_response)
        logger.error(f'KeyError: {e}')
        raise SystemError

    user_locale = get_facebook_locale(browser)

    for vanity_name, tooltip_content, name in regexp.findall(birthday_card_html):
        # Generate a unique ID in compliance with RFC 2445 ICS - 4.8.4.7 Unique Identifier
        trim_start = 15 if vanity_name.startswith('profile.php?id=') else 0
        uid = f'{vanity_name[trim_start:]}@github.com/mobeigi/fb2cal'
        
        # Parse tooltip content into day/month
        day, month = parse_birthday_day_month(tooltip_content, name, user_locale)

        birthdays.append(Birthday(uid, html.unescape(name), day, month))

    return birthdays

def parse_birthday_day_month(tooltip_content, name, user_locale):
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
    if user_locale not in locale_date_format_mapping:
        logger.error(f'The locale {user_locale} is not supported by Facebook.')
        raise SystemError
    
    try:
        # Try to parse the date using appropriate format based on locale
        # We are only interested in the parsed day and month here so we also pass in a leap year to cover the special case of Feb 29
        parsed_date = datetime.strptime(f'{birthday_date_str}/1972', locale_date_format_mapping[user_locale] + "/%Y")
        return (parsed_date.day, parsed_date.month)
    except ValueError:
        # Otherwise, have to convert day names to a day and month
        offset_dict = get_day_name_offset_dict(user_locale)
        cur_date = datetime.now()

        # Use beautiful soup to parse special html codes properly before matching with our dict
        day_name = BeautifulSoup(birthday_date_str).get_text().lower()

        if day_name in offset_dict:
            cur_date = cur_date + relativedelta(days=offset_dict[day_name])
            return (cur_date.day, cur_date.month)

    logger.error(f'Failed to parse birthday day/month. Parse failed with tooltip_content: "{tooltip_content}", locale: "{user_locale}". Day name "{day_name}" is not in the offset dict {offset_dict}')
    raise SystemError

def get_day_name_offset_dict(user_locale):
    """ The day name to offset dict maps a day name to a numerical day offset which can be used to add days to the current date.
        Day names will match the provided user locale and will be in lowercase.
    """

    offset_dict = {}

    # Todays birthdays will be shown normally (as a date) so start from tomorrow
    start_date = datetime.now() + relativedelta(days=1)

    # Method 1: Babel
    try:
        babel_locale = Locale.parse(user_locale, sep='_')
        cur_date = start_date

        # Iterate through the following 7 days
        for i in range(1, 8):
            offset_dict[format_date(cur_date, 'EEEE', locale=babel_locale).lower()] = i
            cur_date = cur_date + relativedelta(days=1)

        return offset_dict
    except UnknownLocaleError as e:
        logger.debug(f'Babel UnknownLocaleError: {e}')

    # Method 2: System locale
    cur_date = start_date
    locale_check_list = [user_locale, user_locale + 'UTF-8', user_locale + 'utf-8']
    system_locale = None

    # Windows
    if any(platform.win32_ver()):
        for locale_to_check in locale_check_list:
            if locale_to_check in locale.windows_locale.values():
                system_locale = locale_to_check
                break
    # POSIX
    else:
        for locale_to_check in locale_check_list:
            if locale_to_check in locale.locale_alias.values():
                system_locale = locale_to_check
                break

    # Check if system locale was found
    if system_locale:
        locale.setlocale(locale.LC_ALL, system_locale)

        # Iterate through the following 7 days
        for i in range(1, 8):
            offset_dict[cur_date.strftime('%A').lower()] = i
            cur_date = cur_date + relativedelta(days=1)

        return offset_dict
    else:
        logger.debug(f"Unable to find system locale for provided user locale: '{user_locale}'")

    # Failure
    logger.error(f"Failed to generate day name offset dictionary for provided user locale: '{user_locale}'")
    raise SystemError

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
    c.creator = f'fb2cal v{__version__} ({__status__}) [{__website__}]'
    c.extra.append(ContentLine(name='X-WR-CALNAME', value='Facebook Birthdays (fb2cal)'))
    c.extra.append(ContentLine(name='X-PUBLISHED-TTL', value='PT12H'))
    c.extra.append(ContentLine(name='X-ORIGINAL-URL', value='/events/birthdays/'))

    cur_date = datetime.now()

    for birthday in birthdays:
        e = Event()
        e.uid = birthday.uid
        e.created = cur_date
        e.name = f"{birthday.name}'s Birthday"

        # Calculate the year as this year or next year based on if its past current month or not
        # Also pad day, month with leading zeros to 2dp
        year = cur_date.year if birthday.month >= cur_date.month else (cur_date + relativedelta(years=1)).year
        
        # Feb 29 special case: 
        # If event year is not a leap year, use Feb 28 as birthday date instead
        if birthday.month == 2 and birthday.day == 29 and not calendar.isleap(year):
            birthday.day = 28

        month = '{:02d}'.format(birthday.month)
        day = '{:02d}'.format(birthday.day)
        e.begin = f'{year}-{month}-{day} 00:00:00'
        e.make_all_day()
        e.duration = timedelta(days=1)
        e.extra.append(ContentLine(name='RRULE', value='FREQ=YEARLY'))

        c.events.add(e)

    return c

if __name__ == '__main__':
    logger = setup_custom_logger('fb2cal')
    logger.info(f'Starting fb2cal v{__version__} ({__status__}) [{__website__}]')
    logger.info(f'This project is released under the {__license__} license.')

    try:
        main()
    except SystemExit:
        logger.critical(f'Critical error encountered. Terminating.')
        sys.exit()
    finally:
        logging.shutdown()

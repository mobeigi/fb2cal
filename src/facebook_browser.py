import mechanicalsoup
import re
import requests
import json
from datetime import datetime
from logger import Logger
from utils import get_next_12_month_epoch_timestamps, strip_ajax_response_prefix
import urllib.parse
from transformer import Transformer

class FacebookBrowser:
    def __init__(self):
        """ Initialize browser as needed """
        self.logger = Logger('fb2cal').getLogger()
        self.browser = mechanicalsoup.StatefulBrowser()
        self.browser.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36')
        self.__cached_async_token = None
        self.__cached_locale = None

    def authenticate(self, email, password):
        """ Authenticate with Facebook setting up session for further requests """
        
        FACEBOOK_LOGIN_URL = 'http://www.facebook.com/login.php'
        FACEBOOK_DATR_TOKEN_REGEXP = r'\"_js_datr\",\"(.*?)\"'
        regexp = re.compile(FACEBOOK_DATR_TOKEN_REGEXP, re.MULTILINE)

        # Add 'datr' cookie to session for countries adhering to GDPR compliance
        login_page = self.browser.get(FACEBOOK_LOGIN_URL)
        
        if login_page.status_code != 200:
            self.logger.debug(login_page.text)
            self.logger.error(f'Failed to authenticate with Facebook with email {email}. Stage: Initial Request for datr Token, Status code: {login_page.status_code}.')
            raise SystemError

        matches = regexp.search(login_page.text)

        if not matches or len(matches.groups()) != 1:
            self.logger.debug(login_page.text)
            self.logger.error(f'Match failed or unexpected number of regexp matches when trying to get datr token.')
            raise SystemError
        
        _js_datr = matches[1]
        
        datr_cookie = requests.cookies.create_cookie(domain='.facebook.com', name='datr', value=_js_datr)
        _js_datr_cookie = requests.cookies.create_cookie(domain='.facebook.com', name='_js_datr', value=_js_datr)
        self.browser.get_cookiejar().set_cookie(datr_cookie)
        self.browser.get_cookiejar().set_cookie(_js_datr_cookie)

        # Perform main login now
        login_page = self.browser.get(FACEBOOK_LOGIN_URL)

        if login_page.status_code != 200:
            self.logger.debug(login_page.text)
            self.logger.error(f'Failed to authenticate with Facebook with email {email}. Stage: Main Login Attempt, Status code: {login_page.status_code}.')
            raise SystemError

        login_form = login_page.soup.find('form', {'id': 'login_form'})
        login_form.find('input', {'id': 'email'})['value'] = email
        login_form.find('input', {'id': 'pass'})['value'] = password
        login_response = self.browser.submit(login_form, login_page.url)

        if login_response.status_code != 200:
            self.logger.debug(login_response.text)
            self.logger.error(f'Failed to authenticate with Facebook with email {email}. Stage: Main Login Reponse, Status code: {login_response.status_code}.')
            raise SystemError

        # Check to see if login failed
        if login_response.soup.find('link', {'rel': 'canonical', 'href': 'https://www.facebook.com/login/'}):
            self.logger.debug(login_response.text)
            self.logger.error(f'Failed to authenticate with Facebook with email {email}. Please check provided email/password.')
            raise SystemError

        # Check to see if we hit Facebook security checkpoint
        if login_response.soup.find('button', {'id': 'checkpointSubmitButton'}):
            self.logger.debug(login_response.text)
            self.logger.error(f'Hit Facebook security checkpoint. Please login to Facebook manually and follow prompts to authorize this device.')
            raise SystemError


    def get_async_birthdays(self):
        """ Returns list of birthday objects by querying the Facebook birthday async page """
        
        FACEBOOK_BIRTHDAY_ASYNC_ENDPOINT = 'https://www.facebook.com/async/birthdays/?'
        birthdays = []
        next_12_months_epoch_timestamps = get_next_12_month_epoch_timestamps()

        transformer = Transformer()
        user_locale = self.get_facebook_locale()

        for epoch_timestamp in next_12_months_epoch_timestamps:
            self.logger.info(f'Processing birthdays for month {datetime.fromtimestamp(epoch_timestamp).strftime("%B")}.')

            # Not all fields are required for response to be given, required fields are date, fb_dtsg_ag and __a
            query_params = {'date': epoch_timestamp,
                            'fb_dtsg_ag': self.get_async_token(),
                            '__a': '1'}
            
            response = self.browser.get(FACEBOOK_BIRTHDAY_ASYNC_ENDPOINT + urllib.parse.urlencode(query_params))
            
            if response.status_code != 200:
                self.logger.debug(response.text)
                self.logger.error(f'Failed to get async birthday response. Params: {query_params}. Status code: {response.status_code}.')
                raise SystemError
            
            birthdays_for_month = transformer.parse_birthday_async_output(response.text, user_locale)
            birthdays.extend(birthdays_for_month)
            self.logger.info(f'Found {len(birthdays_for_month)} birthdays for month {datetime.fromtimestamp(epoch_timestamp).strftime("%B")}.')

        return birthdays

    def get_async_token(self):
        """ Get async authorization token (CSRF protection token) that must be included in all async requests """

        if self.__cached_async_token:
            return self.__cached_async_token

        FACEBOOK_BIRTHDAY_EVENT_PAGE_URL = 'https://www.facebook.com/events/birthdays/' # async token is present on this page
        FACEBOOK_ASYNC_TOKEN_REGEXP_STRING = r'{\"token\":\".*?\",\"async_get_token\":\"(.*?)\"}'
        regexp = re.compile(FACEBOOK_ASYNC_TOKEN_REGEXP_STRING, re.MULTILINE)

        birthday_event_page = self.browser.get(FACEBOOK_BIRTHDAY_EVENT_PAGE_URL)
        
        if birthday_event_page.status_code != 200:
            self.logger.debug(birthday_event_page.text)
            self.logger.error(f'Failed to retreive birthday event page. Status code: {birthday_event_page.status_code}.')
            raise SystemError

        matches = regexp.search(birthday_event_page.text)

        if not matches or len(matches.groups()) != 1:
            self.logger.debug(birthday_event_page.text)
            self.logger.error(f'Match failed or unexpected number of regexp matches when trying to get async token.')
            raise SystemError
        
        self.__cached_async_token = matches[1]
        
        return self.__cached_async_token

    def get_facebook_locale(self):
        """ Returns users Facebook locale """
        
        if self.__cached_locale:
            return self.__cached_locale

        FACEBOOK_LOCALE_ENDPOINT = 'https://www.facebook.com/ajax/settings/language/account.php?'
        FACEBOOK_LOCALE_REGEXP_STRING = r'[a-z]{2}_[A-Z]{2}'
        regexp = re.compile(FACEBOOK_LOCALE_REGEXP_STRING, re.MULTILINE)

        # Not all fields are required for response to be given, required fields are fb_dtsg_ag and __a
        query_params = {'fb_dtsg_ag': self.get_async_token(),
                        '__a': '1'}

        response = self.browser.get(FACEBOOK_LOCALE_ENDPOINT + urllib.parse.urlencode(query_params))
        
        if response.status_code != 200:
            self.logger.debug(response.text)
            self.logger.error(f'Failed to get Facebook locale. Params: {query_params}. Status code: {response.status_code}.')
            raise SystemError

        # Parse json response
        try:
            json_response = json.loads(strip_ajax_response_prefix(response.text))
            current_locale = json_response['jsmods']['require'][0][3][1]['currentLocale']
        except json.decoder.JSONDecodeError as e:
            self.logger.debug(response.text)
            self.logger.error(f'JSONDecodeError: {e}')
            raise SystemError
        except KeyError as e:
            self.logger.debug(json_response)
            self.logger.error(f'KeyError: {e}')
            raise SystemError

        # Validate locale
        if not regexp.match(current_locale):
            self.logger.error(f'Invalid Facebook locale fetched: {current_locale}.')
            raise SystemError

        self.__cached_locale = current_locale

        return self.__cached_locale
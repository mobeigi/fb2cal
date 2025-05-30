import mechanicalsoup
import re
import requests
import json
from bs4 import Tag

from .__init__ import __title__, __version__
from .logger import Logger
from .utils import remove_anti_hijacking_protection, facebook_web_encrypt_password

class FacebookBrowser:
    def __init__(self):
        """ Initialize browser as needed """
        self.logger = Logger('fb2cal').getLogger()
        self.browser = mechanicalsoup.StatefulBrowser()
        self.browser.set_user_agent('{__title__}/{__version__}') # Custom user agent to bypass bot detection / 2FA trigger
        self.__cached_token = None

    def _get_datr_token_from_html(self, html):
        FACEBOOK_DATR_TOKEN_REGEXP = r'\"_js_datr\",\"(.*?)\"'
        regexp = re.compile(FACEBOOK_DATR_TOKEN_REGEXP, re.MULTILINE)

        matches = regexp.search(html)

        if not matches or len(matches.groups()) != 1:
            self.logger.debug(html)
            self.logger.error(f'Match failed or unexpected number of regexp matches when trying to get datr token.')
            raise SystemError
        
        return matches[1]

    def _get_pubkey_from_html(self, html):
        FACEBOOK_PUBKEY_REGEXP = r'\"pubKey\":{"publicKey":"(.+?)","keyId":(\d+?)}}'
        regexp = re.compile(FACEBOOK_PUBKEY_REGEXP, re.MULTILINE)

        matches = regexp.search(html)

        if not matches or len(matches.groups()) != 2:
            self.logger.debug(html)
            self.logger.error(f'Match failed or unexpected number of regexp matches when trying to get pubKey.')
            raise SystemError
        
        public_key = matches[1]
        key_id = int(matches[2])

        return (public_key, key_id)

    def authenticate(self, email, password):
        """ Authenticate with Facebook setting up session for further requests """
        
        FACEBOOK_LOGIN_URL = 'https://www.facebook.com/login'

        login_page = self.browser.open(FACEBOOK_LOGIN_URL)

        if login_page.status_code != 200:
            self.logger.debug(login_page.text)
            self.logger.error(f'Failed to authenticate with Facebook with email {email}. Stage: Initial Request for datr Token, Status code: {login_page.status_code}.')
            raise SystemError

        # Add 'datr' cookie to session for countries adhering to GDPR compliance        
        _js_datr = self._get_datr_token_from_html(login_page.text)
        
        datr_cookie = requests.cookies.create_cookie(domain='.facebook.com', name='datr', value=_js_datr)
        self.browser.get_cookiejar().set_cookie(datr_cookie)

        _js_datr_cookie = requests.cookies.create_cookie(domain='.facebook.com', name='_js_datr', value=_js_datr)
        self.browser.get_cookiejar().set_cookie(_js_datr_cookie)

        # Prepare to send form
        login_form = self.browser.select_form("form#login_form")
        if login_form is None:
            self.logger.error("Could not find login form.")
            raise SystemError
        
        login_form.set("email", email)

        # Encrypt password into enc_pass
        # Facebook only accepts encrypted passwords in a specific format
        public_key, key_id = self._get_pubkey_from_html(login_page.text)
        enc_pass = facebook_web_encrypt_password(key_id, public_key, password)

        # enc_pass is typically computed and included in requests pre-flight with javascript
        # Since we aren't executing javascript we'll just create the input field and include it here so it makes it into our request
        enc_pass_input = Tag(name="input", attrs={"type": "hidden", "name": "encpass", "value": enc_pass})
        login_form.form.append(enc_pass_input)

        login_response = self.browser.submit_selected()

        if login_response.status_code != 200:
            self.logger.debug(login_response.text)
            self.logger.error(f'Failed to authenticate with Facebook with email {email}. Stage: Main Login Reponse, Status code: {login_response.status_code}.')
            raise SystemError

        # Check to see if login failed
        # We do this by checking to see if the `c_user` cookie is set to the users numeric Facebook ID
        c_user = self.browser.get_cookiejar().get('c_user', default=None)

        if not c_user or not c_user.isnumeric():
            self.logger.debug(login_response.text)
            self.logger.debug(f'Cookie(c_user) : {c_user}')
            self.logger.error(f'Failed to authenticate with Facebook with email {email}. Please check provided email/password.')
            raise SystemError

        # Check to see if we hit Facebook security checkpoint
        if login_response.soup.find('button', {'id': 'checkpointSubmitButton'}):
            self.logger.debug(login_response.text)
            self.logger.error(f'Hit Facebook security checkpoint. Please login to Facebook manually and follow prompts to authorize this device.')
            raise SystemError

    def get_token(self):
        """ Get authorization token (CSRF protection token) that must be included in all requests """

        if self.__cached_token:
            return self.__cached_token

        FACEBOOK_BIRTHDAY_EVENT_PAGE_URL = 'https://www.facebook.com/events/birthdays/' # token is present on this page
        FACEBOOK_TOKEN_REGEXP_STRING = r'\[\"DTSGInitialData\",\[],{\"token\":\"(.*?)\"'
        regexp = re.compile(FACEBOOK_TOKEN_REGEXP_STRING, re.MULTILINE)

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
        
        self.__cached_token = matches[1]
        
        return self.__cached_token

    def query_graph_ql_birthday_comet_monthly(self, offset_month):
        """ Query the GraphQL BirthdayCometMonthlyBirthdaysRefetchQuery endpoint that powers the https://www.facebook.com/events/birthdays page 
            This endpoint will return all Birthdays for the offset_month plus the following 2 consecutive months. """

        FACEBOOK_GRAPHQL_ENDPOINT = 'https://www.facebook.com/api/graphql/'
        FACEBOOK_GRAPHQL_API_REQ_FRIENDLY_NAME = 'BirthdayCometMonthlyBirthdaysRefetchQuery'
        DOC_ID = 5347559575302259

        variables = {
            'offset_month': offset_month,
            'scale': 1.5
        }

        payload = {
            'fb_api_req_friendly_name': FACEBOOK_GRAPHQL_API_REQ_FRIENDLY_NAME,
            'variables': json.dumps(variables),
            'doc_id': DOC_ID,
            'fb_dtsg': self.get_token(),
            '__a': '1'
        }

        response = self.browser.post(FACEBOOK_GRAPHQL_ENDPOINT, data=payload)

        # Sanity failsafe, GraphQL relay endpoint will always return 200
        if response.status_code != 200:
            self.logger.debug(response.text)
            self.logger.error(f'Failed to get {FACEBOOK_GRAPHQL_API_REQ_FRIENDLY_NAME} response. Payload: {payload}. Status code: {response.status_code}.')
            raise SystemError
        
        trimmed_response = remove_anti_hijacking_protection(response.text)
        response_json = json.loads(trimmed_response)

        # Validate for errors
        if 'error' in response_json:
            self.logger.debug(response.text)
            self.logger.error(f'Failed to parse {FACEBOOK_GRAPHQL_API_REQ_FRIENDLY_NAME} response. Payload: {payload}. Error: {response_json["errorSummary"]} - {response_json["errorDescription"]}')
            raise SystemError

        return response_json

import mechanicalsoup
import re
import requests
import json

from .logger import Logger

class FacebookBrowser:
    def __init__(self):
        """ Initialize browser as needed """
        self.logger = Logger('fb2cal').getLogger()
        self.browser = mechanicalsoup.StatefulBrowser()
        self.browser.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36')
        self.__cached_token = None
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
        FACEBOOK_TOKEN_REGEXP_STRING = r'{\"token\":\"(.*?)\"'
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

        if response.status_code != 200:
            self.logger.debug(response.text)
            self.logger.error(f'Failed to get {FACEBOOK_GRAPHQL_API_REQ_FRIENDLY_NAME} response. Payload: {payload}. Status code: {response.status_code}.')
            raise SystemError
        
        return response.json()

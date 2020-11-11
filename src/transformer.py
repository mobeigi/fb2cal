import re
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
from logger import Logger
from utils import strip_ajax_response_prefix
from birthday import Birthday
from babel import Locale
from babel.core import UnknownLocaleError
from babel.dates import format_date
import locale
import platform
import html

class Transformer:
    def __init__(self):
        self.logger = Logger('fb2cal').getLogger()

    def parse_birthday_async_output(self, text, user_locale):
        """ Parsed Birthday Async output text and returns list of Birthday objects """
        BIRTHDAY_STRING_REGEXP_STRING = r'class=\"_43q7\".*?href=\"https://www\.facebook\.com/(.*?)\".*?data-tooltip-content=\"(.*?)\">.*?alt=\"(.*?)\".*?/>'
        regexp = re.compile(BIRTHDAY_STRING_REGEXP_STRING, re.MULTILINE)
        
        birthdays = []

        # Fetch birthday card html payload from json response
        try:
            json_response = json.loads(strip_ajax_response_prefix(text))
            self.logger.debug(json_response) # TODO: Remove once domops error fixed #32
            birthday_card_html = json_response['domops'][0][3]['__html']
        except json.decoder.JSONDecodeError as e:
            self.logger.debug(text)
            self.logger.error(f'JSONDecodeError: {e}')
            raise SystemError
        except KeyError as e:
            self.logger.debug(json_response)
            self.logger.error(f'KeyError: {e}')
            raise SystemError
        
        for vanity_name, tooltip_content, name in regexp.findall(birthday_card_html):
            # Generate a unique ID in compliance with RFC 2445 ICS - 4.8.4.7 Unique Identifier
            trim_start = 15 if vanity_name.startswith('profile.php?id=') else 0
            uid = f'{vanity_name[trim_start:]}@github.com/mobeigi/fb2cal'
            
            # Parse tooltip content into day/month
            day, month = self.__parse_birthday_day_month(tooltip_content, name, user_locale)

            birthdays.append(Birthday(uid, html.unescape(name), day, month))

        return birthdays

    def __parse_birthday_day_month(self, tooltip_content, name, user_locale):
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
            self.logger.error(f'The locale {user_locale} is not supported by Facebook.')
            raise SystemError
        
        try:
            # Try to parse the date using appropriate format based on locale
            # We are only interested in the parsed day and month here so we also pass in a leap year to cover the special case of Feb 29
            parsed_date = datetime.strptime(f'{birthday_date_str}/1972', locale_date_format_mapping[user_locale] + "/%Y")
            return (parsed_date.day, parsed_date.month)
        except ValueError:
            # Otherwise, have to convert day names to a day and month
            offset_dict = self.__get_day_name_offset_dict(user_locale)
            cur_date = datetime.now()

            # Use beautiful soup to parse special html codes properly before matching with our dict
            day_name = BeautifulSoup(birthday_date_str).get_text().lower()

            if day_name in offset_dict:
                cur_date = cur_date + relativedelta(days=offset_dict[day_name])
                return (cur_date.day, cur_date.month)

        self.logger.error(f'Failed to parse birthday day/month. Parse failed with tooltip_content: "{tooltip_content}", locale: "{user_locale}". Day name "{day_name}" is not in the offset dict {offset_dict}')
        raise SystemError

    def __get_day_name_offset_dict(self, user_locale):
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
            self.logger.debug(f'Babel UnknownLocaleError: {e}')

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
            self.logger.debug(f"Unable to find system locale for provided user locale: '{user_locale}'")

        # Failure
        self.logger.error(f"Failed to generate day name offset dictionary for provided user locale: '{user_locale}'")
        raise SystemError
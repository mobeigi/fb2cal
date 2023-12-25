import os
from ics import Calendar, Event
from ics.grammar.parse import ContentLine
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar

from .logger import Logger
from .utils import generate_facebook_profile_url_permalink
from .__init__ import __version__, __status__, __github_short_url__

""" Write Birthdays to an ICS file """
class ICSWriter:

    def __init__(self, facebook_users):
        self.logger = Logger('fb2cal').getLogger()
        self.facebook_users = facebook_users

    def generate(self):
        c = Calendar()
        c.scale = 'GREGORIAN'
        c.method = 'PUBLISH'
        c.creator = f'fb2cal v{__version__} ({__status__}) [{__github_short_url__}]'
        c.extra.append(ContentLine(name='X-WR-CALNAME', value='Facebook Birthdays (fb2cal)'))
        c.extra.append(ContentLine(name='X-PUBLISHED-TTL', value='PT12H'))
        c.extra.append(ContentLine(name='X-ORIGINAL-URL', value='/events/birthdays/'))

        cur_date = datetime.now()

        for facebook_user in self.facebook_users:
            # Don't add extra 's' if name already ends with 's'
            formatted_username = f"{facebook_user.name}'s" if facebook_user.name[-1] != 's' else f"{facebook_user.name}'"
            formatted_username = f'{formatted_username} Birthday'

            # Set date components
            day = facebook_user.birthday_day
            month = facebook_user.birthday_month
            year = facebook_user.birthday_year

            # Feb 29 special case:
            # If event year is not a leap year, use Feb 28 as birthday date instead
            if facebook_user.birthday_month == 2 and facebook_user.birthday_day == 29 and not calendar.isleap(year):
                day = 28

            # The birth year may not be visible due to privacy settings
            # In this case, calculate the year as this year or next year based on if its past current month or not
            if year is None:
                year = cur_date.year if facebook_user.birthday_month >= cur_date.month else (cur_date + relativedelta(years=1)).year

            # Format date components as needed
            month = f'{month:02}'
            day = f'{day:02}'

            # Event meta data
            e = Event()

            e.uid = facebook_user.id
            e.name = formatted_username
            e.created = cur_date
            e.description = f'{facebook_user}\n{generate_facebook_profile_url_permalink(facebook_user)}'
            e.begin = f'{year}-{month}-{day} 00:00:00'
            e.make_all_day()
            e.duration = timedelta(days=1)
            e.extra.append(ContentLine(name='RRULE', value='FREQ=YEARLY'))

            c.events.add(e)

        self.birthday_calendar = c

    def write(self, ics_file_path):
        # Remove blank lines
        ics_str = ''.join([line.rstrip('\n') for line in self.birthday_calendar])
        self.logger.debug(f'ics_str: {ics_str}')

        self.logger.info(f'Saving ICS file to local file system...')

        if not os.path.exists(os.path.dirname(ics_file_path)):
            os.makedirs(os.path.dirname(ics_file_path), exist_ok=True)

        with open(ics_file_path, mode='w', encoding="UTF-8") as ics_file:
            ics_file.write(ics_str)
        self.logger.info(f'Successfully saved ICS file to {os.path.abspath(ics_file_path)}')

    def get_birthday_calendar(self):
        return self.birthday_calendar

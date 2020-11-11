import os
import ics
from ics import Calendar, Event
from ics.grammar.parse import ContentLine
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar

from __init__ import __version__, __status__, __website__

""" Write Birthdays to an ICS file """
class ICSWriter:

    def __init__(self, birthdays):
        self.birthdays = birthdays

    def generate(self):
        c = Calendar()
        c.scale = 'GREGORIAN'
        c.method = 'PUBLISH'
        c.creator = f'fb2cal v{__version__} ({__status__}) [{__website__}]'
        c.extra.append(ContentLine(name='X-WR-CALNAME', value='Facebook Birthdays (fb2cal)'))
        c.extra.append(ContentLine(name='X-PUBLISHED-TTL', value='PT12H'))
        c.extra.append(ContentLine(name='X-ORIGINAL-URL', value='/events/birthdays/'))

        cur_date = datetime.now()

        for birthday in self.birthdays:
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

        self.birthday_calendar = c

    def write(self, ics_file_path):
        # Remove blank lines
        ics_str = ''.join([line.rstrip('\n') for line in self.birthday_calendar])
        # logger.debug(f'ics_str: {ics_str}')

        # logger.info(f'Saving ICS file to local file system...')

        if not os.path.exists(os.path.dirname(ics_file_path)):
            os.makedirs(os.path.dirname(ics_file_path), exist_ok=True)

        with open(ics_file_path, mode='w', encoding="UTF-8") as ics_file:
            ics_file.write(ics_str)
        #logger.info(f'Successfully saved ICS file to {os.path.abspath(ics_file_path)}')

import unittest
from unittest.mock import patch
from datetime import datetime, date
from ics import Calendar, Event

from fb2cal import ICSWriter, FacebookUser

class TestICSWriter(unittest.TestCase):
    def setUp(self):
        self.facebook_users = [
            FacebookUser(
                '100000000', 
                'John Smith', 
                'https://www.facebook.com/john.smith.23', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000001_10161077510019848_299841799451806933_o.jpg',
                20,
                1,
            ),
            FacebookUser(
                '100000001', 
                'Laura Daisy', 
                'https://www.facebook.com/laura.dasy.2', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000002_10161077510019848_299841799451806933_o.jpg',
                12,
                3,
            ),
            FacebookUser(
                '100000002', 
                '韩忠清', 
                'https://www.facebook.com/韩忠清', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000002_10161077510019848_299841799451806933_o.jpg',
                6,
                6,
            ),
            FacebookUser(
                '100000003', 
                'حكيم هديّة', 
                'https://www.facebook.com/hadiyya', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000003_10161077510019848_299841799451806933_o.jpg',
                26,
                10,
            ),
            FacebookUser(
                '100000004', 
                'Leap Year', 
                'https://www.facebook.com/leap.year', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000004_10161077510019848_299841799451806933_o.jpg',
                29,
                2,
            ),
            FacebookUser(
                '100000005', 
                'Mónica Bellucci',
                'https://www.facebook.com/mo.lucci', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000005_10161077510019848_299841799451806933_o.jpg',
                31,
                12,
            ),
            FacebookUser(
                '100000006', 
                'Bob Jones',
                'https://www.facebook.com/bob.jones', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000005_10161077510019848_299841799451806933_o.jpg',
                24,
                5,
            ),
        ]
        self.ics_writer = ICSWriter(self.facebook_users)
        self.maxDiff = None

    def test_ics_writer_equivalence(self):
        
        with patch('datetime.date') as mock_date:
            mock_date.now.return_value = date(2010, 10, 8)
            print(datetime.now())

        self.ics_writer.generate()
        actual_calendar = self.ics_writer.get_birthday_calendar()
        expected = """BEGIN:VCALENDAR
X-WR-CALNAME:Facebook Birthdays (fb2cal)
X-PUBLISHED-TTL:PT12H
X-ORIGINAL-URL:/events/birthdays/
CALSCALE:GREGORIAN
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:20210120
DTSTAMP:20201113T071402Z
DURATION:P1D
SUMMARY:John Smith's Birthday
UID:100000000
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:20210312
DTSTAMP:20201113T071402Z
DURATION:P1D
SUMMARY:Laura Daisy's Birthday
UID:100000001
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:20210606
DTSTAMP:20201113T071402Z
DURATION:P1D
SUMMARY:韩忠清's Birthday
UID:100000002
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:20211026
DTSTAMP:20201113T071402Z
DURATION:P1D
SUMMARY:حكيم هديّة's Birthday
UID:100000003
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:20210228
DTSTAMP:20201113T071402Z
DURATION:P1D
SUMMARY:Leap Year's Birthday
UID:100000004
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:20201231
DTSTAMP:20201113T071402Z
DURATION:P1D
SUMMARY:Mónica Bellucci's Birthday
UID:100000005
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:20210524
DTSTAMP:20201113T071402Z
DURATION:P1D
SUMMARY:Bob Jones' Birthday
UID:100000006
END:VEVENT
METHOD:PUBLISH
PRODID:fb2cal v1.2.0 (Production) [https://git.io/fjMwr]
VERSION:2.0
END:VCALENDAR
"""

        expected_calendar = Calendar(expected)

        for actual, expected in zip(actual_calendar.events, expected_calendar.events):
            self.assertEqual(actual.uid, expected.uid)
            self.assertEqual(actual.name, expected.name)
            self.assertEqual(actual.begin, expected.begin)
            self.assertEqual(actual.duration, expected.duration)

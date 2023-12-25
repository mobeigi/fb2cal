import unittest
from ics import Calendar
from freezegun import freeze_time

from fb2cal.ics_writer import ICSWriter
from fb2cal.facebook_user import FacebookUser

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
                1994
            ),
            FacebookUser(
                '100000001', 
                'Laura Daisy', 
                'https://www.facebook.com/laura.dasy.2', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000002_10161077510019848_299841799451806933_o.jpg',
                12,
                3,
                1974
            ),
            FacebookUser(
                '100000002', 
                '韩忠清', 
                'https://www.facebook.com/韩忠清', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000002_10161077510019848_299841799451806933_o.jpg',
                6,
                6,
                2001
            ),
            FacebookUser(
                '100000003', 
                'حكيم هديّة', 
                'https://www.facebook.com/hadiyya', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000003_10161077510019848_299841799451806933_o.jpg',
                26,
                10,
                1987
            ),
            FacebookUser(
                '100000004', 
                'Leap Year', 
                'https://www.facebook.com/leap.year', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000004_10161077510019848_299841799451806933_o.jpg',
                29,
                2,
                2004
            ),
            FacebookUser(
                '100000005', 
                'Mónica Bellucci',
                'https://www.facebook.com/mo.lucci', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000005_10161077510019848_299841799451806933_o.jpg',
                31,
                12,
                None
            ),
            FacebookUser(
                '100000006', 
                'Bob Jones',
                'https://www.facebook.com/bob.jones', 
                'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/00000005_10161077510019848_299841799451806933_o.jpg',
                24,
                5,
                None
            ),
        ]
        self.ics_writer = ICSWriter(self.facebook_users)
        self.maxDiff = None

    @freeze_time("2020-12-01")
    def test_ics_writer_equivalence(self):
        self.ics_writer.generate()
        actual_calendar = self.ics_writer.get_birthday_calendar()
        expected = """BEGIN:VCALENDAR
X-WR-CALNAME:Facebook Birthdays (fb2cal)
X-PUBLISHED-TTL:PT12H
X-ORIGINAL-URL:/events/birthdays/
CALSCALE:GREGORIAN
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:19940120
DTSTAMP:20201113T071402Z
DESCRIPTION:John Smith (20/01/1994)\\nhttps://www.facebook.com/100000000
DURATION:P1D
SUMMARY:John Smith's Birthday
UID:100000000
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:19740312
DTSTAMP:20201113T071402Z
DESCRIPTION:Laura Daisy (12/03/1974)\\nhttps://www.facebook.com/100000001
DURATION:P1D
SUMMARY:Laura Daisy's Birthday
UID:100000001
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:20010606
DTSTAMP:20201113T071402Z
DESCRIPTION:韩忠清 (06/06/2001)\\nhttps://www.facebook.com/100000002
DURATION:P1D
SUMMARY:韩忠清's Birthday
UID:100000002
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:19871026
DTSTAMP:20201113T071402Z
DESCRIPTION:حكيم هديّة (26/10/1987)\\nhttps://www.facebook.com/100000003
DURATION:P1D
SUMMARY:حكيم هديّة's Birthday
UID:100000003
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:20040229
DTSTAMP:20201113T071402Z
DESCRIPTION:Leap Year (29/02/2004)\\nhttps://www.facebook.com/100000004
DURATION:P1D
SUMMARY:Leap Year's Birthday
UID:100000004
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:20201231
DTSTAMP:20201113T071402Z
DESCRIPTION:Mónica Bellucci (31/12/????)\\nhttps://www.facebook.com/100000005
DURATION:P1D
SUMMARY:Mónica Bellucci's Birthday
UID:100000005
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:20210524
DTSTAMP:20201113T071402Z
DESCRIPTION:Bob Jones (24/05/????)\\nhttps://www.facebook.com/100000006
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
            self.assertEqual(actual.description, expected.description)

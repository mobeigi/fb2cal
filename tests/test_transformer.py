import unittest
from fb2cal.transformer import Transformer

from mocks.birthday_comet_root_mocks import BIRTHDAY_COMET_ROOT_JANUARY_MOCK

class TestTransformer(unittest.TestCase):
    def setUp(self):
        self.transformer = Transformer()
        self.facebook_users = self.transformer.transform_birthday_comet_monthly_to_birthdays(BIRTHDAY_COMET_ROOT_JANUARY_MOCK)

    def test_count(self):
        self.assertEqual(len(self.facebook_users), 3)

    def test_friend_in_november(self):
        friend = self.facebook_users[0]
        self.assertEqual(friend.id, '600009847')
        self.assertEqual(friend.name, 'Pirate Pete')
        self.assertEqual(friend.profile_url, 'https://www.facebook.com/pirate.pete')
        self.assertEqual(friend.profile_picture_uri, 'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/122897864_10161077510019848_299841799681806933_o.jpg?_nc_cat=107&ccb=2&_nc_sid=7206a8&_nc_ohc=yzAYhtdvoMYAX9Zxo1e&_nc_ht=scontent-syd2-1.xx&tp=27&oh=dc48247e31223151bc5d55781a572e2f&oe=5FD254D0')
        self.assertEqual(friend.birthday_day, 1)
        self.assertEqual(friend.birthday_month, 11)
        self.assertEqual(friend.birthday_year, 1982)

    def test_friend_in_december(self):
        friend = self.facebook_users[1]
        self.assertEqual(friend.id, '1000023')
        self.assertEqual(friend.name, 'Santa Claus')
        self.assertEqual(friend.profile_url, 'https://www.facebook.com/santa')
        self.assertEqual(friend.profile_picture_uri, 'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/53497864_10161077510019848_299841799451806933_o.jpg?_nc_cat=107&ccb=2&_nc_sid=7206a8&_nc_ohc=yzAYhtdvoMYAX9Zxo1e&_nc_ht=scontent-syd2-1.xx&tp=27&oh=dc48247e31223151bc5d55781a572e2f&oe=5FD254D0')
        self.assertEqual(friend.birthday_day, 25)
        self.assertEqual(friend.birthday_month, 12)
        self.assertEqual(friend.birthday_year, None)

    def test_friend_in_january(self):
        friend = self.facebook_users[2]
        self.assertEqual(friend.id, '198041065')
        self.assertEqual(friend.name, 'Albus Dumbledore')
        self.assertEqual(friend.profile_url, 'https://www.facebook.com/prof.albus')
        self.assertEqual(friend.profile_picture_uri, 'https://scontent-syd2-1.xx.fbcdn.net/v/t1.0-1/cp0/p60x60/34f34864_10161077510019848_299841799681806933_o.jpg?_nc_cat=107&ccb=2&_nc_sid=7406a8&_nc_ohc=yzAYhtdvoMYAX9Zxo1e&_nc_ht=scontent-syd2-1.xx&tp=27&oh=dc48247e31223151bc5d55781a572e2f&oe=5FD254D0')
        self.assertEqual(friend.birthday_day, 17)
        self.assertEqual(friend.birthday_month, 1)
        self.assertEqual(friend.birthday_year, 1881)

DATE_SEPERATOR = '/'
UNKNOWN_CHAR = '?'

class FacebookUser:
    def __init__(self, id, name, profile_url, profile_picture_uri, birthday_day, birthday_month, birthday_year):
        self.id = id
        self.name = name
        self.profile_url = profile_url
        self.profile_picture_uri = profile_picture_uri
        self.birthday_day = birthday_day
        self.birthday_month = birthday_month
        self.birthday_year = birthday_year

    def __str__(self):
        day = f'{self.birthday_day:02}' if self.birthday_day else UNKNOWN_CHAR*2
        month = f'{self.birthday_month:02}' if self.birthday_month else UNKNOWN_CHAR*2
        year = f'{self.birthday_year:04}' if self.birthday_year else UNKNOWN_CHAR*4
        formatted_birthday = DATE_SEPERATOR.join(filter(None, (day, month, year)))
        return f'{self.name} ({formatted_birthday})'

    def __lt__(self, other):
        return (self.birthday_month < other.birthday_month) and (self.birthday_day < other.birthday_month)

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

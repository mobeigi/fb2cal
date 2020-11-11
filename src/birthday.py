class Birthday:
    def __init__(self, uid, name, day, month):
        self.uid = uid # Unique identififer for person (required for ics events)
        self.name = name
        self.day = day
        self.month = month

    def __str__(self):
        return f'{self.name} ({self.day}/{self.month})'
    
    def __unicode__(self):
        return u'{self.name} ({self.day}/{self.month})'
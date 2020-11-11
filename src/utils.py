import pytz
from datetime import datetime
from dateutil.relativedelta import relativedelta
from logger import Logger

def get_next_12_month_epoch_timestamps():
    """ Returns array of epoch timestamps corresponding to the 1st day of the next 12 months starting from the current month.
        For example, if the current date is 2000-05-20, will return epoch for 2000-05-01, 2000-06-01, 2000-07-01 etc for 12 months """
    
    logger = Logger('fb2cal').getLogger()

    epoch_timestamps = []

    # Facebook timezone seems to use Pacific Standard Time locally for these epochs
    # So we have to convert our 00:00:01 datetime on 1st of month from Pacific to UTC before getting our epoch timestamps
    pdt = pytz.timezone('America/Los_Angeles')
    cur_date = datetime.now()

    # Loop for next 12 months
    for _ in range(12):
        # Reset day to 1 and time to 00:00:01
        cur_date = cur_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Convert from Pacific to UTC and store timestamp
        utc_date = pdt.localize(cur_date).astimezone(pytz.utc)
        epoch_timestamps.append(int(utc_date.timestamp()))
        
        # Move cur_date to 1st of next month
        cur_date = cur_date + relativedelta(months=1)
    
    logger.debug(f'Epoch timestamps are: {epoch_timestamps}')
    return epoch_timestamps

def strip_ajax_response_prefix(payload):
    """ Strip the prefix that Facebook puts in front of AJAX responses """

    if payload.startswith('for (;;);'):
        return payload[9:]
    return payload

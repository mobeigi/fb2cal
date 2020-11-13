import os
import logging

LOGGING_FILE_PATH = 'logs/fb2cal.log'

class Logger:
    def __init__(self, name):
        # Setup logger
        if not os.path.exists(os.path.dirname(LOGGING_FILE_PATH)):
            os.makedirs(os.path.dirname(LOGGING_FILE_PATH), exist_ok=True)

        logging.basicConfig(
            format='[%(asctime)s] %(name)s %(levelname)s (%(funcName)s) %(message)s',
            level=logging.DEBUG,
            handlers=[logging.StreamHandler(),
                    logging.FileHandler(LOGGING_FILE_PATH, encoding='UTF-8')]
        )
    
        self.logger = logging.getLogger(name)

    def getLogger(self):
        return self.logger

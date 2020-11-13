import configparser
from .logger import Logger

CONFIG_FILE_NAME = 'config.ini'
CONFIG_FILE_PATH = f'config/{CONFIG_FILE_NAME}'
CONFIG_FILE_TEMPLATE_NAME = 'config-template.ini'

class Config:
    def __init__(self):
        self.logger = Logger('fb2cal').getLogger()
        self.config = configparser.RawConfigParser()

        # Parse config
        try:
            dataset = self.config.read(CONFIG_FILE_PATH)
            if not dataset:
                self.logger.error(f'{CONFIG_FILE_PATH} does not exist. Please rename {CONFIG_FILE_TEMPLATE_NAME} if you have not done so already.')
                raise SystemExit
        except configparser.Error as e:
            self.logger.error(f'ConfigParser error: {e}')
            raise SystemExit

    def getConfig(self):
        return self.config

#!/usr/bin/env python3

""" 
    fb2cal - Facebook Birthday Events to ICS file converter
    Created by: mobeigi

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import logging
from distutils import util

from .ics_writer import ICSWriter
from .logger import Logger
from .config import Config
from .facebook_browser import FacebookBrowser
from .transformer import Transformer

from .__init__ import __version__, __status__, __website__, __license__

# Set CWD to script directory
os.chdir(sys.path[0])

# Init logger
logger = Logger('fb2cal').getLogger()
logger.info(f'Starting fb2cal v{__version__} ({__status__}) [{__website__}]')
logger.info(f'This project is released under the {__license__} license.')

try:
    # Read config
    logger.info(f'Attemping to parse config file...')
    config = Config().getConfig()
    logger.info('Config successfully loaded.')

    # Set logging level based on config
    try:
        logger.setLevel(getattr(logging, config['LOGGING']['level']))
        logging.getLogger().setLevel(logger.level) # Also set root logger level
    except AttributeError:
        logger.error(f'Invalid logging level specified. Level: {config["LOGGING"]["level"]}')
        raise SystemError
    
    logger.info(f'Logging level set to: {logging.getLevelName(logger.level)}')

    # Init Facebook browser
    facebook_browser = FacebookBrowser()

    # Attempt login
    logger.info('Attemping to authenticate with Facebook...')
    facebook_browser.authenticate(config['AUTH']['FB_EMAIL'], config['AUTH']['FB_PASS'])
    logger.info('Successfully authenticated with Facebook.')

    # Fetch birthdays for a full calendar year and transform them 
    facebook_users = set()
    transformer = Transformer()

    # Endpoint will return all birthdays for offset_month plus the following 2 consecutive months.
    logger.info('Fetching all Birthdays via BirthdayCometRootQuery endpoint...')
    # TODO: See #97, offset_month of 10 is needed here because offset months 6/7 are currently returning equivalent months
    for offset_month in [0, 3, 6, 9, 10]:
        birthday_comet_monthly_json = facebook_browser.query_graph_ql_birthday_comet_monthly(offset_month)
        facebook_users_for_quarter = transformer.transform_birthday_comet_monthly_to_birthdays(birthday_comet_monthly_json)
        facebook_users.update(facebook_users_for_quarter)

    if len(facebook_users) == 0:
        logger.warning(f'Facebook user set is empty. Failed to fetch any birthdays.')
        raise SystemError

    logger.info(f'A total of {len(facebook_users)} birthdays were found.')

    # Generate ICS
    ics_writer = ICSWriter(facebook_users)
    logger.info('Creating birthday ICS file...')
    ics_writer.generate()
    logger.info('ICS file created successfully.')

    # Save to file system
    if util.strtobool(config['FILESYSTEM']['SAVE_TO_FILE']):
        ics_writer.write(config['FILESYSTEM']['ICS_FILE_PATH'])

    logger.info('Done! Terminating gracefully.')
except SystemExit:
    logger.critical(f'Critical error encountered. Terminating.')
    sys.exit()
finally:
    logging.shutdown()

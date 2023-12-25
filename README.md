<p align="center">
<img src="https://i.imgur.com/ToHPLjD.png" height="110px" width="auto"/>
<br/>
<h3 align="center">fb2cal</h3>
<p align="center">Facebook Birthday Events to ICS file converter</p>
<h2></h2>
</p>
<br />

<p align="center">
<a href="../../releases"><img src="https://img.shields.io/github/release/mobeigi/fb2cal.svg?style=flat-square" /></a>
<a href="../../actions"><img src="https://img.shields.io/github/actions/workflow/status/mobeigi/fb2cal/test-fb2cal.yml?style=flat-square" /></a>
<a href="../../issues"><img src="https://img.shields.io/github/issues/mobeigi/fb2cal.svg?style=flat-square" /></a>
<a href="../../pulls"><img src="https://img.shields.io/github/issues-pr/mobeigi/fb2cal.svg?style=flat-square" /></a> 
<a href="LICENSE.md"><img src="https://img.shields.io/github/license/mobeigi/fb2cal.svg?style=flat-square" /></a>
</p>

## Description
Around 20 June 2019, Facebook removed their Facebook Birthday ICS export option.  
This change was unannounced and no reason was ever released.  

fb2cal is a tool which restores this functionality.  
It works by calling endpoints that power the https://www.facebook.com/events/birthdays/ page.  
After gathering a list of birthdays for all the users friends for a full year, it creates a ICS calendar file. This ICS file can then be imported into third party tools (such as Google Calendar or Apple Calendar).

## Caveats
* Facebook accounts secured with 2FA are currently not supported (see [#9](../../issues/9))
* During Facebook authentication, a security checkpoint may trigger that will force you to change your Facebook password.

## Requirements
* Facebook account
* Python 3.9+
* pipenv
* Scheduler tool to automatically run script periodically (optional)

## PyPi Project
https://pypi.org/project/fb2cal/

## Instructions

### PyPi (Recommended)
1. In an empty folder of your choice, set up pipenv environment  
`pipenv install`
2. Install `fb2cal` module:  
`pipenv run pip install fb2cal`
3. Download [config/config-template.ini](https://raw.githubusercontent.com/mobeigi/fb2cal/master/config/config-template.ini) file and store it in `config/config.ini`.
4. Update the `config/config.ini` file and enter your Facebook email and password (no quotes).
5. Run the `fb2cal` module  
`pipenv run python -m fb2cal`
6. Check the output folder (`out` by default) for the created `birthdays.ics` file

### Local
1. Clone repo  
`git clone git@github.com:mobeigi/fb2cal.git`
2. Copy `config/config-template.ini` to `config/config.ini`.
3. Update the `config/config.ini` file and enter your Facebook email and password (no quotes).
4. Set up pipenv environment  
`pipenv install`
5. Run the `fb2cal` module  
`pipenv run python -m fb2cal`
6. Check the output folder (`out` by default) for the created `birthdays.ics` file

## Configuration
This tool can be configured by editing the `config/config.ini` configuration file.

<table> <thead> <tr> <th>Section</th> <th>Key</th> <th>Valid Values</th> <th>Description</th> </tr></thead> <tbody> <tr> <td rowspan=2>AUTH</td><td>fb_email</td><td></td><td>Your Facebook login email</td></tr><tr> <td>fb_password</td><td></td><td>Your Facebook login password</td></tr><tr> <td rowspan=2>FILESYSTEM</td><td>save_to_file</td><td>True, False</td><td>If tool should save ICS file to the local file system</td></tr><tr> <td>ics_file_path</td><td></td><td>Path to save ICS file to (including file name)</td></tr><tr> <td>LOGGING</td><td>level</td><td>DEBUG, INFO, WARNING, ERROR, CRITICAL</td><td>Logging level to use. Default: INFO</td></tr></tbody></table>

## Scheduled Task Frequency
It is recommended to run the script **once every 24 hours** to update the ICS file to ensure it is synchronized with the latest Facebook changes (due to friend addition/removal) and to respect the privacy of users who decide to hide their birthday later on. Facebook originally recommended polling for birthday updates **once every 12 hours** based on the `X-PUBLISHED-TTL:PT12H` header included in their ICS files.

## Testing
1. Set up pipenv environment  
`pipenv install`
2. Install the `fb2cal` module  
`pipenv run python -m pip install .`
3. Run the `unittests` module on the `tests` folder  
`pipenv run python -m unittest discover tests`

## Troubleshooting
If you encounter any issues, please open the `config/config.ini` configuration file and set the `LOGGING` `level` to `DEBUG` (it is `INFO` by default). Include these logs when asking for help.

## Contributions
Contributions are always welcome!
Just make a [pull request](../../pulls).

## Licence
GNU General Public License v3.0

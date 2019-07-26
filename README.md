<p align="center">
<img src="https://i.imgur.com/DdzpT8O.png" height="96px" width="96px"/>
<br/>
<h3 align="center">fb2cal</h3>
<p align="center">Facebook Birthday Events to ICS file converter</p>
<h2></h2>
</p>
<br />

<p align="center">
<a href="../../releases"><img src="https://img.shields.io/github/release/mobeigi/fb2cal.svg?style=flat-square" /></a>
<a href="../../issues"><img src="https://img.shields.io/github/issues/mobeigi/fb2cal.svg?style=flat-square" /></a>
<a href="../../pulls"><img src="https://img.shields.io/github/issues-pr/mobeigi/fb2cal.svg?style=flat-square" /></a> 
<a href="LICENSE.md"><img src="https://img.shields.io/github/license/mobeigi/fb2cal.svg?style=flat-square" /></a>
</p>

## Description
Around 20 June 2019, Facebook removed their Facebook Birthday ics export option.  
This change was announced and no reason was ever released.  
News article: https://www.digitaltrends.com/news/facebook-removes-friends-birthday-export/

This tool is a workaround to restore said functionality.  
It works by calling various async endpoints that power the https://www.facebook.com/events/birthdays/ page.  
After gathering a list of birthdays for all the users friends for a full year, it creates a ICS calendar file which is then stored on Google Drive as a publically shared file. This file can then be imported into Google Calendar (or other tools/websites) as a regular ICS file.

This tool **does not** use the Facebook API.

## Requirements
* python3.6+ (and all required python3 modules)
* Scheduler tool to automatically run script periodically
* Google Drive API access

## Instructions
1. Clone repo  
`git clone git@github.com:mobeigi/fb2cal.git`
2. Create a Google Drive API credentials
   1. Visit the Google Drive APIs page: https://console.developers.google.com/apis/api/drive.googleapis.com/overview
   2. Create a new project (if you don't already have one)
   3. Enable API (if not already enabled)
   4. Create OAuth consent screen if required
   5. Create Credentials (**OAuth client ID**)
   5. Download credentials JSON file
3. Rename credentials JSON file to **credentials.json** and put it in the `src` folder
4. Rename `src/config-template.ini` to `src/config.ini` and enter your Facebook email and password as well as a name for your calender to be saved on Google Drive. Initially, the value for the **drive_file_id** field should be empty.
5. Install required python modules   
`pip install -r requirements.txt`
6. Run script manually once for testing purposes:
`python ./fb2cal.py`
7. Check Google Drive to ensure your ics file was made. 
8. Setup cron jobs/Task Scheduler/Automator to repeatly run the script to periodically generate an updated ics file. It is recommended to run the script **once every 24 hours**.
9. Use the following link to import your ics into Calendar applications (i.e. Google Calendar):  
`http://drive.google.com/uc?export=download&id=DRIVE_FILE_ID`. Replace **DRIVE_FILE_ID** with the autopopulated value found in your `src/config.ini` file.

## Contributions
Contributions are always welcome!
Just make a [pull request](../../pulls).

## Licence
GNU General Public License v3.0

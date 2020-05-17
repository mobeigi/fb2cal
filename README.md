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
<a href="../../issues"><img src="https://img.shields.io/github/issues/mobeigi/fb2cal.svg?style=flat-square" /></a>
<a href="../../pulls"><img src="https://img.shields.io/github/issues-pr/mobeigi/fb2cal.svg?style=flat-square" /></a> 
<a href="LICENSE.md"><img src="https://img.shields.io/github/license/mobeigi/fb2cal.svg?style=flat-square" /></a>
</p>

## Description
Around 20 June 2019, Facebook removed their Facebook Birthday ICS export option.  
This change was unannounced and no reason was ever released.  

fb2cal is a tool which restores this functionality.  
It works by calling various async endpoints that power the https://www.facebook.com/events/birthdays/ page.  
After gathering a list of birthdays for all the users friends for a full year, it creates a ICS calendar file which is then stored on Google Drive as a publically shared file. This ICS file can then be imported into third party tools (such as Google Calendar).  
The ICS file can also be stored on the local file system.

This tool **does not** use the Facebook API.

## Requirements
* Facebook account
* python3.6+ (and all required python3 modules)
* Scheduler tool to automatically run script periodically (optional)
* Google Drive API access (optional)

## Instructions
### Option 1: Save ICS file to filesystem 
1. Clone repo
`git clone git@github.com:mobeigi/fb2cal.git`
2. Rename `config/config-template.ini` to `config/config.ini` and enter your Facebook email and password.
3. Install required python modules   
`pip install -r requirements.txt`
4. Run the script manually:
`python src/fb2cal.py`
5. Import the created `birthdays.ics` file into Calendar applications (i.e. Google Calendar)
### Option 2: Automatically Upload ICS file to Google Drive
1. Clone repo  
`git clone git@github.com:mobeigi/fb2cal.git`
2. Create a Google Drive API credentials
   1. Visit the Google Drive APIs page: https://console.developers.google.com/apis/api/drive.googleapis.com/overview
   2. Create a new project (if you don't already have one)
   3. Enable API (if not already enabled)
   4. Select **API & Services** > **Credentials** from left pane.
   5. Select **Create Credentials** > **OAuth client ID**. Make sure to **Configure content screen** if you are prompted to do so. For the application type select **Other** and then enter any name you like (i.e. fb2cal)
   6. Click **Create** to create your OAuth client ID credentials
   7. Download credentials JSON file
3. Rename credentials JSON file to **credentials.json** and put it in the `src` folder
4. Rename `config/config-template.ini` to `config/config.ini` and enter your Facebook email and password as well as a name for your calender to be saved on Google Drive. Change `upload_to_drive` to `True`. Initially, the value for the **drive_file_id** field should be empty.
5. Install required python modules   
`pip install -r requirements.txt`
6. Run script manually once for testing purposes:
`python ./fb2cal.py`
7. Check Google Drive to ensure your ICS file was made. 
8. Setup Cron Jobs/Task Scheduler/Automator to repeatedly run the script to periodically generate an updated ICS file. See **Scheduled Task Frequency** section for more info.
9. Use the following link to import your ICS file into Calendar applications (i.e. Google Calendar):  
`http://drive.google.com/uc?export=download&id=DRIVE_FILE_ID`. Replace **DRIVE_FILE_ID** with the autopopulated value found in your `config/config.ini` file.

## Configuration
This tool can be configured by editing the `config/config.ini` configuration file.

<table> <thead> <tr style="background-color: inherit"> <th>Section</th> <th>Key</th> <th>Valid Values</th> <th>Description</th> </tr></thead> <tbody> <tr style="background-color: inherit"> <td rowspan=2>AUTH</td><td>fb_email</td><td></td><td>Your Facebook login email</td></tr><tr style="background-color: inherit"> <td>fb_password</td><td></td><td>Your Facebook login password</td></tr><tr style="background-color: inherit"> <td rowspan=3>DRIVE</td><td>upload_to_drive</td><td>True, False</td><td>If tool should automatically upload ICS file to Google Drive</td></tr><tr style="background-color: inherit"> <td>drive_file_id</td><td></td><td>The file id of file to write to on Google Drive. Leave blank to create a new file for the first time.</td></tr><tr style="background-color: inherit"> <td>ics_file_name</td><td></td><td>The name of the file to be stored/updated on Google Drive.</td></tr><tr style="background-color: inherit"> <td rowspan=2>FILESYSTEM</td><td>save_to_file</td><td>True, False</td><td>If tool should save ICS file to the local file system</td></tr><tr style="background-color: inherit"> <td>ics_file_path</td><td></td><td>Path to save ICS file to (including file name)</td></tr><tr style="background-color: inherit"> <td>LOGGING</td><td>level</td><td>DEBUG, INFO, WARNING, ERROR, CRITICAL</td><td>Logging level to use. Default: INFO</td></tr></tbody></table>

## Troubleshooting
If you encounter any issues, please open the `config/config.ini` configuration file and set the `LOGGING` `level` to `DEBUG` (it is `INFO` by default). Include these logs when asking for help.

Also make sure to check the **Caveats** section below.

## fb2cal Setup Guide for Non-Devs [Windows]
[![fb2cal Setup Guide for Non-Devs [Windows]](http://img.youtube.com/vi/UnsbV8EJ8-Y/0.jpg)](http://www.youtube.com/watch?v=UnsbV8EJ8-Y "fb2cal Setup Guide for Non-Devs [Windows]")

## Scheduled Task Frequency
It is recommended to run the script **once every 24 hours** to update the ICS file to ensure it is synchronized with the latest Facebook changes (due to friend addition/removal) and to respect the privacy of users who decide to hide their birthday later on. Facebook originally recommended polling for birthday updates **once every 12 hours** based on the `X-PUBLISHED-TTL:PT12H` header included in their ICS files.

## Caveats
* Facebook accounts secured with 2FA are currently not supported (see [#9](../../issues/9))
* During Facebook authentication, a security checkpoint may trigger that will force you to change your Facebook password.
* Some locales are currently not supported (see [#13](../../issues/13))
* Some supported locales may fail. Consider changing your Facebook language to English temporarily as a workaround. (see [#52](../../issues/52))
* Duplicate birthday events may appear if calendar is reimported after Facebook friends change their username due to performance optimizations. (see [#65](../../pull/65))

## Contributions
Contributions are always welcome!
Just make a [pull request](../../pulls).

## Licence
GNU General Public License v3.0

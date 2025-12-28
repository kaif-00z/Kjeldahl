# 🧪 Google Drive Indexer & Streamer

> High Speed Gdrive Mirror, Indexer & File Streamer Written Asynchronous in Python with FastAPI With Awsome Features & Stablility.

[![Python](https://img.shields.io/badge/Python-v3.14.0-blue)](https://www.python.org/)
[![CodeFactor](https://www.codefactor.io/repository/github/kaif-00z/Google-Drive-Mirror/badge)](https://www.codefactor.io/repository/github/kaif-00z/Google-Drive-Mirror)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/kaif-00z/Google-Drive-Mirror/graphs/commit-activity)
[![Contributors](https://img.shields.io/github/contributors/kaif-00z/Google-Drive-Mirror?style=flat-square&color=green)](https://github.com/kaif-00z/Google-Drive-Mirror/graphs/contributors)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://makeapullrequest.com)
[![License](https://img.shields.io/badge/license-AGPLv3-blue)](https://github.com/kaif-00z/Google-Drive-Mirror/blob/main/LICENSE)

## How to deploy?

### Fork Repo Then click on below button of ur fork repo.
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

### Deployment In VPS

- `git clone https://github.com/kaif-00z/Google-Drive-Mirror.git`

- `nano .env` configure env as per [this](https://github.com/kaif-00z/Google-Drive-Mirror/blob/main/.sample.env)

- `sudo docker build . -t gmirror` (make sure to install docker first using `sudo apt install docker.io`)

- `sudo docker run -p 5000:5000 gmirror:latest` (make sure to change port if you are using custom port)

## Generating Configs & Stuffs

### 🖨 ***Getting Google OAuth API credential file and `token.pickle`***

<details>
    <summary><b>View All Steps<b></summary>
    
**NOTES**

- Old authentication changed, now we can't use bot or replit to generate token.pickle. You need OS with a local browser. For example `Termux`.
- Windows users should install python3 and pip. You can find how to install and use them from google or from this [telegraph](https://telegra.ph/Create-Telegram-Mirror-Leech-Bot-by-Deploying-App-with-Heroku-Branch-using-Github-Workflow-12-06) from [Wiszky](https://github.com/vishnoe115) tutorial.
- You can ONLY open the generated link from `generate_drive_token.py` in local browser.

1. Visit the [Google Cloud Console](https://console.developers.google.com/apis/credentials)
2. Go to the OAuth Consent tab, fill it, and save.
3. Go to the Credentials tab and click Create Credentials -> OAuth Client ID
4. Choose Desktop and Create.
5. Publish your OAuth consent screen App to prevent **token.pickle** from expire
6. Use the download button to download your credentials.
7. Move that file to the root of mirrorbot, and rename it to **credentials.json**
8. Visit [Google API page](https://console.developers.google.com/apis/library)
9. Search for Google Drive Api and enable it
10. Finally, run the script to generate **token.pickle** file for Google Drive:

```
pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib
python3 generate_drive_token.py
```
</details>

### 📈 ***Using Service Accounts (User Rate Limit)***

<details>
    <summary><b>View All Notes<b></summary>
    
>For Service Account to work, you must set `IS_SERVICE_ACCOUNT` = True in config file or environment variables.
>**NOTE**: Using Service Accounts is only recommended while uploading to a Team Drive.

### 1. Generate Service Accounts. [What is Service Account?](https://cloud.google.com/iam/docs/service-accounts)

Let us create only the Service Accounts that we need.

**Warning**: Abuse of this feature is not the aim of this project and we do **NOT** recommend that you make a lot of projects, just one project and 100 SAs allow you plenty of use, its also possible that over abuse might get your projects banned by Google.

>**NOTE**: If you have created SAs in past from this script, you can also just re download the keys by running:

```
python3 gen_sa_accounts.py --download-keys $PROJECTID
```

>**NOTE:** 1 Service Account can upload/copy around 750 GB a day, 1 project can make 100 Service Accounts so you can upload 75 TB a day.

>**NOTE:** All people can copy `2TB/DAY` from each file creator (uploader account), so if you got error `userRateLimitExceeded` that doesn't mean your limit exceeded but file creator limit have been exceeded which is `2TB/DAY`.

#### Two methods to create service accounts

Choose one of these methods

##### 1. Create Service Accounts in existed Project (Recommended Method)

- List your projects ids

```
python3 gen_sa_accounts.py --list-projects
```

- Enable services automatically by this command

```
python3 gen_sa_accounts.py --enable-services $PROJECTID
```

- Create Sevice Accounts to current project

```
python3 gen_sa_accounts.py --create-sas $PROJECTID
```

- Download Sevice Accounts as accounts folder

```
python3 gen_sa_accounts.py --download-keys $PROJECTID
```

##### 2. Create Service Accounts in New Project

```
python3 gen_sa_accounts.py --quick-setup 1 --new-only
```

A folder named accounts will be created which will contain keys for the Service Accounts.

### 2. Add Service Accounts

#### Two methods to add service accounts

Choose one of these methods

##### 1. Add Them To Google Group then to Team Drive (Recommended)

- Mount accounts folder

```
cd accounts
```

- Grab emails form all accounts to emails.txt file that would be created in accounts folder
- `For Windows using PowerShell`

```
$emails = Get-ChildItem .\**.json |Get-Content -Raw |ConvertFrom-Json |Select -ExpandProperty client_email >>emails.txt
```

- `For Linux`

```
grep -oPh '"client_email": "\K[^"]+' *.json > emails.txt
```

- Unmount acounts folder

```
cd ..
```

Then add emails from emails.txt to Google Group, after that add this Google Group to your Shared Drive and promote it to manager and delete email.txt file from accounts folder

##### 2. Add Them To Team Drive Directly

- Run:

```
python3 add_to_team_drive.py -d SharedTeamDriveSrcID
```
    
</details>

## Environmental Variable

### REQUIRED VARIABLES

- `ROOT_FOLDER_ID` - Folder ID of your Shared Drive or Team Drive You Want to Index.

- `Not a variable but make sure either you added token.pickle or (service account in accounts/ folder)`

### OPTIONAL VARIABLES

- `IS_SERVICE_ACCOUNT` - `True/False` If you want to use mutiple service account, make sure u add all service accounts inside `accounts/` folder.

- `HOST` - Configure if you want to run on specified host (default 0.0.0.0).

- `PORT` - Configure if you want to run on specified port (default 5000).

# License
[![License](https://www.gnu.org/graphics/agplv3-155x51.png)](LICENSE)   
Google-Drive-Mirror is licensed under [GNU Affero General Public License](https://www.gnu.org/licenses/agpl-3.0.en.html) v3 or later.

# Credits
* [Me](https://github.com/kaif-00z)
* [MLTB Devs For Side Snippets](https://github.com/anasty17/mirror-leech-telegram-bot)

## Donate

- [Contact me on Telegram](t.me/kAiF_00z) if you would like to donate me for my work!
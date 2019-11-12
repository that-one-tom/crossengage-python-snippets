# crossengage-python-snippets
Re-usable Python scripts doing useful things with the various APIs of the CrossEngage CDP. The code provided is neither provided nor endorsed or supported by CrossEngage.

## Prerequisites
These scripts consume APIs of the [CrossEngage](https://www.crossengage.io/) CDP. You need to have an active account with this service and be in possesion of a valid master API key for this account.

The code was written and tested using Python 3.7.4. It utilises the excellent [Requests HTTP library](https://2.python-requests.org/en/master/) as well as [python-dotenv](https://github.com/theskumar/python-dotenv) to make managing environment variables easy.

## Installation
1. Clone the repository from GitHub using `git clone https://github.com/MutedJam/crossengage-python-snippets.git` and enter the newly created directory using `cd crossengage-python-snippets`
2. Install the requirements with `pip3 install -r requirements.txt`
3. Set the environment variables XNG_MASTER_API_KEY, XNG_APP_USER, XNG_APP_PASSWORD manually or configure them permantently in the `.env` file (see next section for an example)

## .env file
To avoid having keys and password available in your shell history, you can create a .env file in the script directory. It will be read when you run a script loading the respective values as environment variables:

```
XNG_MASTER_API_KEY="123abcdef456"
XNG_APP_USER="someone@crossengage.io"
XNG_APP_PASSWORD="topsecretpassword"
XNG_WEB_TRACKING_KEY="123abcdef456"
SENDGRID_API_KEY="SG.some.secretKeyForTheSendgridApi"
```

Not all variables are required for all scripts. Please see the below descriptions for a list of the variables used by each script.

## Available Scripts

### fetchMessageStatistcs.py
Generates a CSV file with yesterday's message statistics for campaigns in your account.

Requires environment variables `XNG_MASTER_API_KEY`, `XNG_APP_USER` and `XNG_APP_PASSWORD`.

Usage Example: `python3 fetchMessageStatistcs.py output.csv` where output.csv is the target file. Use the `-r` or `--reduced` option (e.g. `python3 fetchMessageStatistcs.py -r ~/test.csv)` to have each KPI in a separate column and thus only one row per message (instead of one row per KPI per message).

### optOutSendgridGlobalSuppressions.py
Fetches the _Global Unsubscribes_ from Sendgrid through the [respective API](https://sendgrid.com/docs/API_Reference/Web_API_v3/Suppression_Management/global_suppressions.html), then creates a segment in your CrossEngage account to identify CrossEngage users with matching email addresses and marks them as opted out of all CrossEngage communication. This avoids having CrossEngage send messages for these users to Sendgrid only for Sendgrid to drop them (which would not be reflected in the CrossEngage statistics).

The script only takes Sendgrid's _Global Unsubscribes_ but not _Unsubscribe Groups_ into account as there is no group-based opt-out management available in CrossEngage.

Requires environment variables `XNG_MASTER_API_KEY`, `XNG_APP_USER`, `XNG_APP_PASSWORD`, `XNG_WEB_TRACKING_KEY` and `SENDGRID_API_KEY`. The Sendgrid API key needs at least read access to Suppressions.

Usage Example: `python3 optOutSendgridGlobalSuppressions.py`
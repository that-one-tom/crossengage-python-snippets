# crossengage-python-snippets
Re-usable Python scripts doing useful things with the various APIs of the CrossEngage CDP. The code provided is neither provided nor endorsed or supported by CrossEngage.

## Prerequisites
These scripts consume APIs of the [CrossEngage](https://www.crossengage.io/) CDP. You need to have an active account with this service and be in possesion of a valid master API key for this account.

The code was written and tested using Python 3.7.4. It utilises the excellent [Requests HTTP library](https://2.python-requests.org/en/master/) as well as [python-dotenv](https://github.com/theskumar/python-dotenv) to make managing environment variables easy.

## Installation
1. Clone the repository from GitHub using `git clone https://github.com/MutedJam/crossengage-python-snippets.git` and enter the newly created directory using `cd crossengage-python-snippets`
2. Install the requirements with `pip install -r requirements.txt`
3. Set the environment variables XNG_MASTER_API_KEY, XNG_APP_USER, XNG_APP_PASSWORD manually or configure them permantently in the `.env` file (see next section for an example)

## .env file
To avoid having keys and password available in your shell history, you can create a .env file in the script directory. It will be read when you run a script loading the respective values as environment variables:

```
XNG_MASTER_API_KEY="123abcdef456"
XNG_APP_USER="someone@crossengage.io"
XNG_APP_PASSWORD="topsecretpassword"
```

## Available Scripts
### fetchMessageStatistcs.py
This script generates a CSV file with yesterday's message statistics for campaigns in your account.

Usage Example: `python3 fetchMessageStatistcs.py output.csv` where output.csv is the target file. Use the `-r` or `--reduced` option to have each KPI in a separate column and thus only one row per message (instead of one row per KPI per message).

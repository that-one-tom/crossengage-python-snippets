#!/usr/bin/env python3

import argparse, dotenv, os, datetime, traceback, sys, json, requests, csv

# Parsing command line arguments
argParser = argparse.ArgumentParser(description='Generates a CSV file with yesterday\'s message statistics for campaigns in your account')
argParser.add_argument('target', help='Write the result into csv file specified through this argument. Example: output.csv')
argParser.add_argument('-r', '--reduced', help='Use a more compact output format with only one row per campaign message and separate columns for each KPI', action='store_true')
args = argParser.parse_args()
TARGET_FILE = args.target
print('Target File:', TARGET_FILE)

# Load environment variables
dotenv.load_dotenv()
API_KEY = os.getenv('XNG_MASTER_API_KEY')
XNG_USER = os.getenv('XNG_APP_USER')
XNG_PASS = os.getenv('XNG_APP_PASSWORD')
print('API key (last 3 characters):', API_KEY[-3:])
print('Username:', XNG_USER)

# Configuration
TIMEOUT = 60
KPIS_TO_EXPORT = ['Sent', 'Delivered', 'Viewed', 'Clicked', 'Unique Viewed', 'Unique Clicked', 'Soft Bounced', 'Hard Bounced', 'Marked as Spam', 'Unsubscribed']
START_DATE = (datetime.datetime.now() - datetime.timedelta(1)).strftime('%Y-%m-%d')
END_DATE = (datetime.datetime.now() - datetime.timedelta(1)).strftime('%Y-%m-%d')
print('Fetching statistics from', START_DATE, 'to', END_DATE)

# Create re-usable session
session = requests.Session()
retries = requests.adapters.HTTPAdapter(max_retries=3)
session.mount('https://', retries)
API_BASE_URL = 'https://api.crossengage.io'
UI_BASE_URL = 'https://ui-api.crossengage.io/ui'

# Identify the company ID
companyIdurl = UI_BASE_URL + '/managers/companies'
companyIdPayload = {
    'email': XNG_USER
}
try:
    companyIdResponse = session.post(companyIdurl, data=json.dumps(companyIdPayload), timeout=TIMEOUT)
    if companyIdResponse.status_code == 200:
        companyIds = json.loads(companyIdResponse.text)
        if len(companyIds) != 1:
            raise ValueError('Unexpected number of company IDs returned: ' + companyIdResponse.text)
        else:
            companyId = companyIds[0]
            print('Found company ID', companyId)
    else:
        raise ValueError('Unexpected response code ' + str(companyIdResponse.status_code) + ' when fetching company ID')
except Exception:
    print('Fetching company ID failed')
    traceback.print_exc()
    sys.exit(1)

# Getting UI API token
uiTokenUrl = UI_BASE_URL + '/managers/login'
uiTokenPayload = {
    "email": XNG_USER,
    "password": XNG_PASS
}
uiTokenHeaders = {
    'content-type': 'application/json',
    'company-id': str(companyId)
}
try:
    uiTokenResponse = session.post(uiTokenUrl, data=json.dumps(uiTokenPayload), headers=uiTokenHeaders, timeout=TIMEOUT)
    if uiTokenResponse.status_code == 200:
        uiToken = json.loads(uiTokenResponse.text)['token']
        print('Retrieved UI token (last 5 characters):', uiToken[-5:])
    else:
        raise ValueError('Unexpected response code ' + str(uiTokenResponse.status_code) + ' when fetching UI token')
except Exception:
    print('Fetching UI token failed')
    traceback.print_exc()
    sys.exit(1)

# Defining Headers
API_HEADERS = {
    'Content-Type': 'application/json',
    'X-XNG-ApiVersion': str(2),
    'X-XNG-AuthToken': API_KEY
}
UI_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Company-ID': str(companyId),
    'X-XNG-ApiVersion': str(2),
    'Authorization': 'Bearer ' + uiToken

}

# Fetch KPI definitions
kpiDefinitionsUrl = API_BASE_URL + '/statistics/kpi'
try:
    metricsResponse = session.get(kpiDefinitionsUrl, headers=API_HEADERS, timeout=TIMEOUT)
    if metricsResponse.status_code == 200:
        kpiDefinitions = json.loads(metricsResponse.text)
        print('Retrieved KPI definitions')
    else:
        raise ValueError('Unexpected response code ' + str(metricsResponse.status_code) + ' when fetching KPI definitions')
except Exception:
    print('Fetching KPI definitions failed')
    traceback.print_exc()
    sys.exit(1)

# Fetch campaigns
campaignsUrl = UI_BASE_URL + '/campaigns'
try:
    campaignsResponse = session.get(campaignsUrl, headers=UI_HEADERS, timeout=TIMEOUT)
    if campaignsResponse.status_code == 200:
        campaigns = json.loads(campaignsResponse.text)
        print('Fetched', str(len(campaigns)), 'campaigns')
    else:
        raise ValueError('Unexpected response code ' + str(campaignsResponse.status_code) + ' when fetching campaigns')
except Exception:
    print('Fetching campaigns failed')
    traceback.print_exc()
    sys.exit(1)

# Fetch message statistics for each campaign and build list
results = []
for campaign in campaigns:
    print('Fetching statistics for campaign', campaign['id'])
    campaignStatisticsUrl = UI_BASE_URL + '/campaign/' + str(campaign['id']) + '/stats?startDate=' + START_DATE + 'T00:00:00.000Z&endDate=' + END_DATE + 'T23:59:59.999Z&groupBy=MESSAGE&interval=DAY'
    try:
        campaignStatisticsResponse = session.get(campaignStatisticsUrl, headers=UI_HEADERS, timeout=TIMEOUT)
        if campaignStatisticsResponse.status_code == 200:
            campaignStatistics = json.loads(campaignStatisticsResponse.text)
            print('Received statistics for campaign', campaign['id'])
            for day in campaignStatistics['history']:
                date = day[:10]
                for messageStatistic in campaignStatistics['history'][day]:
                    messageId = messageStatistic['id']
                    messageDetails = campaignStatistics['description'][messageId]
                    if args.reduced:
                        result = {
                            'Date': date,
                            'Campaign ID': campaign['id'],
                            'Campaign Name': campaign['name'],
                            'Message ID': messageId,
                            'Message Name': messageDetails['name'],
                            'Message Channel': messageDetails['channelType']
                        }
                        for kpiId in messageStatistic['values']:
                            value = messageStatistic['values'][kpiId]
                            if len([kpi for kpi in kpiDefinitions if str(kpi['id']) == kpiId]) == 1: # Check if the ID belongs to a defined KPI
                                currentKpi = [kpi for kpi in kpiDefinitions if str(kpi['id']) == kpiId][0]
                                if currentKpi['name'] in KPIS_TO_EXPORT: # Check if the KPI is one of the KPIs we want to export
                                    result[currentKpi['name']] = value
                        results.append(result)
                    else:
                        for kpiId in messageStatistic['values']:
                            value = messageStatistic['values'][kpiId]
                            if len([kpi for kpi in kpiDefinitions if str(kpi['id']) == kpiId]) == 1: # Check if the ID belongs to a defined KPI
                                currentKpi = [kpi for kpi in kpiDefinitions if str(kpi['id']) == kpiId][0]
                                if currentKpi['name'] in KPIS_TO_EXPORT: # Check if the KPI is one of the KPIs we want to export
                                    result = {
                                        'Date': date,
                                        'Campaign ID': campaign['id'],
                                        'Campaign Name': campaign['name'],
                                        'Message ID': messageId,
                                        'Message Name': messageDetails['name'],
                                        'Message Channel': messageDetails['channelType'],
                                        'KPI': currentKpi['name'],
                                        'Value': value
                                    }
                                    results.append(result)
        else:
            raise ValueError('Unexpected response code ' + str(campaignStatisticsResponse.status_code) + ' when fetching campaign statistics')
    except Exception:
        print('Fetching campaign statistics failed')
        traceback.print_exc()
        sys.exit(1)

# Now write everything into a csv file
print('Writing statistics to file')
with open(TARGET_FILE, 'w+', newline='', encoding='utf-8') as csvfile:
    fields = ['Date', 'Campaign ID', 'Campaign Name', 'Message ID', 'Message Name', 'Message Channel']
    if args.reduced:
        fields.extend(KPIS_TO_EXPORT)
    else:
        fields.extend(['KPI', 'Value'])
    writer = csv.DictWriter(csvfile, fieldnames=fields)
    writer.writeheader()
    for result in results:
        writer.writerow(result)
print('Finished')

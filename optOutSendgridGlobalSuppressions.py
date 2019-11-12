#!/usr/bin/env python3

import dotenv, os, datetime, time, traceback, sys, json, requests, uuid

# Load environment variables
dotenv.load_dotenv()
API_KEY = os.getenv('XNG_MASTER_API_KEY')
XNG_USER = os.getenv('XNG_APP_USER')
XNG_PASS = os.getenv('XNG_APP_PASSWORD')
WEB_TRACKING_KEY = os.getenv('XNG_WEB_TRACKING_KEY')
SG_KEY = os.getenv('SENDGRID_API_KEY')
print('CrossEngage API key (last 3 characters):', API_KEY[-3:])
print('CrossEngage User:', XNG_USER)
print('Sendgrid API Key (last 3 characters):', SG_KEY[-3:])

# Configuration
TIMEOUT = 60
MAX_USERS_PER_SEGMENT = 100

# Create re-usable session
session = requests.Session()
retries = requests.adapters.HTTPAdapter(max_retries=3)
session.mount('https://', retries)
API_BASE_URL = 'https://api.crossengage.io'
UI_BASE_URL = 'https://ui-api.crossengage.io/ui'
SENDGRID_API_BASE_URL = 'https://api.sendgrid.com/v3'

# Sendgrid API Headers
SENDGRID_API_HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + SG_KEY
}

# Fetch global unsubscribes (paginated, Sendgrid only provides a maximum of 500 entries per request)
SENDGRID_UNSUBSCRIBES = []
globalUnsubscribesUrl = SENDGRID_API_BASE_URL + '/suppression/unsubscribes?limit=500&offset=0'
moreUnsubscribes = True
while moreUnsubscribes == True:
    try:
        globalUnsubscribesResponse = session.get(globalUnsubscribesUrl, headers=SENDGRID_API_HEADERS, timeout=TIMEOUT)
        if globalUnsubscribesResponse.status_code == 200:
            globalUnsubscribes = json.loads(globalUnsubscribesResponse.text)
            for globalUnsubscribe in globalUnsubscribes:
                SENDGRID_UNSUBSCRIBES.append(globalUnsubscribe['email'])
            print('Retrieved', len(globalUnsubscribes), 'global unsubscribes from Sendgrid')
            if globalUnsubscribesResponse.links['next'] and globalUnsubscribesResponse.links['next']['url'] and globalUnsubscribesUrl != globalUnsubscribesResponse.links['next']['url']:
                globalUnsubscribesUrl = globalUnsubscribesResponse.links['next']['url']
                moreUnsubscribes = True
            else:
                moreUnsubscribes = False
                break
        else:
            raise ValueError('Unexpected response code ' + str(globalUnsubscribesResponse.status_code) + ' when fetching global unsubscribes')
    except Exception:
        print('Fetching global unsubscribes failed')
        traceback.print_exc()
        sys.exit(1)
print('Fetched a toal of', len(SENDGRID_UNSUBSCRIBES),'global unsubscribes from Sendgrid')
SENDGRID_UNSUBSCRIBES = list(set(SENDGRID_UNSUBSCRIBES))
print(len(SENDGRID_UNSUBSCRIBES),'unsubscribes remaining after deduplication')

# Identify the CrossEngage Company ID
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
            print('Found CrossEngage Company ID', companyId)
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
        print('Retrieved UI token (last 5 characters):', uiToken[-3:])
    else:
        raise ValueError('Unexpected response code ' + str(uiTokenResponse.status_code) + ' when fetching UI token')
except Exception:
    print('Fetching UI token failed')
    traceback.print_exc()
    sys.exit(1)

# Define CrossEngage Headers
API_HEADERS = {
    'Content-Type': 'application/json',
    'X-XNG-ApiVersion': str(1),
    'X-XNG-AuthToken': API_KEY
}
UI_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Company-ID': str(companyId),
    'X-XNG-ApiVersion': str(2),
    'Authorization': 'Bearer ' + uiToken
}

### Identify the correct attribute ID for traits.email (this is required for the segment creation)
print('Searching attribute ID for traits.email')
getAttributesUrl = UI_BASE_URL + '/campaigns/event-classes'
getAttributesResponse = session.get(getAttributesUrl, headers=UI_HEADERS, timeout=TIMEOUT)
try:
    if getAttributesResponse.status_code == 200:
        attributeDetails = json.loads(getAttributesResponse.text)
        print('Retrieved attribute details')
    else:
        raise ValueError('Unexpected response code ' + str(getAttributesResponse.status_code) + ' when fetching attribute details')
except Exception:
    print('Fetching attributes failed')
    traceback.print_exc()
    sys.exit(1)
try:
    properties = attributeDetails['properties']
except:
    print('Fetching attribute details failed')
    traceback.print_exc()
    sys.exit(1)
ID_EMAIL_ATTRIBUTE = None
for propertyDetail in properties:
	if propertyDetail['label'] == 'traits.email':
		ID_EMAIL_ATTRIBUTE = propertyDetail['id']
		print('Identified ID of traits.email: ' + str(propertyDetail['id']))
if not ID_EMAIL_ATTRIBUTE:
    print('Could not find ID of traits.email')
    sys.exit(1)

### Build segments
SENDGRID_UNSUBSCRIBE_CHUNKS = [SENDGRID_UNSUBSCRIBES[x:x+MAX_USERS_PER_SEGMENT] for x in range(0, len(SENDGRID_UNSUBSCRIBES), MAX_USERS_PER_SEGMENT)]
for i, UNSUBSCRIBE_CHUNK in enumerate(SENDGRID_UNSUBSCRIBE_CHUNKS):
    SEGMENT_NAME = '[Sendgrid Opt-Out Sync] ' + str(uuid.uuid4())[:8]
    print('Creating segment',i+1,'of',len(SENDGRID_UNSUBSCRIBE_CHUNKS),'as',SEGMENT_NAME,'with',len(UNSUBSCRIBE_CHUNK),'emails')
    SEGMENT_PAYLOAD = {
        'label': SEGMENT_NAME,
        'type': 'CONTAINER',
        'operator': 'OR',
        'subFilters': [],
        'justCreated': False,
        '$$hashKey': 'object:1340'
    }
    for EMAIL in UNSUBSCRIBE_CHUNK:
        SUBFILTER = {
            'type': 'ATTRIBUTE',
            'label': '_gen:_' + str(time.time_ns()),
            'operator': None,
            'justCreated': False,
            'subFilters': [],
            'conditions': [{
                'values': [EMAIL],
                'conditions': [{
                    'values': [''],
                    '$$hashKey': 'object:1874'
                }],
                'valueIdList': [0],
                'attributeId': ID_EMAIL_ATTRIBUTE,
                'operator': '=='
            }],
            'id': None
        }
        SEGMENT_PAYLOAD['subFilters'].append(SUBFILTER)
    createSegmentUrl = UI_BASE_URL + '/campaigns/filters'
    createSegmentResponse = session.post(createSegmentUrl, data=json.dumps(SEGMENT_PAYLOAD), headers=UI_HEADERS, timeout=TIMEOUT)
    try:
        if createSegmentResponse.status_code == 200:
            newSegment = json.loads(createSegmentResponse.text)
            print('New segment created with ID', newSegment['id'])
        else:
            raise ValueError('Unexpected response code ' + str(createSegmentResponse.status_code) + ' creating segment')
    except Exception:
        print('Creating segment failed')
        traceback.print_exc()
        sys.exit(1)

    #### Trigger user count to populate segment
    print('Trigger user count for segment with ID ' + str(newSegment['id']))
    refreshSegmentUrl = UI_BASE_URL + '/filters/' + str(newSegment['id']) + '/count'
    refreshSegmentResponse = session.get(refreshSegmentUrl, headers=UI_HEADERS, timeout=TIMEOUT)
    try:
        if refreshSegmentResponse.status_code == 200:
            refreshResult = json.loads(refreshSegmentResponse.text)
            print('User Count:', refreshResult['total'])
        else:
            raise ValueError('Unexpected response code ' + str(createSegmentResponse.status_code) + ' for user count')
    except Exception:
        print('User count failed')
        traceback.print_exc()
        sys.exit(1)

    #### Fetch users in segment
    print('Retrieving users in segment with ID', str(newSegment['id']))
    fetchSegmentUrl = UI_BASE_URL + '/userexplorer/' + str(newSegment['id']) + '?offset=0&limit=' + str(MAX_USERS_PER_SEGMENT)
    fetchNewSegmentResponse = session.get(fetchSegmentUrl, headers=UI_HEADERS, timeout=TIMEOUT)
    try:
        if fetchNewSegmentResponse.status_code == 200:
            fetchNewSegmentResult = json.loads(fetchNewSegmentResponse.text)
            newSegmentPart = fetchNewSegmentResult['part']
        else:
            raise ValueError('Unexpected response code ' + str(fetchNewSegmentResponse.status_code) + ' when fetching segment users')
    except Exception:
        print('Fetching segment users failed')
        traceback.print_exc()
        sys.exit(1)

    #### Check opt-out status for each user in segment and opt out if required
    for xngUser in newSegmentPart:
        if xngUser['externalId']:
            print('Fetching opt out status for user with xngGlobalUserId', xngUser['xngGlobalUserId'], 'and email', xngUser['email'])
            optOutStatusUrl = API_BASE_URL + '/users/' + xngUser['externalId'] + '/recipient-status'
            optOutStatusResponse = session.get(optOutStatusUrl, headers=API_HEADERS, timeout=TIMEOUT)
            try:
                if optOutStatusResponse.status_code == 200:
                    optOutStatusResult = json.loads(optOutStatusResponse.text)
                    optedOut = optOutStatusResult['optOutAll']
                else:
                    raise ValueError('Unexpected response code ' + str(optOutStatusResponse.status_code) + ' when fetching opt out status')
            except Exception:
                print('Fetching opt out status failed')
                traceback.print_exc()
                sys.exit(1)
            if optedOut == True:
                print('User with xngGlobalUserId', xngUser['xngGlobalUserId'], 'and email', xngUser['email'], 'is already opted out')
            else:
                print('Opting out user with xngGlobalUserId', xngUser['xngGlobalUserId'], 'and email', xngUser['email'])
                optOutUrl = API_BASE_URL + '/users/' + xngUser['externalId'] + '/optout-status'
                optOutPayload = {
                    'optOut': True
                }
                optOutResponse = session.put(optOutUrl, data=json.dumps(optOutPayload), headers=API_HEADERS, timeout=TIMEOUT)
                try:
                    if optOutResponse.status_code == 200:
                        optOutResult = json.loads(optOutResponse.text)
                        newOptOutStatus = optOutResult['optOut']
                        if newOptOutStatus != True:
                            raise ValueError('Unexpected opt out status after update: ' + str(newOptOutStatus))
                    else:
                        raise ValueError('Unexpected response code ' + str(optOutStatusResponse.status_code) + ' when opting out')
                except Exception:
                    print('Opting out failed')
                    traceback.print_exc()
                    sys.exit(1)
                print('User with xngGlobalUserId', xngUser['xngGlobalUserId'], 'and email', xngUser['email'], 'opted out successfully')
        else:
            print('No external ID found for user with xngGlobalUserId', xngUser['xngGlobalUserId'], 'and email', xngUser['email'])
            print('Attempting to opt out user through opt out link workaround')
            optOutLinkUrl = 'https://trk-api.crossengage.io/optout/inbound/webhook/' + WEB_TRACKING_KEY + '/' + xngUser['xngGlobalUserId'] + '?channelType=all'
            optOutLinkResponse = session.get(optOutLinkUrl, timeout=TIMEOUT)
            try:
                if optOutLinkResponse.status_code == 200:
                    print('User with xngGlobalUserId', xngUser['xngGlobalUserId'], 'and email', xngUser['email'], 'was opted out successfully through opt out link method (Response:', optOutLinkResponse.text.replace('\n', ' ').replace('\r', ''), ')')
                else:
                    raise ValueError('Unexpected response code ' + str(fetchNewSegmentResponse.status_code) + ' when using opt out link workaround')
            except Exception:
                print('Opt out link workaround failed')
                traceback.print_exc()
                sys.exit(1)

    #### Our work is done, now deleting segment
    print('Deleting segment with ID ' + str(newSegment['id']))
    deleteSegmentUrl = UI_BASE_URL + '/filters/' + str(newSegment['id'])
    deleteSegmentResponse = session.delete(deleteSegmentUrl, headers=UI_HEADERS, timeout=TIMEOUT)
    try:
        if deleteSegmentResponse.status_code == 204:
            print('Segment with ID', newSegment['id'], 'deleted')
        else:
            raise ValueError('Unexpected response code ' + str(createSegmentResponse.status_code) + ' for segment deletion')
    except Exception:
        print('Segment deletion')
        traceback.print_exc()
        sys.exit(1)

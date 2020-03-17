import requests
import os
import time
import logging
import sys
import json

# vars and configs
bearertoken = ""
vropsUser = "admin"
vropsPassword = "VMware1!"
vropsHost = "field-weekly.cmbu.local"
vropsAuthsource = "Local"
teamId = "52737"

verify = False
if not verify:
    requests.packages.urllib3.disable_warnings()

def vropsGetToken(user=vropsUser, passwd=vropsPassword, authSource=vropsAuthsource, host=vropsHost):
    if not bearertoken:
        url = "https://" + host + "/suite-api/api/auth/token/acquire"
        payload = "{\r\n  \"username\" : \"" + user + "\",\r\n  \"authSource\" : \"" + authSource + "\",\r\n  \"password\" : \"" + passwd + "\",\r\n  \"others\" : [ ],\r\n  \"otherAttributes\" : {\r\n  }\r\n}"
        headers = {
            'accept': "application/json",
            'content-type': "application/json",
            }
        response = requests.request("POST", url, data=payload, headers=headers, verify=verify)
        return response.text
    elif int(bearertoken["validity"])/1000 < time.time():
        url = "https://" + host + "/suite-api/api/versions"
        headers = {
            'authorization': "vRealizeOpsToken " + bearertoken["token"],
            'accept': "application/json"
        }
        response = requests.request("GET", url, headers=headers, verify=verify)
        if response.status_code == 401:
            url = "https://" + host + "/suite-api/api/auth/token/acquire"
            payload = "{\r\n  \"username\" : \"" + vropsUser + "\",\r\n  \"authSource\" : \"" + vropsAuthsource + "\",\r\n  \"password\" : \"" + vropsPassword + "\",\r\n  \"others\" : [ ],\r\n  \"otherAttributes\" : {\r\n  }\r\n}"
            headers = {
            'accept': "application/json",
            'content-type': "application/json",
            }
            response = requests.request("POST", url, data=payload, headers=headers, verify=verify)
            return response.text
        else:
            return json.dumps(bearertoken)
    else:
        return json.dumps(bearertoken)

def vropsRequest(request,method,querystring="",payload=""):
    global bearertoken
    bearertoken = json.loads(vropsGetToken())
    url = "https://" + vropsHost + "/suite-api/" + request
    querystring = querystring
    headers = {
        'authorization': "vRealizeOpsToken " + bearertoken["token"],
        'accept': "application/json",
        'content-type': "application/json"
    }
    if (querystring != "") and (payload != ""):
        response = requests.request(method, url, headers=headers, params=querystring, json=payload, verify=verify)
    elif (querystring != ""):
        response = requests.request(method, url, headers=headers, params=querystring, verify=verify)
    elif (payload != ""):
        response = requests.request(method, url, headers=headers, json=payload, verify=verify)
    else:
        response = requests.request(method, url, headers=headers, verify=verify)

    print ("Request " + response.url + " returned status " + str(response.status_code))
    return response.json()

def foldRequest(request,method,querystring="",payload=""):
    url = "https://stats.foldingathome.org/api/" + request
    headers = {
        'content-type' : "application/json"
    }
    retry = True
    while retry:
        response = requests.request(method, url, headers=headers)
        print ("Request " + response.url + " returned status " + str(response.status_code))
        if response.status_code == 200:
            return response.json()

teamStats = foldRequest("team/"+teamId,"GET")
# Load team objects
payload = {
    'description' : 'Folding@Home Team',
    'resourceKey' : {
        'name' : teamStats['name'],
        'adapterKindKey' : 'FoldingAtHome',
        'resourceKindKey' : 'Folding Team'
    },
     'resourceIdentifiers' : [
        {
            'identifierType' : {
                'name' : 'teamId',
                'dataType' : 'STRING',
                'isPartOfUniqueness' : True
            },
            'value' : teamStats['team']
        }
     ]
}

response = vropsRequest("/api/resources/adapterkinds/httpPost","POST","",payload)

# Push team status
timestamp = long(time.time() * 1000)
payload = {
  "stat-content" : [ {
    "statKey" : "WUs",
    "timestamps" : [ timestamp ],
    "data" : [ teamStats['wus'] ]
  },{
    "statKey" : "rank",
    "timestamps" : [ timestamp ],
    "data" : [ teamStats['rank'] ]
   },{
    "statKey" : "active_50"
    "timestamps" : [timestamp],
    "data" : [ teamStats['active_50'] ]
   },{
    "statKey" : "credit",
    "timestamps" : [timestamp],
    "data" : [ teamStats['credit'] ]
   } ]
}

resourceId = response["identifier"]

response = vropsRequest("/api/resources/"+resourceId+"/stats","POST","",payload)

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
    if response.text:
        return response.json()


def foldRequest(request,method,querystring="",payload=""):
    url = "https://stats.foldingathome.org/api/" + request
    headers = {
        'content-type' : "application/json"
    }
    retry = True
    while retry:
        response = requests.request(method, url, headers=headers)
        #print ("Request " + response.url + " returned status " + str(response.status_code))
        if response.status_code == 200:
            return response.json()


teamStats = foldRequest("team/"+teamId,"GET")
#Uncomment to use sample file
#with open ('StatsSample.json') as f:
#    teamStats = json.load(f)

# Load team objects
# First find if the team has been added to vROps
vropsObjects = vropsRequest("api/resources","GET","adapterKind=FoldingAtHome")
teams = vropsObjects["resourceList"]
teamRes = ""
for team in teams:
    if team["resourceKey"]["name"] == teamStats['name']:
        teamRes = team
        break

# If no team found create it
if teamRes == "":
    payload = {
    'description' : 'Folding@Home Team',
    'resourceKey' : {
        'name' : teamStats['name'],
        'adapterKindKey' : 'FoldingAtHome',
        'resourceKindKey' : 'Folding Team'
        }
    }
    teamRes = vropsRequest("api/resources/adapterkinds/foldingathome","POST","",payload)

# Push team stats
timestamp = time.time()
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
    "statKey" : "active_50",
    "timestamps" : [timestamp],
    "data" : [ teamStats['active_50'] ]
   },{
    "statKey" : "credit",
    "timestamps" : [timestamp],
    "data" : [ teamStats['credit'] ]
   },{
     "statKey" : "id",
     "timestamps" : [ timestamp ],
     "data" : [ teamStats['team'] ]
    } ]
}

resourceId = teamRes["identifier"]

response = vropsRequest("api/resources/"+resourceId+"/stats","POST","",payload)

# Add and update team members
teamChildren = []
donorsList = teamStats["donors"]
for donor in donorsList:
    fahObjs = vropsObjects["resourceList"]
    donorRes = ""
    for fahObj in fahObjs:
        if fahObj["resourceKey"]["name"] == donor['name']:
            donorRes = fahObj
            break

    # If no team found create it
    if donorRes == "":
        payload = {
        'description' : 'Folding@Home Donor',
        'resourceKey' : {
            'name' : donor['name'],
            'adapterKindKey' : 'FoldingAtHome',
            'resourceKindKey' : 'Folding Donor'
            }
        }
        donorRes = vropsRequest("api/resources/adapterkinds/foldingathome","POST","",payload)
        #add to list of children to be added to teams
        teamChildren.append(donorRes["identifier"])
        print(teamChildren)
     # Push donor stats; new donors are unranked so this has to be dealt with
    donorRank = 0
    if 'rank' in donor:
        donorRank = donor['rank']
    payload = {
    "stat-content" : [ {
     "statKey" : "WUs",
     "timestamps" : [ timestamp ],
     "data" : [ donor['wus'] ]
    },{
     "statKey" : "rank",
     "timestamps" : [ timestamp ],
     "data" : [ donorRank ]
    },{
     "statKey" : "credit",
     "timestamps" : [timestamp],
     "data" : [ donor['credit'] ]
    },{
     "statKey" : "id",
     "timestamps" : [ timestamp ],
     "data" : [ donor['id'] ]
    } ]
    }

    resourceId = donorRes["identifier"]

    response = vropsRequest("api/resources/"+resourceId+"/stats","POST","",payload)

payload = {"uuids" : teamChildren}
response = vropsRequest("api/resources/"+teamRes["identifier"]+"/relationships/CHILD","POST","",payload)

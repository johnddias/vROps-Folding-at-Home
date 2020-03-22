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
    elif int(bearertoken["validity"])/1000 < int(round(time.time()*1000)):
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

def vropsRequest(request,method,querystring="",payload="",log=True):
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
    if log == True:
        print ("Request " + response.url + " returned status " + str(response.status_code))
    if response.text:
        return response.json()

def foldRequest(request,method,querystring="",payload=""):
    url = "https://api.foldingathome.org" + request
    headers = {
        'content-type' : "application/json"
    }
    retry = True
    tryCount = 0
    while retry:
        response = requests.request(method, url, headers=headers)
        #print ("Request " + response.url + " returned status " + str(response.status_code))
        if response.status_code == 200:
            return response.json()
        else:
            if tryCount > 15:
                retry = False
            else:
                tryCount += 1
                time.sleep(5)

teamStats = foldRequest("/team/"+teamId,"GET")

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
    teamRes = vropsRequest("api/resources/adapterkinds/foldingathome","POST","",payload,False)

# Push team stats
timestamp = int(round(time.time()*1000))
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
    "data" : [ teamStats['score'] ]
   },{
     "statKey" : "id",
     "timestamps" : [ timestamp ],
     "data" : [ teamStats['id'] ]
    } ]
}

resourceId = teamRes["identifier"]

response = vropsRequest("api/resources/"+resourceId+"/stats","POST","",payload,False)

# Add and update team members
memberStats = foldRequest("/team/"+teamId+"/members","GET")
del memberStats[0]
teamChildren = []
resourcestatcontent = []
for member in memberStats:
    fahObjs = vropsObjects["resourceList"]
    memberRes = ""
    for fahObj in fahObjs:
        if fahObj["resourceKey"]["name"] == str(member[0]):
            memberRes = fahObj
            break

    # If no member found create it
    if memberRes == "":
        memberName = ""
        if len(member[0]) == 0:
            print("Invalid name " + member[0] + ", skipping.")
            break
        else:
            memberName = member[0]
        payload = {
        'description' : 'Folding@Home Member',
        'resourceKey' : {
            'name' : memberName,
            'adapterKindKey' : 'FoldingAtHome',
            'resourceKindKey' : 'Folding Donor'
            }
        }
        print("Adding member " + memberName)
        memberRes = vropsRequest("api/resources/adapterkinds/foldingathome","POST","",payload,False)
        #add to list of children to be added to teams
        teamChildren.append(memberRes["identifier"])
     # Push member stats; new members are unranked so this has to be dealt with
    resourceId = memberRes["identifier"]
    memberRank = member[2]
    memberWUs = member[4]
    memberCredit = member[3]
    memberStat = {"id" : resourceId,
     "stat-contents" : [ {
         "statKey" : "WUs",
         "timestamps" : [ timestamp ],
         "data" : [ member[4] ]
        },{
         "statKey" : "rank",
         "timestamps" : [ timestamp ],
         "data" : [ member[2] ]
        },{
         "statKey" : "credit",
         "timestamps" : [timestamp],
         "data" : [ member[3] ]
        },{
         "statKey" : "id",
         "timestamps" : [ timestamp ],
         "data" : [ member[1] ]
        } ]
    }
    resourcestatcontent.append(memberStat)

payload = { "resource-stat-content" : resourcestatcontent }
response = vropsRequest("api/resources/stats","POST","",payload)

if teamChildren:
    payload = {"uuids" : teamChildren}
    response = vropsRequest("api/resources/"+teamRes["identifier"]+"/relationships/CHILD","POST","",payload)

#!/usr/bin/env python3
# A web server to echo back a request's headers and data.
#
# Usage: ./webserver
#        ./webserver 0.0.0.0:5000

from http.server import HTTPServer, BaseHTTPRequestHandler
from sys import argv
import json

BIND_HOST = 'localhost'
PORT = 8008

discovery_response = json.dumps({
    "name": "This is a local test service",
    "description": "This local test service does nothing, just logs out the requests.",
    "url": "https://website.com/more-information", # URL to more information about the application, or the application home page
    "version": "1.0.0",
    "endpoints": { # If not present, defaults to all endpoints enabled. If present, only data for listed endpoints should be sent
        "activities":
        {
            "min_period": 60 # Minimum number of seconds between requests. There will also be a hard minimum applied client-side (so values lower than that will be ignored). If omitted, use client default.
        },
        "events":
        {
            "min_period": 15, # Minimum number of seconds between requests. There will also be a hard minimum applied client-side (so values lower than that will be ignored). If omitted, use client default.
            "max_batch": 10 # Maximum number of events to include in a single request. Any remaining events will be sent in the next request. If omitted, use client default.
        }
    },
    "events": # If not present, accept default set of events. If present, only listed events should be sent to API (with optional further filtering).
    {
        "ApproachSettlement":
        {
            # Can be an empty object, in which case all occurrences of this event are sent
        },
        "CollectCargo":
        {
            "filters":
            {
                "Type": "$UnknownArtifact2_name;"
            }
        },
        "Died":
        {
            "filters":
            {
                "KillerShip": "scout_hq|scout_nq|scout_q|scout|thargonswarm|thargon"
            }
        },
        "FactionKillBond":
        {
            "filters":
            {
                "AwardingFaction": "^\\$faction_PilotsFederation;$",
                "VictimFaction": "^\\$faction_Thargoid;$"
            }
        },
        "FSDJump": {},
        "Location": {},
        "MissionAccepted": {},
        "MissionCompleted": {},
        "MissionFailed": {},
        "StartUp": {}
    }
}).encode('utf-8')

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith("/discovery"):
            self.write_response(discovery_response)
        else:
            self.write_response(b'')

    def do_POST(self):
        content_length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(content_length)

        self.write_response(body)

    def do_PUT(self):
        content_length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(content_length)

        self.write_response(body)

    def write_response(self, content):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(content)

        print(self.headers)
        print(content.decode('utf-8'))

if len(argv) > 1:
    arg = argv[1].split(':')
    BIND_HOST = arg[0]
    PORT = int(arg[1])

print(f'Listening on http://{BIND_HOST}:{PORT}\n')

httpd = HTTPServer((BIND_HOST, PORT), SimpleHTTPRequestHandler)
httpd.serve_forever()




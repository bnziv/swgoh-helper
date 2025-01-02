import os
from datetime import datetime
import requests
import time
from swgoh_comlink import SwgohComlink
from backend.queries import Queries
queries = Queries()

def log(message):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

from backend.database import Database
from backend.fleetpayout import FleetPayout
from backend.dataloader import DataLoader
from backend.roster import Roster

COMLINK_URL = os.getenv('COMLINK_URL')

def comlink_ready():
    try:
        requests.get(COMLINK_URL)
        log("Connected to Comlink")
        return True
    except:
        log("Error connecting to Comlink")
        return False

db = Database()
while not comlink_ready():
    time.sleep(2)
comlink = SwgohComlink(COMLINK_URL)
dataloader = DataLoader(db, comlink)
fleetpayout = FleetPayout(db, comlink)
roster = Roster(db, comlink)
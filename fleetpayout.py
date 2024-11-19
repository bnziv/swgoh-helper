from swgoh_comlink import SwgohComlink
from database import Database

class FleetPayout:
    def __init__(self, database: Database, comlink: SwgohComlink):
        self.db = database
        self.connection = self.db.connection
        self.cursor = self.db.cursor
        self.comlink = comlink
    
    def add_player(self, allycode):
        result = self.comlink.get_player_arena(allycode=allycode, player_details_only=True)
        name = result['name']
        offset = result['localTimeZoneOffsetMinutes']
        query = '''
        INSERT INTO fleet_shard_players (allycode, name, time_offset) VALUES (%s, %s, %s)
        ON CONFLICT (allycode) DO UPDATE SET
        name = excluded.name,
        time_offset = excluded.time_offset;
        '''
        self.db.cursor.execute(query, (allycode, name, offset))
        self.db.connection.commit()
    
    def get_payout(self, allycode = None, name = None):
        if not allycode and not name:
            return
        if allycode:
            query = '''
            SELECT payout FROM fleet_shard_players WHERE allycode = %s
            '''
            params = (allycode,)
        else:
            query = '''
            SELECT payout FROM fleet_shard_players WHERE name ILIKE %s
            '''
            params = (f"%{name}%",)
        self.db.cursor.execute(query, params)
        result = self.db.cursor.fetchall()
        return result
    
    def get_all_payouts(self, allycode):
        query = '''
        SELECT name, payout FROM fleet_shard WHERE allycode = %s
        '''
        self.db.cursor.execute(query, (allycode,))
        result = self.db.cursor.fetchall()
        return result
    
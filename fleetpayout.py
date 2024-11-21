from swgoh_comlink import SwgohComlink
from database import Database

class FleetPayout:
    def __init__(self, database: Database, comlink: SwgohComlink):
        self.db = database
        self.connection = self.db.connection
        self.cursor = self.db.cursor
        self.comlink = comlink
    
    def add_player(self, allycode, name, offset, owner):
        query = '''
        INSERT INTO fleet_shard_players (allycode, name, time_offset, part_of) VALUES (%s, %s, %s, %s)
        ON CONFLICT (allycode) DO UPDATE SET
        name = excluded.name,
        time_offset = excluded.time_offset,
        part_of = excluded.part_of;
        '''
        self.db.cursor.execute(query, (allycode, name, offset, owner))
        self.db.connection.commit()
    
    def get_payout(self, allycode = None, name = None):
        if not allycode and not name:
            return
        if allycode:
            query = '''
            SELECT time_offset FROM fleet_shard_players WHERE allycode = %s
            '''
            params = (allycode,)
        else:
            query = '''
            SELECT allycode, name, time_offset FROM fleet_shard_players WHERE name ILIKE %s
            '''
            params = (f"%{name}%",)
        self.db.cursor.execute(query, params)
        result = self.db.cursor.fetchall()
        return result
    
    def get_all_payouts(self):
        query = '''
        SELECT allycode, name, time_offset FROM fleet_shard_players
        '''
        self.db.cursor.execute(query)
        result = self.db.cursor.fetchall()
        return result
    
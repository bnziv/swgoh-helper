from swgoh_comlink import SwgohComlink
from backend.database import Database

class FleetPayout:
    def __init__(self, database: Database, comlink: SwgohComlink):
        self.db = database
        self.comlink = comlink
    
    async def add_player(self, allycode, name, offset, owner):
        query = '''
        INSERT INTO fleet_shard_players (allycode, name, time_offset, part_of) VALUES ($1, $2, $3, $4)
        ON CONFLICT (allycode) DO UPDATE SET
        name = excluded.name,
        time_offset = excluded.time_offset,
        part_of = excluded.part_of;
        '''
        await self.db.execute(query, allycode, name, offset, owner)

    async def remove_player(self, allycode):
        query = '''
        DELETE FROM fleet_shard_players WHERE allycode = $1
        '''
        result = await self.db.execute(query, allycode)
        if result == "DELETE 0":
            return False
        return True

    
    async def get_payout(self, allycode = None, name = None):
        if not allycode and not name:
            return
        if allycode:
            query = '''
            SELECT time_offset FROM fleet_shard_players WHERE allycode = $1
            '''
            params = allycode
        else:
            query = '''
            SELECT allycode, name, time_offset FROM fleet_shard_players WHERE name ILIKE $1
            '''
            params = f"%{name}%"
        result = await self.db.fetch(query, params)
        return result
    
    async def get_all_payouts(self):
        query = '''
        SELECT allycode, name, time_offset FROM fleet_shard_players
        '''
        result = await self.db.fetch(query)
        return result
    
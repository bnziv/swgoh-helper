from database import Database
from swgoh_comlink import SwgohComlink

class DataLoader:
    def __init__(self, database: Database, comlink: SwgohComlink):
        self.db = database
        self.connection = self.db.connection
        self.cursor = self.db.cursor
        self.comlink = comlink
    
    def checkVersion(self):
        version = self.comlink.get_latest_game_data_version()['game']
        query = '''
        INSERT INTO game_version (version) VALUES (%s)
        ON CONFLICT (version) DO NOTHING;'''
        self.cursor.execute(query, (version,))
        query = '''
        SELECT version FROM game_version ORDER BY timestamp DESC LIMIT 1
        '''
        self.cursor.execute(query)
        result = self.db.cursor.fetchone()[0]
        self.connection.commit()
        if result == version:
            return True
        else:
            return False
        
    def get_localization(self):
        data = self.comlink.get_localization(locale="ENG_US", unzip=True, enums=True)['Loc_ENG_US.txt']
        lines = data.strip().split('\n')
        localization = {}
        for line in lines:
            if line.startswith('#'):
                continue
            key, value = line.split('|', 1)
            localization[key.strip()] = value.strip()
        return localization
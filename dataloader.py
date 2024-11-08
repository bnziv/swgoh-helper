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

    def load_data(self):
        gameData = self.comlink.get_game_data()
        localization = self.get_localization()
        self.load_units(gameData['units'], localization)
        self.load_tags(gameData['category'], localization)

    def load_units(self, units, localization):
        for unit in units:
            if unit['obtainableTime'] == '0':
                baseId = unit['baseId']
                name = localization[unit['nameKey']]
                desc = localization[unit['descKey']]
                query = '''
                INSERT INTO units (baseId, name, description) VALUES (%s, %s, %s)
                ON CONFLICT (baseId) DO UPDATE SET
                name = excluded.name,
                description = excluded.description;
                '''
                self.cursor.execute(query, (baseId, name, desc))
                self.connection.commit()

    def load_tags(self, tags, localization):
        for tag in tags:
            if (tag['visible']):
                id = tag['id']
                name = localization[tag['descKey']]
                query = '''
                INSERT INTO tags (id, name) VALUES (%s, %s)
                ON CONFLICT (id) DO UPDATE SET
                name = excluded.name;
                '''
                self.cursor.execute(query, (id, name))
                self.connection.commit()

    def load_unit_tags(self, units):
        query = '''
        INSERT INTO unit_tags (unitId, tagId) VALUES (%s, %s)
        ON CONFLICT (unitId, tagId) DO NOTHING'''
        self.cursor.exeute("SELECT id from tags")
        visibleTags = {row[0] for row in self.cursor.fetchall()}
        self.cursor.execute("SELECT baseId from units")
        playableUnits = {row[0] for row in self.cursor.fetchall()}
        for unit in units:
            baseId = unit['baseId']
            for tag in unit['categoryId']:
                if tag in visibleTags:
                    self.cursor.execute(query, (baseId, tag))
        self.connection.commit()
from database import Database
from swgoh_comlink import SwgohComlink

class DataLoader:
    def __init__(self, database: Database, comlink: SwgohComlink):
        self.db = database
        self.connection = self.db.connection
        self.cursor = self.db.cursor
        self.comlink = comlink
    
    def check_version(self):
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
        gameData = self.comlink.get_game_data(include_pve_units=False)
        localization = self.get_localization()
        self.load_units(gameData['units'], localization)
        self.load_tags(gameData['category'], localization)
        self.load_abilities(gameData['units'], gameData['skill'], gameData['ability'], localization)
    def load_units(self, units, localization):
        for unit in units:
            if unit['obtainableTime'] == '0':
                baseId = unit['baseId']
                name = localization[unit['nameKey']]
                desc = localization[unit['descKey']]
                query = '''
                INSERT INTO units (unit_id, name, description) VALUES (%s, %s, %s)
                ON CONFLICT (unit_id) DO UPDATE SET
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
                INSERT INTO tags (tag_id, name) VALUES (%s, %s)
                ON CONFLICT (tag_id) DO UPDATE SET
                name = excluded.name;
                '''
                self.cursor.execute(query, (id, name))
                self.connection.commit()

    def load_unit_tags(self, units):
        query = '''
        INSERT INTO unit_tags (unit_id, tag_id) VALUES (%s, %s)
        ON CONFLICT (unit_id, tag_id) DO NOTHING'''
        self.cursor.execute("SELECT tag_id from tags")
        visibleTags = {row[0] for row in self.cursor.fetchall()}
        self.cursor.execute("SELECT unit_id from units")
        playableUnits = {row[0] for row in self.cursor.fetchall()}
        for unit in units:
            baseId = unit['baseId']
            if baseId in playableUnits:
                for tag in unit['categoryId']:
                    if tag in visibleTags:
                        self.cursor.execute(query, (baseId, tag))
        self.connection.commit()
    
    def load_abilities(self, units, skills, abilities, localization):
        queryUnits = '''
        SELECT unit_id FROM units
        '''
        queryAbilities = '''
        INSERT INTO abilities (skill_id, name, description, max_level, is_zeta, is_omicron, omicron_mode) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (skill_id) DO UPDATE SET
        description = excluded.description
        '''
        queryUnitsAbilities = '''
        INSERT INTO unit_abilities (unit_id, ability_id) VALUES (%s, %s)
        ON CONFLICT (unit_id, ability_id) DO NOTHING
        '''
        self.cursor.execute(queryUnits)
        playableUnits = [row[0] for row in self.cursor.fetchall()]
        for unit in units:
            baseId = unit['baseId']
            if baseId not in playableUnits:
                continue
            skillIds = [skill['skillId'] for skill in unit['skillReference']]
            skillIds += [skill['skillReference'][0]['skillId'] for skill in unit['crew']]
            for id in skillIds:
                name, desc, maxLevel, isZeta, isOmicron, omiMode = self.__get_skill_data(id, skills, abilities, localization)
                self.cursor.execute(queryAbilities, (id, name, desc, maxLevel, isZeta, isOmicron, omiMode))
                self.cursor.execute(queryUnitsAbilities, (baseId, id))
        self.connection.commit()
            
    def __get_skill_data(self, id, skills, abilities, localization):
        for skill in skills:
            if skill['id'] != id:
                continue
            maxLevel = len(skill['tier']) + 1
            isZeta = skill['isZeta']
            if skill['omicronMode'] != 1:
                isOmicron = True
                omiMode = skill['omicronMode']
            else:
                isOmicron = False
                omiMode = None
            for ability in abilities:
                if ability['id'] != skill['abilityReference']:
                    continue
                name = localization[ability['nameKey']]
                descKey = ability['tier'][-1]['descKey']
                desc = localization[descKey]
        return name, desc, maxLevel, isZeta, isOmicron, omiMode
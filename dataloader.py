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
        self.gameData = self.comlink.get_game_data(include_pve_units=False)
        self.localization = self.get_localization()
        self.load_units()
        self.load_tags()
        self.load_unit_tags()
        self.load_abilities()
    
    def load_units(self):
        query = '''
        INSERT INTO units (unit_id, name, description, image_url) VALUES (%s, %s, %s, %s)
        ON CONFLICT (unit_id) DO UPDATE SET
        name = excluded.name,
        description = excluded.description;
        '''
        processedUnits = set()

        for unit in self.gameData['units']:
            unitId = unit['baseId']
            if unit['obtainableTime'] != '0' or unitId in processedUnits:
                continue
            
            name = self.localization[unit['nameKey']]
            desc = self.localization[unit['descKey']]
            imageUrl = unit['thumbnailName']
            
            self.cursor.execute(query, (unitId, name, desc, imageUrl))
            processedUnits.add(unitId)

        self.connection.commit()

    def load_tags(self):
        query = '''
        INSERT INTO tags (tag_id, name) VALUES (%s, %s)
        ON CONFLICT (tag_id) DO UPDATE SET
        name = excluded.name;
        '''

        for tag in self.gameData['category']:
            if not tag['visible'] or tag['id'] == 'eventonly':
                continue

            id = tag['id']
            name = self.localization[tag['descKey']]
            self.cursor.execute(query, (id, name))

        self.connection.commit()

    def load_unit_tags(self):
        self.cursor.execute("SELECT tag_id from tags")
        visibleTags = {row[0] for row in self.cursor.fetchall()}

        self.cursor.execute("SELECT unit_id from units")
        playableUnits = {row[0] for row in self.cursor.fetchall()}

        query = '''
        INSERT INTO unit_tags (unit_id, tag_id) VALUES (%s, %s)
        ON CONFLICT (unit_id, tag_id) DO NOTHING
        '''
        processedUnits = set()

        for unit in self.gameData['units']:
            unitId = unit['baseId']
            if unitId not in playableUnits or unitId in processedUnits:
                continue

            for tag in unit['categoryId']:
                if tag in visibleTags:
                    self.cursor.execute(query, (unitId, tag))

            processedUnits.add(unitId)

        self.connection.commit()
    
    def load_abilities(self):
        selectUnits = '''
        SELECT unit_id FROM units
        '''
        insertAbilities = '''
        INSERT INTO abilities (skill_id, name, description, max_level, is_zeta, is_omicron, omicron_mode, image_url) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (skill_id) DO UPDATE SET
        description = excluded.description
        '''
        insertUnitsAbilities = '''
        INSERT INTO unit_abilities (unit_id, ability_id) VALUES (%s, %s)
        ON CONFLICT (unit_id, ability_id) DO NOTHING
        '''
        self.cursor.execute(selectUnits)
        playableUnits = {row[0] for row in self.cursor.fetchall()}

        #Lookup dictionaries for helper function
        skills = {s['id']: s for s in self.gameData['skill']}
        abilities = {a['id']: a for a in self.gameData['ability']}

        for unit in self.gameData['units']:
            unitId = unit['baseId']
            if unitId not in playableUnits:
                continue
            skillIds = [s['skillId'] for s in unit['skillReference']] + [s['skillReference'][0]['skillId'] for s in unit['crew']]
            for id in skillIds:
                skillData = self.__get_skill_data(id, skills, abilities)
                self.cursor.execute(insertAbilities, skillData)
                self.cursor.execute(insertUnitsAbilities, (unitId, id))

        self.connection.commit()
            
    def __get_skill_data(self, id, skills, abilities):
        skill = skills[id]
        maxLevel = len(skill['tier']) + 1
        isZeta = skill['isZeta']
        isOmicron = skill['omicronMode'] != 1
        omiMode = skill['omicronMode'] if isOmicron else None

        ability = abilities[skill['abilityReference']]
        name = self.localization[ability['nameKey']]
        descKey = ability['tier'][-1]['descKey']
        desc = self.localization[descKey]
        imageUrl = ability["icon"]
        return id, name, desc, maxLevel, isZeta, isOmicron, omiMode, imageUrl
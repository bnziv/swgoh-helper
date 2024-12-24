from database import Database
from swgoh_comlink import SwgohComlink
from queries import Queries
queries = Queries()

class DataLoader:
    def __init__(self, database: Database, comlink: SwgohComlink):
        self.db = database
        self.connection = self.db.connection
        self.cursor = self.db.cursor
        self.comlink = comlink
        self.gameData = self.comlink.get_game_data(include_pve_units=False)
        self.localization = self.get_localization()
        self.skills_dict = {s['id']: s for s in self.gameData['skill']}
    
    def check_version(self):
        version = self.comlink.get_latest_game_data_version()['game']
        query = '''
        SELECT version FROM game_version ORDER BY timestamp DESC LIMIT 1
        '''
        self.cursor.execute(query)
        result = self.db.cursor.fetchone()
        if not result or result[0] != version:
            print("New version detected, updating database")
            self.cursor.execute(queries.insert_game_version, (version,))
            self.connection.commit()
            self.load_data()
        else:
            print("Game data is up to date")
        
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
        self.load_units()
        self.load_tags()
        self.load_unit_tags()
        self.load_abilities()
    
    def load_units(self):
        processedUnits = set()

        for unit in self.gameData['units']:
            unitId = unit['baseId']
            if unit['obtainableTime'] != '0' or unitId in processedUnits:
                continue
            
            name = self.localization[unit['nameKey']]
            desc = self.localization[unit['descKey']]
            imageUrl = unit['thumbnailName']
            
            self.cursor.execute(queries.insert_unit, (unitId, name, desc, imageUrl))
            processedUnits.add(unitId)

        self.connection.commit()

    def load_tags(self):
        for tag in self.gameData['category']:
            if not tag['visible'] or tag['id'] == 'eventonly':
                continue

            id = tag['id']
            name = self.localization[tag['descKey']]
            self.cursor.execute(queries.insert_tag, (id, name))

        self.connection.commit()

    def load_unit_tags(self):
        self.cursor.execute("SELECT tag_id from tags")
        visibleTags = {row[0] for row in self.cursor.fetchall()}

        self.cursor.execute("SELECT unit_id from units")
        playableUnits = {row[0] for row in self.cursor.fetchall()}

        processedUnits = set()

        for unit in self.gameData['units']:
            unitId = unit['baseId']
            if unitId not in playableUnits or unitId in processedUnits:
                continue

            for tag in unit['categoryId']:
                if tag in visibleTags:
                    self.cursor.execute(queries.insert_unit_tag, (unitId, tag))

            processedUnits.add(unitId)

        self.connection.commit()
    
    def load_abilities(self):
        selectUnits = '''
        SELECT unit_id FROM units
        '''
        self.cursor.execute(selectUnits)
        playableUnits = {row[0] for row in self.cursor.fetchall()}
        processedUnits = set()

        #Lookup dictionaries for helper function
        skills = self.skills_dict
        abilities = {a['id']: a for a in self.gameData['ability']}

        for unit in self.gameData['units']:
            unitId = unit['baseId']
            if unitId not in playableUnits or unitId in processedUnits:
                continue
            skillIds = [s['skillId'] for s in unit['skillReference']] + [s['skillReference'][0]['skillId'] for s in unit['crew']]
            for id in skillIds:
                skillData = self.__get_skill_data(id, skills, abilities)
                self.cursor.execute(queries.insert_ability, skillData)
                self.cursor.execute(queries.insert_unit_ability, (unitId, skillData[0]))
            processedUnits.add(unitId)
            
            #For galactic legend ultimate abilities
            if "galactic_legend" not in unit['categoryId']:
                continue
            for a in unit['limitBreakRef']:
                if a['abilityId'].startswith('ultimate'):
                    ability = abilities[a['abilityId']]
                    name = self.localization[ability['nameKey']]
                    desc = self.localization[ability['descKey']]
                    imageUrl = ability['icon']
                    self.cursor.execute(queries.insert_ability, (ability['id'], None, name, desc, 1, False, False, None, imageUrl))
                    self.cursor.execute(queries.insert_unit_ability, (unitId, ability['id']))

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
        return ability['id'], id, name, desc, maxLevel, isZeta, isOmicron, omiMode, imageUrl
    
    def get_upgrade_skill_data(self, id, old_level, new_level):
        zetaFlag = omicronFlag = False
        skill = self.skills_dict[id]
        purchased_levels = range(old_level+1, new_level+1)
        
        for i in purchased_levels:
             #tier[0] is for leveling from 1 to 2, tier[1] is for leveling from 2 to 3, etc
            previous_level = skill['tier'][i-3 if i > 2 else 0]
            ability = skill['tier'][i-2]

            if ability['isZetaTier'] and not previous_level['isZetaTier']:
                zetaFlag = True
            if ability['isOmicronTier'] and not previous_level['isOmicronTier']:
                omicronFlag = True
        return zetaFlag, omicronFlag
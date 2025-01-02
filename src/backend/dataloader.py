import asyncio
import time
from backend.database import Database
from swgoh_comlink import SwgohComlink
from backend import queries, log

class DataLoader:
    def __init__(self, database: Database, comlink: SwgohComlink):
        self.db = database
        self.connection = self.db.connection
        self.cursor = self.db.cursor
        self.comlink = comlink
    
    async def check_version(self):
        """
        Check comlink data version with database and update if necessary
        """
        version = self.comlink.get_latest_game_data_version()['game']
        query = '''
        SELECT version FROM game_version ORDER BY timestamp DESC LIMIT 1
        '''
        self.cursor.execute(query)
        result = self.db.cursor.fetchone()
        if not result or result[0] != version:
            log("New version detected, updating database")
            self.cursor.execute(queries.insert_game_version, (version,))
            self.connection.commit()
            await self.load_data()
            log("Update complete")
        else:
            log("Database is up to date")
        
    def convert_localization(self):
        """
        Convert the Comlink localization response into a dictionary
        """
        data = self.comlink.get_localization(locale="ENG_US", unzip=True, enums=True)['Loc_ENG_US.txt']
        lines = data.strip().split('\n')
        localization = {}
        for line in lines:
            if line.startswith('#'):
                continue
            key, value = line.split('|', 1)
            localization[key.strip()] = value.strip()
        return localization
    
    def get_localization(self, key):
        """
        Get localization value from database
        """
        self.cursor.execute(queries.get_localization, (key,))
        return self.cursor.fetchone()[0]

    async def load_data(self):
        self.load_localization()
        self.load_tags()
        skills = self.comlink.get_game_data(items="SkillDefinitions")
        skills = {s['id']: s for s in skills['skill']}
        abilities = self.comlink.get_game_data(items="AbilityDefinitions")
        abilities = {a['id']: a for a in abilities['ability']}
        await asyncio.sleep(20) #Sleep for Comlink memory release
        self.load_units(skills, abilities)
        self.load_ability_upgrades(skills)
        self.load_portraits()
    
    def load_localization(self):
        localization = self.convert_localization()
        for key, value in localization.items():
            self.cursor.execute(queries.insert_localization, (key, value))
        self.connection.commit()

    def load_units(self, skills, abilities):
        """
        Load units and their tags into the database
        """
        game_data = self.comlink.get_game_data(items="UnitDefinitions")
        self.cursor.execute("SELECT tag_id from tags")
        visibleTags = {row[0] for row in self.cursor.fetchall()}
        processedUnits = set()

        for unit in game_data['units']:
            unitId = unit['baseId']
            if unit['obtainableTime'] != '0' or not unit['obtainable'] or unitId in processedUnits:
                continue
            
            name = self.get_localization(unit['nameKey'])
            desc = self.get_localization(unit['descKey'])
            imageUrl = unit['thumbnailName']
            
            self.cursor.execute(queries.insert_unit, (unitId, name, desc, imageUrl))

            for tag in unit['categoryId']:
                if tag in visibleTags:
                    self.cursor.execute(queries.insert_unit_tag, (unitId, tag))

            self.load_abilities(unit, skills, abilities)
            processedUnits.add(unitId)

        self.connection.commit()

    def load_tags(self):
        """
        Load all visible tags into the database
        """
        game_data = self.comlink.get_game_data(items="CategoryDefinitions")
        for tag in game_data['category']:
            if not tag['visible'] or tag['id'] == 'eventonly':
                continue

            id = tag['id']
            name = self.get_localization(tag['descKey'])
            self.cursor.execute(queries.insert_tag, (id, name))

        self.connection.commit()

    def load_abilities(self, unit, skills_dict, abilities_dict):
        """
        Load a unit's abilities into the database
        """
        unitId = unit['baseId']
        skill_ids = [s['skillId'] for s in unit['skillReference']] + [s['skillReference'][0]['skillId'] for s in unit['crew']]
        for id in skill_ids:
            skillData = self.__get_skill_data(id, skills_dict, abilities_dict)
            self.cursor.execute(queries.insert_ability, skillData)
            self.cursor.execute(queries.insert_unit_ability, (unitId, skillData[0]))
        
        #For galactic legend ultimate abilities
        if "galactic_legend" not in unit['categoryId']:
            return
        for a in unit['limitBreakRef']:
            if a['abilityId'].startswith('ultimate'):
                ability = abilities_dict[a['abilityId']]
                name = self.get_localization(ability['nameKey'])
                desc = self.get_localization(ability['descKey'])
                imageUrl = ability['icon']
                self.cursor.execute(queries.insert_ability, (ability['id'], None, name, desc, 1, False, False, None, imageUrl))
                self.cursor.execute(queries.insert_unit_ability, (unitId, ability['id']))
    
    def load_ability_upgrades(self, skills):
        """
        Load an ability's zeta and omicron levels into the database
        """
        self.db.cursor.execute("SELECT skill_id FROM abilities WHERE skill_id IS NOT NULL")
        for skill_id in self.db.cursor.fetchall():
            zeta_level = omicron_level = None
            skill = skills[skill_id[0]]
            for i in range(len(skill['tier'])):
                tier = skill['tier'][i]
                if 'zeta' in tier['recipeId'].lower():
                    zeta_level = i + 2
                if 'omicron' in tier['recipeId'].lower():
                    omicron_level = i + 2
            if zeta_level or omicron_level:
                self.cursor.execute(queries.insert_ability_upgrade, (zeta_level, omicron_level, skill_id))

    def __get_skill_data(self, id, skills, abilities):
        """
        Helper function to get relevant data for an ability
        """
        skill = skills[id]
        maxLevel = len(skill['tier']) + 1
        isZeta = skill['isZeta']
        isOmicron = skill['omicronMode'] != 1
        omiMode = skill['omicronMode'] if isOmicron else None

        ability = abilities[skill['abilityReference']]
        name = self.get_localization(ability['nameKey'])
        descKey = ability['tier'][-1]['descKey']
        desc = self.get_localization(descKey)
        imageUrl = ability["icon"]
        return ability['id'], id, name, desc, maxLevel, isZeta, isOmicron, omiMode, imageUrl
    
    def load_portraits(self):
        """
        Load all player portraits into the database
        """
        game_data = self.comlink.get_game_data(items="PlayerPortaitDefinitions") #Typo intended due to wrapper
        for portrait in game_data['playerPortrait']:
            self.cursor.execute(queries.insert_portrait, (portrait['id'], self.get_localization(portrait['nameKey']), portrait['icon']))
        self.connection.commit()
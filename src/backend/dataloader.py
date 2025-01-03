import asyncio
from datetime import datetime
import time
from backend.database import Database
from swgoh_comlink import SwgohComlink
from backend import queries, log

class DataLoader:
    def __init__(self, database: Database, comlink: SwgohComlink):
        self.db = database
        self.comlink = comlink
    
    async def check_version(self):
        """
        Check comlink data version with database and update if necessary
        """
        version = self.comlink.get_latest_game_data_version()['game']
        query = '''
        SELECT version FROM game_version ORDER BY timestamp DESC LIMIT 1
        '''
        result = await self.db.fetchval(query)
        if not result or result != version:
            log("New version detected, updating database")
            await self.db.execute(queries.insert_game_version, version)
            await self.load_data()
            log("Update complete")
        else:
            log("Database is up to date")
        
    def convert_localization(self, tuples=False):
        """
        Convert the Comlink localization response into a dictionary or list of tuples
        """
        data = self.comlink.get_localization(locale="ENG_US", unzip=True, enums=True)['Loc_ENG_US.txt']
        lines = data.strip().split('\n')
        if tuples:
            localization = []
            for line in lines:
                if line.startswith('#'):
                    continue
                key, value = line.split('|', 1)
                localization.append((key.strip(), value.strip()))
        else:
            localization = {}
            for line in lines:
                if line.startswith('#'):
                    continue
                key, value = line.split('|', 1)
                localization[key.strip()] = value.strip()
        return localization
    
    async def get_localization(self, key):
        """
        Get localization value from database
        """
        result = await self.db.fetchval(queries.get_localization, key)
        return result

    async def load_data(self):
        log("Loading localization...")
        await self.load_localization()
        log("Loading tags...")
        await self.load_tags()
        skills = self.comlink.get_game_data(items="SkillDefinitions")
        skills = {s['id']: s for s in skills['skill']}
        abilities = self.comlink.get_game_data(items="AbilityDefinitions")
        abilities = {a['id']: a for a in abilities['ability']}
        await asyncio.sleep(20) #Sleep for Comlink memory release
        log("Loading units...")
        await self.load_units(skills, abilities)
        log("Loading ability upgrades...")
        await self.load_ability_upgrades(skills)
        log("Loading portrait data...")
        await self.load_portraits()
    
    async def load_localization(self):
        """
        Load localization into the database
        """
        async def function(connection):
            localization = self.convert_localization(tuples=True)
            await connection.executemany(queries.insert_localization, localization)

        await self.db.transaction(function)

    async def load_units(self, skills, abilities):
        """
        Load units, their abilities and tags into the database
        """
        #Load all units, tags and their abilities in one transaction
        async def function(connection):
            game_data = self.comlink.get_game_data(items="UnitDefinitions")
            result = await connection.fetch("SELECT tag_id from tags")
            visibleTags = {row['tag_id'] for row in result}
            processedUnits = set()

            for unit in game_data['units']:
                unitId = unit['baseId']
                if unit['obtainableTime'] != '0' or not unit['obtainable'] or unitId in processedUnits:
                    continue
                
                name = await self.get_localization(unit['nameKey'])
                desc = await self.get_localization(unit['descKey'])
                imageUrl = unit['thumbnailName']
                
                await connection.execute(queries.insert_unit, unitId, name, desc, imageUrl)

                for tag in unit['categoryId']:
                    if tag in visibleTags:
                        await connection.execute(queries.insert_unit_tag, unitId, tag)

                await self.load_abilities(unit, skills, abilities, connection)
                processedUnits.add(unitId)

        await self.db.transaction(function)

    async def load_tags(self):
        """
        Load all visible tags into the database
        """
        async def function(connection):
            game_data = self.comlink.get_game_data(items="CategoryDefinitions")
            data = []
            for tag in game_data['category']:
                if not tag['visible'] or tag['id'] == 'eventonly':
                    continue

                id = tag['id']
                name = await self.get_localization(tag['descKey'])
                data.append((id, name))

            await connection.executemany(queries.insert_tag, data)

        await self.db.transaction(function)

    async def load_abilities(self, unit, skills_dict, abilities_dict, connection):
        """
        Load a unit's abilities into the database
        """
        unitId = unit['baseId']
        skill_ids = [s['skillId'] for s in unit['skillReference']] + [s['skillReference'][0]['skillId'] for s in unit['crew']]
        abilities_data = []
        unit_abilities_data = []
        for id in skill_ids:
            skill_data = await self.__get_skill_data(id, skills_dict, abilities_dict)
            abilities_data.append(skill_data)
            unit_abilities_data.append((unitId, skill_data[0]))
        
        #For galactic legend ultimate abilities
        if "galactic_legend" in unit['categoryId']:
            for a in unit['limitBreakRef']:
                if a['abilityId'].startswith('ultimate'):
                    ability = abilities_dict[a['abilityId']]
                    name = await self.get_localization(ability['nameKey'])
                    desc = await self.get_localization(ability['descKey'])
                    imageUrl = ability['icon']
                    abilities_data.append((ability['id'], None, name, desc, 1, False, False, None, imageUrl))
                    unit_abilities_data.append((unitId, ability['id']))

        await connection.executemany(queries.insert_ability, abilities_data)
        await connection.executemany(queries.insert_unit_ability, unit_abilities_data)
    
    async def load_ability_upgrades(self, skills):
        """
        Load an ability's zeta and omicron levels into the database
        """
        async def function(connection):
            result = await connection.fetch("SELECT skill_id FROM abilities WHERE skill_id IS NOT NULL")
            data = []
            for row in result:
                skill_id = row['skill_id']
                zeta_level = omicron_level = None
                skill = skills[skill_id]
                for i in range(len(skill['tier'])):
                    tier = skill['tier'][i]
                    if 'zeta' in tier['recipeId'].lower():
                        zeta_level = i + 2
                    if 'omicron' in tier['recipeId'].lower():
                        omicron_level = i + 2
                if zeta_level or omicron_level:
                    data.append((zeta_level, omicron_level, skill_id))
                    
            await connection.executemany(queries.insert_ability_upgrade, data)
        
        await self.db.transaction(function)

    async def __get_skill_data(self, id, skills, abilities):
        """
        Helper function to get relevant data for an ability
        """
        skill = skills[id]
        maxLevel = len(skill['tier']) + 1
        isZeta = skill['isZeta']
        isOmicron = skill['omicronMode'] != 1
        omiMode = skill['omicronMode'] if isOmicron else None

        ability = abilities[skill['abilityReference']]
        name = await self.get_localization(ability['nameKey'])
        descKey = ability['tier'][-1]['descKey']
        desc = await self.get_localization(descKey)
        imageUrl = ability["icon"]
        return ability['id'], id, name, desc, maxLevel, isZeta, isOmicron, omiMode, imageUrl
    
    async def load_portraits(self):
        """
        Load all player portraits into the database
        """
        async def function(connection):
            game_data = self.comlink.get_game_data(items="PlayerPortaitDefinitions") #Typo intended due to wrapper
            data = []
            for portrait in game_data['playerPortrait']:
                data.append((portrait['id'], await self.get_localization(portrait['nameKey']), portrait['icon']))

            await connection.executemany(queries.insert_portrait, data)
            
        await self.db.transaction(function)
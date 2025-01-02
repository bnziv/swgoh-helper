from backend.database import Database
from swgoh_comlink import SwgohComlink
from backend import queries

class Roster:
    def __init__(self, database: Database, comlink: SwgohComlink):
        self.db = database
        self.connection = self.db.connection
        self.cursor = self.db.cursor
        self.comlink = comlink

    def get_roster(self, allycode):
        """
        Returns a two dictionaries for the allycode's roster, units and unit skills
        """
        data = self.comlink.get_player(allycode=allycode)['rosterUnit']
        units = {}
        unit_skills = {}
        for unit in data:
            unit_data = {}
            unit_data['baseId'] = unit['definitionId'].split(':')[0]
            unit_data['level'] = unit['currentLevel']
            unit_data['stars'] = unit['currentRarity']
            unit_data['gearLevel'] = unit['currentTier'] if unit['relic'] else None
            unit_data['relicLevel'] = unit['relic']['currentTier'] - 2 if unit['currentTier'] == 13 else None
            unit_data['ultimate'] = True if unit['purchasedAbilityId'] else False

            skills = {}
            for skill in unit['skill']:
                skills[skill['id']] = skill['tier'] + 2
            units[unit['id']] = unit_data
            unit_skills[unit['id']] = skills
        
        return units, unit_skills
    
    def insert_roster(self, allycode, update=True):
        """
        Inserts the allycode's roster into the database and returns the updated rows if the update flag is True
        """
        units, unit_skills = self.get_roster(allycode)
        updates = []
        # Iterate through each unit
        for unit_id, unit_data in units.items():
            self.cursor.execute(queries.roster.insert_roster, (unit_id, unit_id, unit_data['baseId'], unit_data['level'], unit_data['stars'], unit_data['gearLevel'], unit_data['relicLevel'], unit_data['ultimate'], allycode))
            if update:
                results = self.cursor.fetchone()
                if results:
                    updates.append(results)

            # Iterate through each unit's abilities
            for skill_id, skill_level in unit_skills[unit_id].items():
                self.cursor.execute(queries.roster.insert_roster_abilities, (unit_id, skill_id, skill_id, unit_id, skill_level))
                if update:
                    results = self.cursor.fetchone()
                    if results:
                        updates.append(results)
        
        self.connection.commit()
        return updates
    
    def get_upgrade_skill_data(self, id, old_level, new_level):
        """
        Returns whether an ability upgrade is a zeta and/or omicron upgrade
        """
        zetaFlag = omicronFlag = False
        self.cursor.execute('''SELECT zeta_level, omicron_level FROM ability_upgrades WHERE skill_id = %s''', (id,))
        result = self.cursor.fetchone()
        if not result:
            return zetaFlag, omicronFlag
        
        zeta_level = result[0]
        omicron_level = result[1]
        purchased_levels = range(old_level+1, new_level+1)
        if zeta_level in purchased_levels:
            zetaFlag = True
        if omicron_level in purchased_levels:
            omicronFlag = True
        return zetaFlag, omicronFlag
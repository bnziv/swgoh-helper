class Queries:
    def __init__(self):
        pass

    insert_game_version = '''
    INSERT INTO game_version (version) VALUES (%s)
    ON CONFLICT (version) DO NOTHING;
    '''

    insert_unit = '''
    INSERT INTO units (unit_id, name, description, image_url) VALUES (%s, %s, %s, %s)
    ON CONFLICT (unit_id) DO UPDATE SET
    name = excluded.name,
    description = excluded.description;
    '''

    insert_tag = '''
    INSERT INTO tags (tag_id, name) VALUES (%s, %s)
    ON CONFLICT (tag_id) DO UPDATE SET
    name = excluded.name;
    '''

    insert_unit_tag = ''' 
    INSERT INTO unit_tags (unit_id, tag_id) VALUES (%s, %s)
    ON CONFLICT (unit_id, tag_id) DO NOTHING
    '''

    insert_discord_user = '''
    INSERT INTO discord_users (discord_id) VALUES (%s) 
    ON CONFLICT (discord_id) DO NOTHING
    '''
    
    insert_linked_account = '''
    INSERT INTO linked_accounts (allycode, discord_id, name, time_offset) VALUES (%s, %s, %s, %s)
    '''

    insert_ability = '''
    INSERT INTO abilities (ability_id, skill_id, name, description, max_level, is_zeta, is_omicron, omicron_mode, image_url) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (ability_id) DO UPDATE SET
    name = excluded.name,
    description = excluded.description,
    max_level = excluded.max_level,
    is_zeta = excluded.is_zeta,
    is_omicron = excluded.is_omicron,
    omicron_mode = excluded.omicron_mode,
    image_url = excluded.image_url,
    skill_id = excluded.skill_id;
    '''

    insert_ability_upgrade = '''
    INSERT INTO ability_upgrades (zeta_level, omicron_level, skill_id) VALUES (%s, %s, %s)
    ON CONFLICT (skill_id) DO UPDATE SET
    zeta_level = excluded.zeta_level,
    omicron_level = excluded.omicron_level;
    '''

    insert_unit_ability = '''
    INSERT INTO unit_abilities (unit_id, ability_id) VALUES (%s, %s)
    ON CONFLICT (unit_id, ability_id) DO NOTHING
    '''

    insert_portrait = '''
    INSERT INTO portraits (id, name, icon) VALUES (%s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET name = excluded.name, icon = excluded.icon
    '''

    insert_localization = '''
    INSERT INTO localization (key, value) VALUES (%s, %s) 
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    '''

    get_localization = '''
    SELECT value FROM localization WHERE key = %s
    '''

    class roster:
        insert_roster = '''
        WITH old AS (
            SELECT * FROM roster_units
            WHERE id = %s
        )
        INSERT INTO roster_units
                        (id, unit_id, level, star_level, gear_level, relic_level, ultimate_ability, owner)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
        level = EXCLUDED.level,
        star_level = EXCLUDED.star_level,
        gear_level = EXCLUDED.gear_level,
        relic_level = EXCLUDED.relic_level,
        ultimate_ability = EXCLUDED.ultimate_ability
        WHERE roster_units.level IS DISTINCT FROM EXCLUDED.level
        OR roster_units.star_level IS DISTINCT FROM EXCLUDED.star_level
        OR roster_units.gear_level IS DISTINCT FROM EXCLUDED.gear_level
        OR roster_units.relic_level IS DISTINCT FROM EXCLUDED.relic_level
        OR roster_units.ultimate_ability IS DISTINCT FROM EXCLUDED.ultimate_ability
        RETURNING   roster_units.id,
                    (SELECT level FROM old) AS old_level,
                    roster_units.level AS new_level,
                    (SELECT star_level FROM old) AS old_star_level,
                    roster_units.star_level AS new_star_level,
                    (SELECT gear_level FROM old) AS old_gear_level,
                    roster_units.gear_level AS new_gear_level,
                    (SELECT relic_level FROM old) AS old_relic_level,
                    roster_units.relic_level AS new_relic_level,
                    (SELECT ultimate_ability FROM old) AS old_ultimate_ability,
                    roster_units.ultimate_ability AS new_ultimate_ability;
        '''
        insert_roster_abilities = '''
        WITH old AS (
            SELECT * FROM roster_unit_abilities
            WHERE unit_id = %s AND skill_id = %s
        )
        INSERT INTO roster_unit_abilities (skill_id, unit_id, level)
        VALUES (%s, %s, %s)
        ON CONFLICT (skill_id, unit_id) DO UPDATE SET
        level = EXCLUDED.level
        WHERE roster_unit_abilities.level IS DISTINCT FROM EXCLUDED.level
        RETURNING   roster_unit_abilities.unit_id,
                    roster_unit_abilities.skill_id,
                    (SELECT level FROM old) AS old_level,
                    roster_unit_abilities.level AS new_level;
        '''
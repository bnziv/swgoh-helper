class Queries:
    def __init__(self):
        pass

    insert_game_version = '''
    INSERT INTO game_version (version) VALUES ($1)
    ON CONFLICT (version) DO NOTHING;
    '''

    insert_unit = '''
    INSERT INTO units (unit_id, name, description, image_url) VALUES ($1, $2, $3, $4)
    ON CONFLICT (unit_id) DO UPDATE SET
    name = excluded.name,
    description = excluded.description;
    '''

    insert_tag = '''
    INSERT INTO tags (tag_id, name) VALUES ($1, $2)
    ON CONFLICT (tag_id) DO UPDATE SET
    name = excluded.name;
    '''

    insert_unit_tag = ''' 
    INSERT INTO unit_tags (unit_id, tag_id) VALUES ($1, $2)
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
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
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
    INSERT INTO ability_upgrades (zeta_level, omicron_level, skill_id) VALUES ($1, $2, $3)
    ON CONFLICT (skill_id) DO UPDATE SET
    zeta_level = excluded.zeta_level,
    omicron_level = excluded.omicron_level;
    '''

    insert_unit_ability = '''
    INSERT INTO unit_abilities (unit_id, ability_id) VALUES ($1, $2)
    ON CONFLICT (unit_id, ability_id) DO NOTHING
    '''

    insert_portrait = '''
    INSERT INTO portraits (id, name, icon) VALUES ($1, $2, $3)
    ON CONFLICT (id) DO UPDATE SET name = excluded.name, icon = excluded.icon
    '''

    insert_localization = '''
    INSERT INTO localization (key, value) VALUES ($1, $2) 
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    '''

    get_localization = '''
    SELECT value FROM localization WHERE key = $1
    '''

    class roster:
        insert_roster = '''
        WITH old AS (
            SELECT * FROM roster_units
            WHERE id = $1
        )
        INSERT INTO roster_units
                        (id, unit_id, level, star_level, gear_level, relic_level, ultimate_ability, owner)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
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
        RETURNING   roster_units.id AS unit_id,
                    (SELECT star_level FROM old) AS old_star,
                    roster_units.star_level AS new_star,
                    (SELECT gear_level FROM old) AS old_gear,
                    roster_units.gear_level AS new_gear,
                    (SELECT relic_level FROM old) AS old_relic,
                    roster_units.relic_level AS new_relic,
                    (SELECT ultimate_ability FROM old) AS old_ultimate,
                    roster_units.ultimate_ability AS new_ultimate;
        '''
        insert_roster_abilities = '''
        WITH old AS (
            SELECT * FROM roster_unit_abilities
            WHERE unit_id = $1 AND skill_id = $2
        )
        INSERT INTO roster_unit_abilities (skill_id, unit_id, level)
        VALUES ($2, $1, $3)
        ON CONFLICT (skill_id, unit_id) DO UPDATE SET
        level = EXCLUDED.level
        WHERE roster_unit_abilities.level IS DISTINCT FROM EXCLUDED.level
        RETURNING   roster_unit_abilities.unit_id AS unit_id,
                    roster_unit_abilities.skill_id AS skill_id,
                    (SELECT level FROM old) AS old_level,
                    roster_unit_abilities.level AS new_level;
        '''
    
    create_tables = '''
        CREATE TABLE IF NOT EXISTS game_version (
            version VARCHAR PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS localization (
            key VARCHAR PRIMARY KEY,
            value VARCHAR
        );
        CREATE TABLE IF NOT EXISTS units (
            unit_id VARCHAR PRIMARY KEY,
            name VARCHAR,
            description VARCHAR,
            image_url VARCHAR
        );
        CREATE TABLE IF NOT EXISTS tags (
            tag_id VARCHAR PRIMARY KEY,
            name VARCHAR
        );
        CREATE TABLE IF NOT EXISTS unit_tags (
            unit_id VARCHAR REFERENCES units(unit_id) ON UPDATE CASCADE ON DELETE CASCADE,
            tag_id VARCHAR REFERENCES tags(tag_id) ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY (unit_id, tag_id)
        );
        CREATE TABLE IF NOT EXISTS abilities (
            ability_id VARCHAR PRIMARY KEY,
            skill_id VARCHAR UNIQUE,
            name VARCHAR,
            description VARCHAR,
            max_level INT,
            is_zeta BOOLEAN,
            is_omicron BOOLEAN,
            omicron_mode INT DEFAULT NULL,
            image_url VARCHAR
        );
        CREATE TABLE IF NOT EXISTS ability_upgrades (
            id SERIAL PRIMARY KEY,
            zeta_level INT DEFAULT NULL,
            omicron_level INT DEFAULT NULL,
            skill_id VARCHAR REFERENCES abilities(skill_id) ON UPDATE CASCADE ON DELETE CASCADE,
            UNIQUE (skill_id)
        );
        CREATE TABLE IF NOT EXISTS unit_abilities (
            unit_id VARCHAR REFERENCES units(unit_id) ON UPDATE CASCADE ON DELETE CASCADE,
            ability_id VARCHAR REFERENCES abilities(ability_id) ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY (unit_id, ability_id)
        );
        CREATE TABLE IF NOT EXISTS discord_users (
            discord_id VARCHAR(20) PRIMARY KEY,
            notify_events BOOLEAN DEFAULT TRUE
        );
        CREATE TABLE IF NOT EXISTS linked_accounts (
            allycode INT PRIMARY KEY,
            name VARCHAR,
            time_offset INT,
            notify_payout BOOLEAN DEFAULT TRUE,
            notify_energy BOOLEAN DEFAULT TRUE,
            notify_roster BOOLEAN DEFAULT TRUE,
            discord_id VARCHAR REFERENCES discord_users(discord_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS fleet_shard_players (
            allycode INT PRIMARY KEY,
            name VARCHAR,
            time_offset INT,
            part_of INT REFERENCES linked_accounts(allycode)
        );
        CREATE TABLE IF NOT EXISTS roster_units (
            id VARCHAR PRIMARY KEY,
            unit_id VARCHAR REFERENCES units(unit_id) ON DELETE CASCADE,
            level INT,
            star_level INT,
            gear_level INT,
            relic_level INT DEFAULT NULL,
            ultimate_ability BOOLEAN DEFAULT FALSE,
            owner INT REFERENCES linked_accounts(allycode) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS roster_unit_abilities (
            skill_id VARCHAR REFERENCES abilities(skill_id) ON DELETE CASCADE,
            unit_id VARCHAR REFERENCES roster_units(id) ON DELETE CASCADE,
            level INT,
            PRIMARY KEY (skill_id, unit_id)
        );
        CREATE TABLE IF NOT EXISTS portraits (
            id VARCHAR PRIMARY KEY,
            name VARCHAR,
            icon VARCHAR
        );
        '''
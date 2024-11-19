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

    insert_ability = '''
    INSERT INTO abilities (ability_id, name, description, max_level, is_zeta, is_omicron, omicron_mode, image_url) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (ability_id) DO UPDATE SET
    name = excluded.name,
    description = excluded.description,
    max_level = excluded.max_level,
    is_zeta = excluded.is_zeta,
    is_omicron = excluded.is_omicron,
    omicron_mode = excluded.omicron_mode,
    image_url = excluded.image_url;
    '''

    insert_unit_ability = '''
    INSERT INTO unit_abilities (unit_id, ability_id) VALUES (%s, %s)
    ON CONFLICT (unit_id, ability_id) DO NOTHING
    '''
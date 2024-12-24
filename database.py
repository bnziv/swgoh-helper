import psycopg2
import os
from dotenv import load_dotenv

class Database:
    def __init__(self):
        load_dotenv()
        self.user = os.getenv('DB_USERNAME')
        self.password = os.getenv('DB_PASSWORD')
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                dbname='swgoh',
                user=self.user,
                password=self.password
            )
            print("Connected to database.")
        except psycopg2.OperationalError as e:
            print("App database doesn't exist. Attempting to create 'swgoh'")
            try: self.connection = psycopg2.connect(
                    dbname='postgres',
                    user=self.user,
                    password=self.password
                )
            except:
                print("Failed to connect to database or 'postgres' doesn't exist")
                exit(1)
            self.connection.autocommit = True
            self.cursor = self.connection.cursor()
            self.cursor.execute("CREATE DATABASE swgoh")
            self.connection.close()
            self.connect()

        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        query = '''
        CREATE TABLE IF NOT EXISTS game_version (
            version VARCHAR PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            skill_id VARCHAR,
            name VARCHAR,
            description VARCHAR,
            max_level INT,
            is_zeta BOOLEAN,
            is_omicron BOOLEAN,
            omicron_mode INT DEFAULT NULL,
            image_url VARCHAR
        );
        CREATE TABLE IF NOT EXISTS unit_abilities (
            unit_id VARCHAR REFERENCES units(unit_id) ON UPDATE CASCADE ON DELETE CASCADE,
            ability_id VARCHAR REFERENCES abilities(ability_id) ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY (unit_id, ability_id)
        );
        CREATE TABLE IF NOT EXISTS users (
            allycode INT PRIMARY KEY,
            discord_id VARCHAR(20),
            name VARCHAR,
            time_offset INT,
            notify_events BOOLEAN,
            notify_energy BOOLEAN,
            notify_roster BOOLEAN
        );
        CREATE TABLE IF NOT EXISTS fleet_shard_players (
            allycode INT PRIMARY KEY,
            name VARCHAR,
            time_offset INT,
            part_of INT REFERENCES users(allycode)
        );
        CREATE TABLE IF NOT EXISTS roster_units (
            id VARCHAR PRIMARY KEY,
            unit_id VARCHAR REFERENCES units(unit_id) ON DELETE CASCADE,
            level INT,
            star_level INT,
            gear_level INT,
            relic_level INT DEFAULT NULL,
            ultimate_ability BOOLEAN DEFAULT FALSE,
            owner INT REFERENCES users(allycode) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS roster_unit_abilities (
            skill_id VARCHAR REFERENCES abilities(skill_id) ON DELETE CASCADE,
            unit_id VARCHAR REFERENCES roster_units(id) ON DELETE CASCADE,
            level INT,
            PRIMARY KEY (skill_id, unit_id)
        );
        '''
        self.cursor.execute(query)
        self.connection.commit()
import psycopg2
import os
import time
from backend import log

class Database:
    def __init__(self):
        self.user = os.getenv('DB_USERNAME')
        self.password = os.getenv('DB_PASSWORD')
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self):
        for attempts in range(5):
            try:
                self.connection = psycopg2.connect(os.getenv('DB_URL'))
                log("Connected to database.")
                break
            except psycopg2.OperationalError as e:
                if attempts < 4:
                    log("Database connection failed. Retrying...")
                    time.sleep(3)
                else:
                    log("Could not connect to database.")
                    exit(1)

                    ### For manual db server setup ###
                    # print("App database doesn't exist. Attempting to create 'swgoh'")
                    # try: self.connection = psycopg2.connect(
                    #         dbname='postgres',
                    #         user=self.user,
                    #         password=self.password
                    #     )
                    # except:
                    #     print("Failed to connect to database or 'postgres' doesn't exist")
                    #     exit(1)
                    # self.connection.autocommit = True
                    # self.cursor = self.connection.cursor()
                    # self.cursor.execute("CREATE DATABASE swgoh")
                    # self.connection.close()
                    # self.connect()

        if self.connection:
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
            image_url VARCHAR,
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
        self.cursor.execute(query)
        self.connection.commit()
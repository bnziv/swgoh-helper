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
            print("App database doesn't exist. Creating as 'swgoh'...")
            self.connection = psycopg2.connect(
                dbname='postgres',
                user=self.user,
                password=self.password
            )
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
            description VARCHAR
        );
        CREATE TABLE IF NOT EXISTS tags (
            tag_id VARCHAR PRIMARY KEY,
            name VARCHAR
        );
        CREATE TABLE IF NOT EXISTS unit_tags (
            unit_id VARCHAR REFERENCES units(unit_id),
            tag_id VARCHAR REFERENCES tags(tag_id),
            PRIMARY KEY (unit_id, tag_id)
        );
        CREATE TABLE IF NOT EXISTS abilities (
            skill_id VARCHAR PRIMARY KEY,
            name VARCHAR,
            description VARCHAR,
            max_level INT,
            is_zeta BOOLEAN,
            is_omicron BOOLEAN,
            omicron_mode INT DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS unit_abilities (
            unit_id VARCHAR REFERENCES units(unit_id),
            ability_id VARCHAR REFERENCES abilities(skill_id),
            PRIMARY KEY (unit_id, ability_id)
        );
        '''
        self.cursor.execute(query)
        self.connection.commit()
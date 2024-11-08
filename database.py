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
            baseId VARCHAR PRIMARY KEY,
            name VARCHAR,
            description VARCHAR
        );
        CREATE TABLE IF NOT EXISTS tags (
            id VARCHAR PRIMARY KEY,
            name VARCHAR
        );
        CREATE TABLE IF NOT EXISTS unit_tags (
            unitId VARCHAR REFERENCES units(baseId),
            tagId VARCHAR REFERENCES tags(id),
            PRIMARY KEY (unitId, tagId)
        );
        '''
        self.cursor.execute(query)
        self.connection.commit()
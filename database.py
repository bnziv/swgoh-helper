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
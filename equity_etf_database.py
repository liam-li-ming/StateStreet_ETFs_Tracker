import sqlite3
import pandas as pd
from datetime import datetime
import os

class ETFDatabase: 

    def __init__(self, db_path = 'data/equity/equity_etf.db'):
        self.db_path = db_path

        os.makedirs(os.path.dirname(db_path), exist_ok = True)
        self._init_database()

    def start_database(self): 

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS 
                       available_equity_etfs (
                            domicile TEXT NOT NULL,
                            etf_name TEXT NOT NULL, 
                            ticker TEXT NOT NULL PRIMARY KEY, 
                            expense_ratio TEXT,
                            nav TEXT,
                            aum TEXT,
                            updated_date TEXT
                       )
        ''')

    def 

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS 
                       etf_compositions (
                            
                       )

        ''')
#!/usr/bin/env python3
"""
All-in-One Migration Script for Finance Tracker
- Installs dependencies if missing
- Imports both Personal Log.xlsx and Spending.xlsx
- Sets up database and budget periods
"""

import subprocess
import sys
import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import re

# ------------------------------
# Dependency Installer
# ------------------------------
def install_requirements():
    """Install required packages for migration"""
    print("📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
        print("✅ Packages installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install packages. Please run manually:")
        print("   pip install pandas openpyxl")
        return False
    return True

# ------------------------------
# File Checker
# ------------------------------
def check_files():
    """Check if Excel files exist"""
    files_missing = []
    
    if not os.path.exists("Personal Log.xlsx"):
        files_missing.append("Personal Log.xlsx")
    
    if not os.path.exists("Spending.xlsx"):
        files_missing.append("Spending.xlsx")
    
    if files_missing:
        print("❌ Missing Excel files:")
        for file in files_missing:
            print(f"   - {file}")
        print("\nPlease copy your Excel files to this directory and try again.")
        return False
    
    print("✅ Excel files found")
    return True

# ------------------------------
# Database Setup
# ------------------------------
def setup_database():
    conn = sqlite3.connect('finance_tracker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS personal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE UNIQUE NOT NULL,
            gym BOOLEAN DEFAULT 0,
            jiu_jitsu BOOLEAN DEFAULT 0,
            skateboarding BOOLEAN DEFAULT 0,
            work BOOLEAN DEFAULT 0,
            coitus BOOLEAN DEFAULT 0,
            sauna BOOLEAN DEFAULT 0,
            supplements BOOLEAN DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS spending_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            item TEXT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budget_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            budget_amount DECIMAL(10,2) DEFAULT 500.00,
            is_current BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database setup complete")

# ------------------------------
# Personal Data Migration
# ------------------------------
def migrate_personal_data():
    print("\n📊 Migrating personal data...")
    try:
        df = pd.read_excel('Personal Log.xlsx', sheet_name='Life')
        conn = sqlite3.connect('finance_tracker.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM personal_log')
        
        def to_bool(value):
            if pd.isna(value):
                return 0
            return 1 if str(value).lower().strip() in ['yes', 'y', '1', 'true'] else 0
        
        migrated_count = 0
        for _, row in df.iterrows():
            if pd.isna(row.get('Date')):
                continue
            date_obj = pd.to_datetime(row['Date']).date()
            gym = to_bool(row.get('Gym'))
            jiu_jitsu = to_bool(row.get('Jiu Jitsu'))
            skateboarding = to_bool(row.get('Skateboard'))
            work = to_bool(row.get('Work'))
            coitus = to_bool(row.get('Coitus'))
            sauna = to_bool(row.get('Sauna'))
            supplements = to_bool(row.get('Supplements'))
            notes = str(row.get('What ', '')) if not pd.isna(row.get('What ')) else ''
            notes = notes.strip() if notes != 'nan' else ''
            
            cursor.execute('''
                INSERT OR REPLACE INTO personal_log 
                (date, gym, jiu_jitsu, skateboarding, work, coitus, sauna, supplements, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date_obj, gym, jiu_jitsu, skateboarding, work, coitus, sauna, supplements, notes))
            migrated_count += 1
        
        conn.commit()
        conn.close()
        print(f"   ✅ Migrated {migrated_count} personal records")
    except Exception as e:
        print(f"   ❌ Error migrating personal data: {e}")

# ------------------------------
# Spending Data Migration
# ------------------------------
def parse_dates_from_sheet_name(sheet_name):
    patterns = [
        (r'([A-Za-z]+)\s+(\d+)\s*-\s*([A-Za-z]+)\s+(\d+)', 'cross_month'),
        (r'([A-Za-z]+)\s+(\d+)\s*-\s*(\d+)', 'same_month'),
        (r'([A-Za-z]+)\s+(\d+)\s+-\s*(\d+)', 'same_month'),
        (r'([A-Za-z]+)\s+(\d+)\s*-\s*([A-Za-z]+)\s+(\d+)', 'cross_month')
    ]
    for pattern, pattern_type in patterns:
        match = re.match(pattern, sheet_name.strip())
        if match:
            groups = match.groups()
            try:
                if pattern_type == 'cross_month' and len(groups) == 4:
                    start_month, start_day, end_month, end_day = groups
                    for year in [2025, 2024]:
                        try:
                            start_date = pd.to_datetime(f"{start_month} {start_day} {year}").date()
                            end_date = pd.to_datetime(f"{end_month} {end_day} {year}").date()
                            if end_date < start_date:
                                end_date = pd.to_datetime(f"{end_month} {end_day} {year + 1}").date()
                            return start_date, end_date
                        except:
                            continue
                elif pattern_type == 'same_month' and len(groups) == 3:
                    month, start_day, end_day = groups
                    for year in [2025, 2024]:
                        try:
                            start_date = pd.to_datetime(f"{month} {start_day} {year}").date()
                            end_date = pd.to_datetime(f"{month} {end_day} {year}").date()
                            return start_date, end_date
                        except:
                            continue
            except:
                continue
    return None, None

def extract_daily_totals_from_sheet(sheet_name):
    start_date, end_date = parse_dates_from_sheet_name(sheet_name)
    if not start_date:
        print(f"   ❌ Could not parse dates from: {sheet_name}")
        return []
    df = pd.read_excel("Spending.xlsx", sheet_name=sheet_name)
    daily_entries = []
    for row_idx in range(14, min(20, len(df))):
        row = df.iloc[row_idx]
        daily_amounts = []
        for col_idx in range(min(14, len(row))):
            cell_value = row.iloc[col_idx]
            if pd.notna(cell_value):
                try:
                    if isinstance(cell_value, str):
                        cell_value = cell_value.replace('$', '').replace(',', '').strip()
                    amount = float(cell_value)
                    if 0.50 <= amount <= 300.00:
                        expense_date = start_date + timedelta(days=col_idx)
                        if expense_date <= end_date:
                            daily_amounts.append((expense_date, amount))
                except:
                    continue
        if len(daily_amounts) >= 5:
            daily_entries.extend(daily_amounts)
            break
    return daily_entries

def migrate_spending_data():
    print("\n💰 Migrating spending data...")
    excel_file = pd.ExcelFile("Spending.xlsx")
    sheet_names = [name for name in excel_file.sheet_names if name.lower() != 'general' and ' - ' in name]
    conn = sqlite3.connect('finance_tracker.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM spending_log')
    total_migrated = 0
    for sheet_name in sheet_names:
        print(f"\n   📊 Processing: {sheet_name}")
        daily_entries = extract_daily_totals_from_sheet(sheet_name)
        for expense_date, amount in daily_entries:
            cursor.execute('''
                INSERT INTO spending_log (date, item, price)
                VALUES (?, ?, ?)
            ''', (expense_date, "Daily Total", amount))
            total_migrated += 1
            print(f"     {expense_date}: ${amount:.2f}")
    conn.commit()
    conn.close()
    print(f"\n   ✅ Migrated {total_migrated} spending records")

# ------------------------------
# Budget Periods
# ------------------------------
def create_budget_periods():
    print("\n📅 Creating budget periods...")
    conn = sqlite3.connect('finance_tracker.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM budget_periods')
    cursor.execute('SELECT MIN(date), MAX(date) FROM spending_log')
    result = cursor.fetchone()
    if result[0] and result[1]:
        start_date = datetime.strptime(result[0], '%Y-%m-%d').date()
        end_date = datetime.strptime(result[1], '%Y-%m-%d').date()
        current_date = start_date
        today = datetime.now().date()
        period_count = 0
        while current_date <= end_date:
            period_end = current_date + timedelta(days=13)
            is_current = 1 if current_date <= today <= period_end else 0
            cursor.execute('''
                INSERT INTO budget_periods (start_date, end_date, budget_amount, is_current)
                VALUES (?, ?, 500.00, ?)
            ''', (current_date, period_end, is_current))
            period_count += 1
            current_date = period_end + timedelta(days=1)
        conn.commit()
        print(f"   ✅ Created {period_count} budget periods")
    conn.close()

# ------------------------------
# Verification
# ------------------------------
def verify_migration():
    print("\n🔍 Verifying migration...")
    conn = sqlite3.connect('finance_tracker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM personal_log')
    personal_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM spending_log')
    spending_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM budget_periods')
    periods_count = cursor.fetchone()[0]
    conn.close()
    print(f"   📊 Personal activities: {personal_count} records")
    print(f"   💰 Spending entries: {spending_count} records")
    print(f"   📅 Budget periods: {periods_count} periods")

# ------------------------------
# Main
# ------------------------------
def main():
    print("🚀 Finance Tracker Migration")
    print("=" * 55)
    if not check_files():
        return
    if not install_requirements():
        return
    setup_database()
    migrate_personal_data()
    migrate_spending_data()
    create_budget_periods()
    verify_migration()
    print("\n🎉 Migration Completed! Run: python app.py")

if __name__ == "__main__":
    main()

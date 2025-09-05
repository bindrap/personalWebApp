from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from datetime import datetime, timedelta
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure random key

# Database setup
def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect('finance_tracker.db')
    cursor = conn.cursor()
    
    # Personal activities table
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
    
    # Spending entries table
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
    
    # Budget periods table for tracking biweekly budgets
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

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('finance_tracker.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_current_budget_period():
    """Get or create the current budget period"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Try to find current period
    today = datetime.now().date()
    cursor.execute('''
        SELECT * FROM budget_periods 
        WHERE start_date <= ? AND end_date >= ?
        ORDER BY start_date DESC LIMIT 1
    ''', (today, today))
    
    period = cursor.fetchone()
    
    if not period:
        # Create new budget period (14 days from today)
        start_date = today
        end_date = today + timedelta(days=13)  # 14-day period
        
        cursor.execute('''
            INSERT INTO budget_periods (start_date, end_date, budget_amount, is_current)
            VALUES (?, ?, 500.00, 1)
        ''', (start_date, end_date))
        
        period_id = cursor.lastrowid
        conn.commit()
        
        # Get the newly created period
        cursor.execute('SELECT * FROM budget_periods WHERE id = ?', (period_id,))
        period = cursor.fetchone()
    
    conn.close()
    return period

@app.route('/')
def dashboard():
    """Dashboard with analytics"""
    conn = get_db_connection()
    
    # Get current budget period
    budget_period = get_current_budget_period()
    
    # Calculate days left in current period
    today = datetime.now().date()
    end_date = datetime.strptime(budget_period['end_date'], '%Y-%m-%d').date()
    days_left = (end_date - today).days + 1
    
    # Get spending for current period
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(price) as total_spent 
        FROM spending_log 
        WHERE date BETWEEN ? AND ?
    ''', (budget_period['start_date'], budget_period['end_date']))
    
    result = cursor.fetchone()
    total_spent = float(result['total_spent']) if result['total_spent'] else 0.0
    
    # Calculate remaining budget
    budget_amount = float(budget_period['budget_amount'])
    remaining_budget = budget_amount - total_spent
    daily_spend_limit = remaining_budget / max(days_left, 1)
    
    # Get recent activities (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    cursor.execute('''
        SELECT 
            SUM(gym) as gym_count,
            SUM(jiu_jitsu) as jiu_jitsu_count,
            SUM(skateboarding) as skateboarding_count,
            SUM(work) as work_count,
            SUM(coitus) as coitus_count,
            SUM(sauna) as sauna_count,
            SUM(supplements) as supplements_count,
            COUNT(*) as total_days
        FROM personal_log 
        WHERE date >= ?
    ''', (thirty_days_ago,))
    
    activity_stats = cursor.fetchone()
    
    # Get recent spending by category
    cursor.execute('''
        SELECT 
            CASE 
                WHEN LOWER(item) LIKE '%tim%' OR LOWER(item) LIKE '%coffee%' THEN 'Coffee'
                WHEN LOWER(item) LIKE '%gas%' OR LOWER(item) LIKE '%fuel%' THEN 'Gas'
                WHEN LOWER(item) LIKE '%food%' OR LOWER(item) LIKE '%restaurant%' OR LOWER(item) LIKE '%mcdonald%' OR LOWER(item) LIKE '%domino%' THEN 'Food'
                WHEN LOWER(item) LIKE '%weed%' OR LOWER(item) LIKE '%cannabis%' THEN 'Cannabis'
                ELSE 'Other'
            END as category,
            SUM(price) as total
        FROM spending_log 
        WHERE date >= ?
        GROUP BY category
        ORDER BY total DESC
    ''', (thirty_days_ago,))
    
    spending_by_category = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                         budget_period=budget_period,
                         total_spent=total_spent,
                         remaining_budget=remaining_budget,
                         days_left=days_left,
                         daily_spend_limit=daily_spend_limit,
                         activity_stats=activity_stats,
                         spending_by_category=spending_by_category)

@app.route('/personal')
def personal():
    """Personal activities page"""
    today = datetime.now().date()
    
    # Get today's data if it exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM personal_log WHERE date = ?', (today,))
    today_data = cursor.fetchone()
    
    # Get recent entries for display
    cursor.execute('''
        SELECT * FROM personal_log 
        ORDER BY date DESC 
        LIMIT 10
    ''')
    recent_entries = cursor.fetchall()
    
    conn.close()
    
    return render_template('personal.html', 
                         today_data=today_data, 
                         recent_entries=recent_entries,
                         today=today)

@app.route('/personal/save', methods=['POST'])
def save_personal():
    """Save personal activities data"""
    date_str = request.form.get('date')
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Get form data (checkboxes return 'on' if checked, None if not)
    gym = 1 if request.form.get('gym') == 'on' else 0
    jiu_jitsu = 1 if request.form.get('jiu_jitsu') == 'on' else 0
    skateboarding = 1 if request.form.get('skateboarding') == 'on' else 0
    work = 1 if request.form.get('work') == 'on' else 0
    coitus = 1 if request.form.get('coitus') == 'on' else 0
    sauna = 1 if request.form.get('sauna') == 'on' else 0
    supplements = 1 if request.form.get('supplements') == 'on' else 0
    notes = request.form.get('notes', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert or update
    cursor.execute('''
        INSERT OR REPLACE INTO personal_log 
        (date, gym, jiu_jitsu, skateboarding, work, coitus, sauna, supplements, notes, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (date_obj, gym, jiu_jitsu, skateboarding, work, coitus, sauna, supplements, notes))
    
    conn.commit()
    conn.close()
    
    flash('Personal data saved successfully!', 'success')
    return redirect(url_for('personal'))

@app.route('/spending')
def spending():
    """Spending tracking page"""
    today = datetime.now().date()
    
    # Get current budget period
    budget_period = get_current_budget_period()
    
    # Get today's spending
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM spending_log 
        WHERE date = ? 
        ORDER BY created_at DESC
    ''', (today,))
    today_spending = cursor.fetchall()
    
    # Get spending for current period
    cursor.execute('''
        SELECT * FROM spending_log 
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC, created_at DESC
    ''', (budget_period['start_date'], budget_period['end_date']))
    
    period_spending = cursor.fetchall()
    
    # Calculate totals
    cursor.execute('''
        SELECT SUM(price) as total 
        FROM spending_log 
        WHERE date = ?
    ''', (today,))
    today_total = cursor.fetchone()['total'] or 0
    
    cursor.execute('''
        SELECT SUM(price) as total 
        FROM spending_log 
        WHERE date BETWEEN ? AND ?
    ''', (budget_period['start_date'], budget_period['end_date']))
    period_total = cursor.fetchone()['total'] or 0
    
    conn.close()
    
    return render_template('spending.html', 
                         budget_period=budget_period,
                         today_spending=today_spending,
                         period_spending=period_spending,
                         today_total=today_total,
                         period_total=period_total,
                         today=today)

@app.route('/spending/add', methods=['POST'])
def add_spending():
    """Add spending entry"""
    date_str = request.form.get('date')
    item = request.form.get('item')
    price = float(request.form.get('price'))
    
    if not item or price <= 0:
        flash('Please provide valid item and price', 'error')
        return redirect(url_for('spending'))
    
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO spending_log (date, item, price)
        VALUES (?, ?, ?)
    ''', (date_obj, item, price))
    
    conn.commit()
    conn.close()
    
    flash(f'Added {item} for ${price:.2f}', 'success')
    return redirect(url_for('spending'))

@app.route('/spending/delete/<int:entry_id>', methods=['POST'])
def delete_spending(entry_id):
    """Delete spending entry"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM spending_log WHERE id = ?', (entry_id,))
    conn.commit()
    conn.close()
    
    flash('Spending entry deleted', 'success')
    return redirect(url_for('spending'))

@app.route('/api/analytics')
def api_analytics():
    """API endpoint for analytics data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get last 30 days of data for charts
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    
    # Daily spending over last 30 days
    cursor.execute('''
        SELECT date, SUM(price) as total
        FROM spending_log 
        WHERE date >= ?
        GROUP BY date
        ORDER BY date
    ''', (thirty_days_ago,))
    daily_spending = [dict(row) for row in cursor.fetchall()]
    
    # Activity frequency over last 30 days
    cursor.execute('''
        SELECT date, gym, jiu_jitsu, skateboarding, work, coitus, sauna, supplements
        FROM personal_log 
        WHERE date >= ?
        ORDER BY date
    ''', (thirty_days_ago,))
    daily_activities = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'daily_spending': daily_spending,
        'daily_activities': daily_activities
    })

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
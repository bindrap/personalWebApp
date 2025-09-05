# requirements.txt
Flask==2.3.3
Werkzeug==2.3.7

# setup.py or run.py
from app import app, init_db

if __name__ == '__main__':
    print("Initializing database...")
    init_db()
    print("Database initialized!")
    print("Starting Flask app...")
    app.run(debug=True, host='0.0.0.0', port=5000)

---

# PROJECT STRUCTURE
Your project should be organized like this:

finance_tracker/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── run.py                # Application runner
├── finance_tracker.db    # SQLite database (created automatically)
├── templates/
│   ├── base.html         # Base template
│   ├── dashboard.html    # Dashboard page
│   ├── personal.html     # Personal activities page
│   └── spending.html     # Spending tracker page
└── static/               # Static files (optional, using CDN for now)

---

# INSTALLATION INSTRUCTIONS

1. Create a new directory for your project:
   mkdir finance_tracker
   cd finance_tracker

2. Create a virtual environment:
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate

3. Install dependencies:
   pip install flask

4. Create the files:
   - Copy the Flask app code into app.py
   - Create templates/ directory
   - Copy each HTML template into the templates/ directory
   - Create run.py with the setup code above

5. Run the application:
   python run.py

6. Open your browser and go to:
   http://localhost:5000

---

# FEATURES IMPLEMENTED

✅ Dashboard with:
   - Budget overview and progress bar
   - Activity statistics (last 30 days)
   - Spending by category breakdown
   - Interactive charts for spending trends and activity frequency

✅ Personal Activities Tab:
   - Toggle switches for: Gym, Jiu Jitsu, Skateboarding, Work, Coitus, Sauna, Supplements
   - Date picker (defaults to today)
   - Notes field for additional details
   - Recent entries display

✅ Spending Tab:
   - Add expenses with item name and price
   - Date picker (defaults to today)
   - Current budget period display
   - Today's total, period total, and remaining budget
   - Delete functionality for expenses
   - Organized by date with timestamps

✅ Database:
   - SQLite database for easy setup
   - Automatic table creation
   - Budget period management (14-day cycles)
   - Data persistence

✅ Analytics:
   - REST API endpoint for chart data
   - Interactive charts using Chart.js
   - Categorization of spending (Coffee, Gas, Food, Cannabis, Other)
   - Activity frequency tracking

---

# CUSTOMIZATION OPTIONS

Budget Amount:
- Default is $500 per 14-day period
- Can be modified in the get_current_budget_period() function

Activities:
- Easy to add/remove activities by modifying the database schema and forms
- Icons and colors can be customized in the HTML templates

Categories:
- Spending categorization logic is in the dashboard route
- Add more categories by modifying the SQL CASE statement

Styling:
- Using Bootstrap 5 for responsive design
- Custom CSS in base.html for toggle switches and cards
- Easy to modify colors and layout

---

# DATA MIGRATION (Optional)

If you want to import your existing Excel data:

1. Create a migration script:

```python
import sqlite3
import pandas as pd
from datetime import datetime

def migrate_excel_data():
    # Read your Excel files
    personal_df = pd.read_excel('Personal Log.xlsx', sheet_name='Life')
    
    # Connect to database
    conn = sqlite3.connect('finance_tracker.db')
    cursor = conn.cursor()
    
    # Migrate personal data
    for _, row in personal_df.iterrows():
        if pd.notna(row['Date']):
            cursor.execute('''
                INSERT OR REPLACE INTO personal_log 
                (date, gym, jiu_jitsu, skateboarding, work, coitus, sauna, supplements, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['Date'].strftime('%Y-%m-%d'),
                1 if row.get('Gym') == 'Yes' else 0,
                1 if row.get('Jiu Jitsu') == 'Yes' else 0,
                1 if row.get('Skateboard') == 'Yes' else 0,
                1 if row.get('Work') == 'Yes' else 0,
                1 if row.get('Coitus') == 'Yes' else 0,
                1 if row.get('Sauna') == 'Yes' else 0,
                1 if row.get('Supplements') == 'Yes' else 0,
                row.get('What ', '')
            ))
    
    conn.commit()
    conn.close()
    print("Migration completed!")

# Run migration
migrate_excel_data()
```

---

# TROUBLESHOOTING

1. If templates aren't found:
   - Make sure templates/ folder is in the same directory as app.py
   - Check that all template files are properly named

2. If database errors occur:
   - Delete finance_tracker.db and restart the app
   - The database will be recreated automatically

3. If charts don't load:
   - Check browser console for JavaScript errors
   - Ensure internet connection for CDN resources

4. Port already in use:
   - Change port in app.run() to a different number (e.g., 5001)

---

# NEXT STEPS / ENHANCEMENTS

Possible future improvements:
- User authentication and multiple users
- Data export functionality
- Mobile app using Flask API
- Advanced analytics and goal setting
- Integration with bank APIs
- Backup and sync features
- Monthly/yearly reporting
- Budget alerts and notifications
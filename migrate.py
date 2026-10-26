from database import get_db

conn = get_db()

columns = [
    ('first_name', 'TEXT DEFAULT ""'),
    ('last_name',  'TEXT DEFAULT ""'),
    ('dob',        'TEXT DEFAULT ""'),
    ('phone',      'TEXT DEFAULT ""'),
]

for col_name, col_def in columns:
    try:
        conn.execute(f'ALTER TABLE users ADD COLUMN {col_name} {col_def}')
        print(f'✅ {col_name} added')
    except Exception as e:
        print(f'⚠️  {col_name} already exists — skipping')

conn.commit()
conn.close()
print('\nDone! All columns ready.')

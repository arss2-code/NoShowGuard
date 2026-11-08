import sqlite3
from pathlib import Path

db_paths = [
    Path("G:/SSA/backend/noshowguard.db"),
    Path("G:/SSA/noshowguard.db")
]

for db_path in db_paths:
    if not db_path.exists():
        continue
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cols = [c[1] for c in cur.execute("PRAGMA table_info(masters)").fetchall()]
        print(f"{db_path.name} masters columns before:", cols)
        
        if "trial_ends_at" not in cols:
            cur.execute("ALTER TABLE masters ADD COLUMN trial_ends_at TIMESTAMP")
        if "subscription_tier" not in cols:
            cur.execute("ALTER TABLE masters ADD COLUMN subscription_tier VARCHAR(20) DEFAULT 'trial'")
        if "subscription_active_until" not in cols:
            cur.execute("ALTER TABLE masters ADD COLUMN subscription_active_until TIMESTAMP")
        if "digest_enabled" not in cols:
            cur.execute("ALTER TABLE masters ADD COLUMN digest_enabled BOOLEAN DEFAULT 1")
        if "digest_time" not in cols:
            cur.execute("ALTER TABLE masters ADD COLUMN digest_time VARCHAR(5) DEFAULT '09:00'")
        
        b_cols = [c[1] for c in cur.execute("PRAGMA table_info(bookings)").fetchall()]
        if "terms_accepted" not in b_cols:
            cur.execute("ALTER TABLE bookings ADD COLUMN terms_accepted BOOLEAN DEFAULT 1")
        if "terms_accepted_at" not in b_cols:
            cur.execute("ALTER TABLE bookings ADD COLUMN terms_accepted_at TIMESTAMP")
            
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscription_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                master_id INTEGER NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
                amount INTEGER NOT NULL,
                tier VARCHAR(20) NOT NULL,
                payment_id VARCHAR(100),
                payment_status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        print(f"Successfully migrated {db_path}")
    except Exception as e:
        print(f"Error migrating {db_path}: {e}")

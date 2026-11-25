import sqlite3

DB_NAME = "aashi_cloud.db"

connection = sqlite3.connect(DB_NAME)

try:
    cursor = connection.cursor()

    for table in ["projects", "cloud_files"]:
        columns = [
            row[1]
            for row in cursor.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()
        ]

        if "user_id" not in columns:
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id)"
            )
            print(f"{table}: user_id column added")
        else:
            print(f"{table}: user_id already exists")

    connection.commit()
    print("Migration completed successfully.")

except Exception as error:
    connection.rollback()
    print("Migration failed:", error)

finally:
    connection.close()
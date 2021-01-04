from decouple import config
import psycopg2

DATABASE_URL = config('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL)

    cur = conn.cursor()
    cur.execute(
        """
            CREATE TABLE tweeted (
                pk integer PRIMARY KEY NOT NULL,
                updated timestamp DEFAULT current_timestamp
            )
        """
    )

    print("Table created successfully")

    cur.close()
    conn.commit()

except (Exception, psycopg2.DatabaseError) as error:
    print(error)

finally:
    if conn is not None:
        conn.close()

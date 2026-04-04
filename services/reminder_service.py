from db import get_db

def check_reminders():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        select id, url
        from inbox_links
        where reminder_at <= now()
        and reminder_at is not null
    """)

    rows = cur.fetchall()

    for r in rows:
        print("REMINDER:", r[1])

        cur.execute("""
            update inbox_links
            set reminder_at=null
            where id=%s
        """, (r[0],))

    conn.commit()
import json
import logging
from peewee import SqliteDatabase, Model, CharField, DateTimeField, TextField
import datetime
import os

db_path = os.path.join(os.path.dirname(__file__), "content_history.db")
db = SqliteDatabase(db_path)

class ContentLog(Model):
    date_posted = DateTimeField(default=datetime.datetime.now)
    title = CharField()
    fact_summary = TextField()
    
    class Meta:
        database = db

def init_db():
    db.connect(reuse_if_open=True)
    db.create_tables([ContentLog], safe=True)
    db.close()

def log_content(title: str, fact_summary: str):
    init_db()
    ContentLog.create(title=title, fact_summary=fact_summary)
    
def get_recent_topics(days: int = 30) -> str:
    """Returns a formatted string of recent topics to feed back to Gemini."""
    init_db()
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
    recent_logs = ContentLog.select().where(ContentLog.date_posted >= cutoff_date).order_by(ContentLog.date_posted.desc())
    
    topics = []
    for log in recent_logs:
        topics.append(log.title)
        
    if not topics:
        return "No recent videos yet."
        
    return ", ".join(topics)

if __name__ == "__main__":
    init_db()

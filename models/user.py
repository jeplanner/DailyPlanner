from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import supabase_client as db


class User(UserMixin):
    def __init__(self, data):
        self.id = data["id"]
        self.email = data["email"]
        self.display_name = data["display_name"]
        self.password_hash = data.get("password_hash", "")
        self.is_active_flag = data.get("is_active", True)
        self.created_at = data.get("created_at")

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self.is_active_flag

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get(user_id):
        rows = db.get("users", {"id": f"eq.{user_id}", "is_active": "eq.true"})
        if rows:
            return User(rows[0])
        return None

    @staticmethod
    def get_by_email(email):
        rows = db.get("users", {"email": f"eq.{email.lower().strip()}"})
        if rows:
            return User(rows[0])
        return None

    @staticmethod
    def create(email, display_name, password):
        password_hash = generate_password_hash(password)
        data = {
            "email": email.lower().strip(),
            "display_name": display_name.strip(),
            "password_hash": password_hash,
        }
        rows = db.post("users", data)
        if rows:
            return User(rows[0])
        return None

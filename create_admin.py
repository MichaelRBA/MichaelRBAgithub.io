from flask import Flask
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/your_database"  # Ganti dengan URI MongoDB Anda
mongo = PyMongo(app)

# Ganti dengan ID dan Password yang diinginkan
admin_username = "admin_user"  # Ganti dengan username admin yang diinginkan
admin_password = "admin"  # Ganti dengan password admin yang diinginkan

with app.app_context():
    # Hanya tambahkan admin jika belum ada
    if mongo.db.users.find_one({"username": admin_username}) is None:
        mongo.db.users.insert_one({
            "username": admin_username,
            "password": generate_password_hash(admin_password),  # Meng-hash password
            "role": "admin"
        })
        print("Admin telah ditambahkan.")
    else:
        print("Admin sudah ada.")

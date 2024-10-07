from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import os
from bson.objectid import ObjectId
from pdf2image import convert_from_path

def pdf_to_images(pdf_path):
    images = convert_from_path(pdf_path)
    image_paths = []
    
    for i, image in enumerate(images):
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{i + 1}.png")
        image.save(image_path, 'PNG')
        image_paths.append(image_path)
    
    return image_paths

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Ganti dengan kunci rahasia Anda

@app.route('/login', methods=['POST'])
def login():
    # Logika login
    session['role'] = 'admin'  # atau 'user' sesuai login
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')  # Template Anda di sini

# Konfigurasi MongoDB
app.config["MONGO_URI"] = "mongodb+srv://michaelrba:michaelrba@clusterzero.eyley3u.mongodb.net/Gereja?retryWrites=true&w=majority"
mongo = PyMongo(app)

# Folder untuk menyimpan warta jemaat
UPLOAD_FOLDER = 'static/uploads/warta/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Cek dan buat folder jika belum ada
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/view_image/<filename>')
def view_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/view_pdf/<filename>')
def view_pdf(filename):
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(pdf_path):
        # Convert PDF to images
        images = pdf_to_images(pdf_path)
        # Serve the first page image
        return send_from_directory(app.config['UPLOAD_FOLDER'], os.path.basename(images[0]))
    
    return "File not found", 404

# Rute untuk upload warta jemaat
@app.route('/upload_warta', methods=['GET', 'POST'])
def upload_warta():
    if 'role' in session and session['role'] == 'admin':
        if request.method == 'POST':
            warta_file = request.files['warta_file']
            if warta_file:
                try:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], warta_file.filename)
                    warta_file.save(file_path)

                    # Simpan informasi file ke MongoDB
                    mongo.db.warta.insert_one({
                        'filename': warta_file.filename,
                        'path': file_path
                    })
                    return redirect(url_for('admin_dashboard'))
                except Exception as e:
                    return f"Error saving file: {e}"

        return render_template('upload_warta.html')

    return redirect(url_for('admin_login'))

# Rute untuk mendownload warta jemaat
@app.route('/download_warta/<filename>')
def download_warta(filename):
    if 'role' in session and session['role'] == 'admin':
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    elif 'role' in session and session['role'] == 'user':
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    return redirect(url_for('user_login'))


# Pastikan Anda sudah meng-import ObjectId
from bson.objectid import ObjectId

@app.route('/view_warta', methods=['GET'])
def view_warta():
    if 'role' in session and session['role'] == 'user':
        # Retrieve uploaded warta files from the database
        warta_files = mongo.db.warta.find()
        return render_template('view_warta.html', role=session['role'], warta_files=warta_files)
    
    return redirect(url_for('user_login'))



# Rute untuk delete warta jemaat
@app.route('/delete_warta/<warta_id>')
def delete_warta(warta_id):
    if 'role' in session and session['role'] == 'admin':
        warta = mongo.db.warta.find_one({'_id': ObjectId(warta_id)})
        if warta:
            os.remove(warta['path'])  # Hapus file dari server
            mongo.db.warta.delete_one({'_id': ObjectId(warta_id)})  # Hapus dari database
        return redirect(url_for('view_warta'))
    return redirect(url_for('admin_login'))

@app.route('/create_admin', methods=['GET', 'POST'])
def create_admin():
    if request.method == 'POST':
        admin_username = request.form['username']
        admin_password = request.form['password']

        # Hanya tambahkan admin jika belum ada
        if mongo.db.users.find_one({"username": admin_username}) is None:
            mongo.db.users.insert_one({
                "username": admin_username,
                "password": generate_password_hash(admin_password),
                "role": "admin"
            })
            return "Admin telah ditambahkan."
        else:
            return "Admin sudah ada."

    return render_template('create_admin.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Cek apakah username sudah ada
        if mongo.db.users.find_one({"username": username}) is None:
            # Simpan user baru
            mongo.db.users.insert_one({
                "username": username,
                "password": generate_password_hash(password),
                "role": "user"  # Atur role default sebagai user
            })
            return redirect(url_for('user_login'))  # Redirect ke halaman login setelah pendaftaran berhasil
        else:
            return "Username sudah ada.", 400

    return render_template('register.html')  # Tampilkan form jika GET


# Rute login admin
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = mongo.db.users.find_one({'username': username, 'role': 'admin'})
        
        if admin and check_password_hash(admin['password'], password):
            session['username'] = username
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        else:
            return "Login failed", 401
            
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        profiles = mongo.db.profiles.find()
        warta_files = mongo.db.warta.find()  # Ambil warta jemaat
        return render_template('admin_dashboard.html', profiles=profiles, warta_files=warta_files)
    return redirect(url_for('admin_login'))


@app.route('/delete_profile/<profile_id>', methods=['POST'])
def delete_profile(profile_id):
    if 'role' in session and session['role'] == 'admin':
        mongo.db.profiles.delete_one({'_id': ObjectId(profile_id)})
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))


# Rute login user
@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = mongo.db.users.find_one({'username': username, 'role': 'user'})
        
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['role'] = 'user'
            return redirect(url_for('success'))
        else:
            return "Login failed", 401
            
    return render_template('user_login.html')

@app.route('/success')
def success():
    if 'username' in session:
        profile = mongo.db.profiles.find_one({"username": session['username']})  # Retrieve the profile for the logged-in user
        profile_name = profile['name'] if profile else "User"  # Default to "User" if no profile is found
        return render_template('success.html', profile_name=profile_name)
    return redirect(url_for('user_login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        birthdate = request.form['birthdate']
        photo = request.files['photo']

        # Check if the user already has a profile
        existing_profile = mongo.db.profiles.find_one({"username": session['username']})
        if existing_profile:
            return "You already have a profile. Please edit your existing profile.", 400

        # Save photo to disk
        photo_path = os.path.join('static/uploads', photo.filename)
        photo.save(photo_path)

        # Save new profile to MongoDB
        mongo.db.profiles.insert_one({
            'username': session['username'],
            'name': name,
            'age': age,
            'birthdate': birthdate,
            'photo': photo_path
        })
        
        return redirect(url_for('view_profile'))

    return render_template('profile.html')


@app.route('/view_profile')
def view_profile():
    if 'username' in session:
        profile = mongo.db.profiles.find_one({"username": session['username']})  # Get profile by username
        if profile:
            profile['_id'] = str(profile['_id'])  # Convert ObjectId to string
            return render_template('view_profile.html', profiles=[profile])  # Pass the single profile as a list for consistency
        else:
            return "Profile not found.", 404
    return redirect(url_for('user_login'))

@app.route('/view_church_info')
def view_church_info():
    church_info = mongo.db.church_info.find_one()  # Retrieve church information from MongoDB
    activities = list(mongo.db.activities.find())  # Convert cursor to list
    return render_template('view_church_info.html', church_info=church_info, activities=activities)
    

@app.route('/update_church_info', methods=['GET', 'POST'])
def update_church_info():
    if 'role' in session and session['role'] == 'admin':
        if request.method == 'POST':
            church_info = {
                'name': request.form['name'],
                'address': request.form['address'],
                'phone': request.form['phone'],
                'email': request.form['email'],
                'description': request.form['description'],
            }
            # Upsert church info into the database
            mongo.db.church_info.update_one({}, {'$set': church_info}, upsert=True)
            return redirect(url_for('admin_dashboard'))  # Redirect to dashboard after saving

        return render_template('update_church_info.html')

    return redirect(url_for('admin_login'))


@app.route('/add_activity', methods=['POST'])
def add_activity():
    activity_name = request.form['activity_name']
    activity_date = request.form['activity_date']
    activity_description = request.form['activity_description']
    
    # Insert the new activity into the database
    activities_collection.insert_one({
        'name': activity_name,
        'date': activity_date,
        'description': activity_description
    })
    
    return redirect(url_for('view_church_info'))  # Redirect back to the church info page


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        return redirect(url_for('user_login'))

    profile = mongo.db.profiles.find_one({"username": session['username']})

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        birthdate = request.form['birthdate']
        photo = request.files['photo']
        
        if photo:
            photo_path = os.path.join('static/uploads', photo.filename)
            photo.save(photo_path)
        else:
            photo_path = profile['photo']

        mongo.db.profiles.update_one(
            {'username': session['username']},
            {'$set': {
                'name': name,
                'age': age,
                'birthdate': birthdate,
                'photo': photo_path
            }}
        )

        return redirect(url_for('view_profile'))

    if profile:
        profile['_id'] = str(profile['_id'])
        return render_template('edit_profile.html', profile=profile)

    return "Profile not found.", 404



@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('user_login'))

if __name__ == '__main__':
    app.run(debug=True)

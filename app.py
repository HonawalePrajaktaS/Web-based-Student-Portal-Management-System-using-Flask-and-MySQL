
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from config import Config
import hashlib

app = Flask(__name__)
app.secret_key = 'Prajakta'


# Database connection setup
db = mysql.connector.connect(
    host=Config.MYSQL_HOST,
    user=Config.MYSQL_USER,
    password=Config.MYSQL_PASSWORD,
    database=Config.MYSQL_DB
)
cursor = db.cursor()

@app.route('/')
def index():
    return "Welcome to the Student Portal!"

import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads'  # Folder to save uploaded files
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        # Handle file upload
        photo = request.files.get('photo')
        photo_url = None
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_url = f'uploads/{filename}'


        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        try:
            cursor = db.cursor()
            cursor.execute("INSERT INTO students (username, password, email, photo_url) VALUES (%s, %s, %s, %s)",
                           (username, hashed_password, email, photo_url))
            db.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError as e:
            db.rollback()
            flash('Username or email already exists.', 'error')
        except Exception as e:
            db.rollback()
            flash(f'An error occurred: {e}', 'error')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Hash the input password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM students WHERE username = %s AND password = %s",
                           (username, hashed_password))
            user = cursor.fetchone()

            cursor.close()

            if user:
                session['user_id'] = user['id']
                flash('Login successful!', 'success')
                return redirect(url_for('profile'))
            else:
                flash('Invalid credentials.', 'error')
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')

    return render_template('login.html')



@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    
    if not user_id:
        flash('You must be logged in to view your profile.', 'error')
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE id = %s", (user_id,))
    student = cursor.fetchone()
    
    if student:
        cursor.execute("SELECT course FROM enrollments WHERE user_id = %s", (user_id,))
        courses = cursor.fetchall()
        student['courses'] = [course['course'] for course in courses]
        return render_template('profile.html', student=student)
    else:
        flash('Student not found.', 'error')
        return redirect(url_for('login'))


@app.route('/enroll', methods=['GET', 'POST'])
def enroll():
    if request.method == 'POST':
        course = request.form.get('course')
        
        user_id = session.get('user_id')
        
        if user_id:
            try:
                cursor = db.cursor()
                cursor.execute("INSERT INTO enrollments (user_id, course) VALUES (%s, %s)", 
                               (user_id, course))
                db.commit()
                cursor.close()
                flash('Enrollment successful!', 'success')
                return redirect(url_for('profile'))
            except Exception as e:
                db.rollback()
                flash(f'An error occurred: {e}', 'error')
        else:
            flash('You must be logged in to enroll.', 'error')

    return render_template('enroll.html')



@app.route('/grades')
def grades():
    user_id = session.get('user_id')

    if not user_id:
        flash('You must be logged in to view your grades.', 'error')
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT subject, marks 
        FROM marks 
        WHERE student_id = %s
    """, (user_id,))
    marks = cursor.fetchall()

    return render_template('grades.html', marks=marks)


@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove user_id from session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)


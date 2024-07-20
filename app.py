from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, session, flash
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from collections import defaultdict
from src.video_stream import VideoCamera
from datetime import datetime, timedelta
import dateutil.parser
import os
from models import db, User, HistoricalData

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
db.init_app(app)

migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

CORS(app)
video_camera = VideoCamera()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class HistoricalDataManager:
    def __init__(self):
        self.data = []

    def append(self, item):
        self.data.append(item)

    def get_all(self):
        return self.data

historical_manager = HistoricalDataManager()

class EmotionData:
    def __init__(self):
        self.user_data = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'total_intensity': 0}))

    def update(self, user_id, emotions):
        for emotion in emotions:
            self.user_data[user_id][emotion['emotion']]['count'] += 1
            self.user_data[user_id][emotion['emotion']]['total_intensity'] += emotion['probability']

    def get_stats(self, user_id):
        return {
            emotion: {
                'count': details['count'],
                'average_intensity': (details['total_intensity'] / details['count']) if details['count'] > 0 else 0
            }
            for emotion, details in self.user_data[user_id].items()
        }

    def reset_stats(self, user_id):
        self.user_data[user_id] = defaultdict(lambda: {'count': 0, 'total_intensity': 0})

    def save_current_stats(self, user_id):
        timestamp = datetime.now().isoformat()
        emotions_stats = {
            emotion: {
                'count': details['count'],
                'average_intensity': (details['total_intensity'] / details['count']) if details['count'] > 0 else 0
            }
            for emotion, details in self.user_data[user_id].items()
        }
        snapshot = {'timestamp': timestamp, **emotions_stats}
        historical_manager.append(snapshot)

        if current_user.is_authenticated:
            new_data = HistoricalData(
                user_id=user_id,
                timestamp=datetime.now(),
                angry=emotions_stats.get('Angry', {}).get('average_intensity', 0),
                disgust=emotions_stats.get('Disgust', {}).get('average_intensity', 0),
                fear=emotions_stats.get('Fear', {}).get('average_intensity', 0),
                happy=emotions_stats.get('Happy', {}).get('average_intensity', 0),
                neutral=emotions_stats.get('Neutral', {}).get('average_intensity', 0),
                sad=emotions_stats.get('Sad', {}).get('average_intensity', 0),
                surprise=emotions_stats.get('Surprise', {}).get('average_intensity', 0)
            )
            db.session.add(new_data)
            db.session.commit()

        return snapshot

emotion_data = EmotionData()

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    user_id = current_user.id
    emotion_data.reset_stats(user_id)
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        password = request.form['password']
        retype_password = request.form['retype_password']

        if password != retype_password:
            flash('Passwords do not match. Please try again.', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, first_name=first_name, last_name=last_name, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')

@app.route('/profile_settings', methods=['GET', 'POST'])
@login_required
def profile_settings():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        current_password = request.form.get('current_password')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        profile_picture = request.files.get('profile_picture')

        user = current_user

        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name

        if new_password:
            if check_password_hash(user.password, current_password):
                if new_password == confirm_password:
                    user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
                else:
                    flash('New passwords do not match.', 'error')
                    return redirect(url_for('profile_settings'))
            else:
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('profile_settings'))

        if profile_picture:
            filename = secure_filename(profile_picture.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_picture.save(filepath)
            user.profile_picture = 'uploads/' + filename

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile_settings'))

    return render_template('profile.html')

@app.route('/live_feed')
@login_required
def live_feed():
    return render_template('live_feed.html')

@app.route('/start_video')
@login_required
def start_video():
    video_camera.start_camera()
    return "Camera started"

@app.route('/stop_video')
@login_required
def stop_video():
    video_camera.stop_camera()
    return "Camera stopped"

@app.route('/switch_camera', methods=['POST'])
@login_required
def switch_camera():
    camera_index = int(request.json.get('cameraIndex', 0))
    video_camera.switch_camera(camera_index)
    return jsonify({"status": "Camera switched to index {}".format(camera_index)})

@app.route('/video_feed')
@login_required
def video_feed():
    return Response(gen(video_camera), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/emotion_stats')
@login_required
def emotion_stats():
    user_id = current_user.id
    emotions = video_camera.latest_emotions
    emotion_data.update(user_id, emotions)
    return jsonify(emotion_data.get_stats(user_id))

@app.route('/save_emotion_stats', methods=['POST'])
@login_required
def save_emotion_stats():
    user_id = current_user.id
    return jsonify(emotion_data.save_current_stats(user_id))

@app.route('/reset_emotion_stats', methods=['POST'])
@login_required
def reset_emotion_stats():
    user_id = current_user.id
    emotion_data.reset_stats(user_id)
    return jsonify({"status": "Emotion stats have been reset"})

@app.route('/historical_data')
@login_required
def historical_data():
    return render_template('historical_data.html')

@app.route('/get_historical_data')
@login_required
def get_historical_data():
    date_range = request.args.get('dateRange')
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')
    
    if date_range:
        end_date = datetime.now()
        if date_range == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == 'yesterday':
            end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = end_date - timedelta(days=1)
        elif date_range == 'last7days':
            start_date = end_date - timedelta(days=7)
        elif date_range == 'last30days':
            start_date = end_date - timedelta(days=30)
        elif date_range == 'thismonth':
            start_date = end_date.replace(day=1)
        elif date_range == 'lastmonth':
            start_date = (end_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    elif start_date and end_date:
        start_date = dateutil.parser.parse(start_date)
        end_date = dateutil.parser.parse(end_date)
    else:
        return jsonify([])  # No data if date range is not specified
    
    filtered_data = HistoricalData.query.filter(
        HistoricalData.user_id == current_user.id,
        HistoricalData.timestamp >= start_date,
        HistoricalData.timestamp <= end_date
    ).all()

    result = [{
        'timestamp': data.timestamp.isoformat(),
        'Angry': {'average_intensity': data.angry},
        'Disgust': {'average_intensity': data.disgust},
        'Fear': {'average_intensity': data.fear},
        'Happy': {'average_intensity': data.happy},
        'Neutral': {'average_intensity': data.neutral},
        'Sad': {'average_intensity': data.sad},
        'Surprise': {'average_intensity': data.surprise}
    } for data in filtered_data]
    
    return jsonify(result)

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/help')
def help():
    return render_template('help.html')

def gen(camera):
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

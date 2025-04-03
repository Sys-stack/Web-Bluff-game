from flask import Flask, request, redirect, url_for, render_template_string, make_response, jsonify
import requests
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from supabase import create_client, Client
import os
import uuid
import secrets
import logging
from werkzeug.security import generate_password_hash, check_password_hash
import eventlet
import eventlet.wsgi

# ------------------------
# Configuration and Setup
# ------------------------
class Config:
    """Configuration settings for the application"""
    SUPABASE_URL = os.environ.get("supabase_url")
    SUPABASE_KEY = os.environ.get("supabase_api")
    SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(24))
    MAX_PLAYERS = 4
    COOKIE_MAX_AGE = 60 * 60 * 24  # 24 hours
    PORT = int(os.environ.get("PORT", 5000))
    
# ------------------------
# Helper Functions
# ------------------------
def generate_unique_id():
    """Generate a unique ID using UUID4"""
    return str(uuid.uuid4())[:8]  # Using first 8 chars of UUID for readability

def get_template(url):
    """Fetch template from URL with error handling"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logging.error(f"Failed to load template: {str(e)}")
        return None

def validate_input(text, min_length=1, max_length=50):
    """Basic input validation"""
    if not text or not isinstance(text, str):
        return False
    if len(text) < min_length or len(text) > max_length:
        return False
    return True

# ------------------------
# Database Operations
# ------------------------
class DatabaseOperations:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    def create_room(self, room_id, room_name, password):
        """Create a new room in the database"""
        try:
            self.supabase.table("rooms").insert({
                "id": room_id,
                "password": generate_password_hash(password),
                "name": room_name
            }).execute()
            return True
        except Exception as e:
            logging.error(f"Error creating room: {str(e)}")
            return False
    
    def add_user_to_room(self, user_id, username, color, room_name):
        """Add a user to a room"""
        try:
            self.supabase.table("userinfo").insert({
                "ip": user_id,
                "username": username,
                "color": color,
                "roomname": room_name
            }).execute()
            return True
        except Exception as e:
            logging.error(f"Error adding user to room: {str(e)}")
            return False
    
    def check_room_exists(self, room_name):
        """Check if a room with the given name exists"""
        try:
            response = self.supabase.table("rooms").select("*").eq("name", room_name).execute()
            return len(response.data) > 0, response.data
        except Exception as e:
            logging.error(f"Error checking room existence: {str(e)}")
            return False, None
    
    def check_password(self, room_name, password):
        """Verify room password"""
        try:
            response = self.supabase.table("rooms").select("password").eq("name", room_name).single().execute()
            if not response.data:
                return False
            stored_hash = response.data.get("password")
            return check_password_hash(stored_hash, password)
        except Exception as e:
            logging.error(f"Error checking password: {str(e)}")
            return False
    
    def get_room_users(self, room_name):
        """Get users in a room"""
        try:
            response = self.supabase.table("userinfo").select("username").eq("roomname", room_name).execute()
            return [user["username"] for user in response.data] if response.data else []
        except Exception as e:
            logging.error(f"Error getting room users: {str(e)}")
            return []
    
    def check_user_in_room(self, user_id, room_name):
        """Check if a user is in a specific room"""
        try:
            response = self.supabase.table("userinfo").select("*").eq("ip", user_id).eq("roomname", room_name).execute()
            return len(response.data) > 0
        except Exception as e:
            logging.error(f"Error checking user in room: {str(e)}")
            return False
    
    def remove_user(self, user_id):
        """Remove a user from all rooms"""
        try:
            # Get user's room before deleting
            user_info = self.supabase.table("userinfo").select("roomname").eq("ip", user_id).single().execute()
            room_name = user_info.data.get("roomname") if user_info.data else None
            
            # Delete user
            self.supabase.table("userinfo").delete().eq("ip", user_id).execute()
            
            # Check if room is empty and delete if so
            if room_name:
                remaining = self.get_room_users(room_name)
                if len(remaining) == 0:
                    self.supabase.table("rooms").delete().eq("name", room_name).execute()
            
            return True, room_name
        except Exception as e:
            logging.error(f"Error removing user: {str(e)}")
            return False, None

# ------------------------
# Application Initialization
# ------------------------
def create_app():
    """Initialize and configure the Flask application"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize Supabase client
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        logging.warning("Supabase credentials are missing. Using dummy values for development.")
        supabase_url = "https://dummy.supabase.co"
        supabase_key = "dummy_key"
    else:
        supabase_url = Config.SUPABASE_URL
        supabase_key = Config.SUPABASE_KEY
    
    supabase = create_client(supabase_url, supabase_key)
    db = DatabaseOperations(supabase)
    
    # Initialize SocketIO
    socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*", ping_interval=25)
    
    return app, socketio, db

app, socketio, db = create_app()

# ------------------------
# Routes
# ------------------------
@app.route("/", methods=["GET", "POST"])
def home():
    """Home page route"""
    action = request.form.get("action")
    if action == "play":
        return redirect(url_for("rooms"))
    elif action == "about":
        return redirect(url_for("credits"))
    
    template = get_template("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/Bluff.html")
    if template:
        return template
    return "Failed to load home page. Please try again later.", 500

@app.route("/credits")
def credits():
    """Credits page"""
    return "<h2>Game Credits Page</h2>"

@app.route("/rooms", methods=["POST", "GET"])
def rooms():
    """Rooms selection page"""
    room_action = request.form.get("action")
    if room_action == "newroom":
        return redirect(url_for("newroom"))
    elif room_action == "oldroom":
        return redirect(url_for("oldroom"))

    username = request.form.get("username", "Username")
    color = request.form.get("color", "#ffffff")

    template = get_template("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/rooms.html")
    if not template:
        return "Failed to load rooms page. Please try again later.", 500
    
    # Create response with the template
    resp = make_response(render_template_string(template, username=username))
    
    # Set cookies only if username is not the default and is valid
    if username != "Username" and validate_input(username, max_length=30):
        resp.set_cookie("username", username, max_age=Config.COOKIE_MAX_AGE, httponly=True, samesite='Lax')
        resp.set_cookie("color", color, max_age=Config.COOKIE_MAX_AGE, httponly=True, samesite='Lax')
    
    return resp

@app.route("/newroom", methods=["GET", "POST"])
def newroom():
    """Create new room page"""
    username = request.cookies.get("username")
    color = request.cookies.get("color")
    password = request.form.get("password")
    room_name = request.form.get("roomname")
    
    # Check if the username and color are set
    if not username:
        return redirect(url_for("rooms"))
    
    # Process form submission
    if request.method == "POST" and room_name and password:
        # Input validation
        if not validate_input(room_name, max_length=30) or not validate_input(password, min_length=4):
            return "Invalid room name or password. Room name must be 1-30 characters and password at least 4 characters.", 400
        
        # Check if room exists
        exists, _ = db.check_room_exists(room_name)
        if exists:
            return "Room name already exists. Please choose another name.", 400
        
        # Generate user ID and create room
        user_id = generate_unique_id()
        if not db.create_room(user_id, room_name, password):
            return "Error creating room. Please try again.", 500
        
        # Add user to room
        if not db.add_user_to_room(user_id, username, color, room_name):
            return "Error adding user to room. Please try again.", 500
        
        # Redirect to lobby with cookie
        resp = make_response(redirect(url_for("lobby", roomname=room_name)))
        resp.set_cookie("user_id", user_id, max_age=Config.COOKIE_MAX_AGE, httponly=True, samesite='Lax')
        return resp
    
    # Display new room form
    template = get_template("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/newroom.html")
    if template:
        return render_template_string(template, password=password, roomname=room_name)
    return "Failed to load new room page. Please try again later.", 500

@app.route("/room/<roomname>", methods=["POST", "GET"])
def lobby(roomname):
    """Game lobby for a specific room"""
    user_id = request.cookies.get("user_id")
    if not user_id:
        return redirect(url_for("rooms"))
    
    # Input validation
    if not validate_input(roomname):
        return "Invalid room name", 400
    
    # Check if room exists
    exists, room_data = db.check_room_exists(roomname)
    if not exists:
        return "Room not found", 404
    
    # Check if user is part of this room
    if not db.check_user_in_room(user_id, roomname):
        return "You don't have access to this room", 403
    
    # Get room details
    room_password = room_data[0].get("password") if room_data else ""
    usernames = db.get_room_users(roomname)
    
    # Limit to max players and fill remaining slots with "None"
    usernames = usernames[:Config.MAX_PLAYERS]
    while len(usernames) < Config.MAX_PLAYERS:
        usernames.append("None")
    
    # Render lobby template - use local file if it exists, otherwise fetch from CDN
    template = get_template("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/main/lobby.html")
    if not template:
        return "Failed to load lobby. Please try again later.", 500
    
    return render_template_string(
        template, 
        roomname=roomname, 
        password="********",  # Don't expose password hash
        p1=usernames[0],
        p2=usernames[1],
        p3=usernames[2],
        p4=usernames[3]
    )

@app.route("/oldroom", methods=["GET", "POST"])
def oldroom():
    """Join existing room page"""
    username = request.cookies.get("username")
    color = request.cookies.get("color")
    if not username or not color:
        return redirect(url_for("rooms"))
    
    room_name = request.form.get("roomname")
    password = request.form.get("password")
    
    if request.method == "POST" and room_name and password:
        # Input validation
        if not validate_input(room_name) or not validate_input(password):
            return "Invalid room name or password", 400
        
        # Check if room exists and password matches
        exists, _ = db.check_room_exists(room_name)
        if not exists or not db.check_password(room_name, password):
            return "Invalid room name or password", 400
        
        # Check if room is full
        users = db.get_room_users(room_name)
        if len(users) >= Config.MAX_PLAYERS:
            return "Room is full", 400
        
        # Generate user ID and add to room
        user_id = generate_unique_id()
        if not db.add_user_to_room(user_id, username, color, room_name):
            return "Error joining room. Please try again.", 500
        
        # Redirect to lobby
        resp = make_response(redirect(url_for("lobby", roomname=room_name)))
        resp.set_cookie("user_id", user_id, max_age=Config.COOKIE_MAX_AGE, httponly=True, samesite='Lax')
        return resp
    
    # Display join room form
    template = get_template("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/oldroom.html")
    if template:
        return render_template_string(template)
    return "Failed to load join room page. Please try again later.", 500

@app.route("/leave_room")
def leave_room_route():
    """Leave current room"""
    user_id = request.cookies.get("user_id")
    if user_id:
        success, _ = db.remove_user(user_id)
        
        resp = make_response(redirect(url_for("rooms")))
        resp.delete_cookie("user_id")
        return resp
    
    return redirect(url_for("rooms"))

@app.route("/play", methods=["POST"])
def play_game():
    """Start the game"""
    user_id = request.cookies.get("user_id")
    room_name = request.form.get("roomname")
    
    if not user_id or not room_name:
        return redirect(url_for("rooms"))
    
    # Check if user is in the specified room
    if not db.check_user_in_room(user_id, room_name):
        return redirect(url_for("rooms"))
    
    # Here you would redirect to the actual game page
    # For now, we'll just redirect back to the lobby
    return redirect(url_for("lobby", roomname=room_name))
    
# ------------------------
# Socket Event Handlers
# ------------------------
@socketio.on('connect')
def handle_connect():
    """Handle socket connection"""
    username = request.cookies.get("username")
    user_id = request.cookies.get("user_id")

    logging.info(f"{username if username else 'Unknown user'} with ID of {user_id if user_id else 'unknown'} has connected")
    data = {"username": username, "user_id": user_id}
    
    emit("connect_response", data, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle socket disconnection"""
    username = request.cookies.get("username")
    user_id = request.cookies.get("user_id")

    if user_id:
        success, room_name = db.remove_user(user_id)
        if success and room_name:
            leave_room(room_name)
            # Broadcast updated players list to the room
            emit_player_update(room_name)

    logging.info(f"{username if username else 'Unknown user'} with ID of {user_id if user_id else 'unknown'} has disconnected")
    data = {"username": username, "user_id": user_id}
    
    emit("disconnect_response", data, broadcast=True)

@socketio.on('join')
def handle_join(data):
    """Handle room joining"""
    room_name = data.get('room')
    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")
    
    if not room_name or not user_id:
        return
    
    # Verify user belongs to the room
    if not db.check_user_in_room(user_id, room_name):
        return
    
    # Join the Flask-SocketIO room
    join_room(room_name)
    logging.info(f"{username} joined room {room_name}")
    
    # Send updated players list to all clients in the room
    emit_player_update(room_name)

@socketio.on('get_players')
def handle_get_players(data):
    """Get the list of players in a room"""
    room_name = data.get('room')
    if not room_name:
        return
    
    emit_player_update(room_name)

@socketio.on('start_game')
def handle_start_game(data):
    """Handle game start"""
    room_name = data.get('room')
    user_id = request.cookies.get("user_id")
    
    if not room_name or not user_id:
        return
    
    # Verify user belongs to the room
    if not db.check_user_in_room(user_id, room_name):
        return
    
    # Get current players
    players = db.get_room_users(room_name)
    
    # Verify enough players to start
    if len(players) < 2:
        emit('game_error', {'message': 'Need at least 2 players to start'}, room=request.sid)
        return
    
    # Emit game start event to all players in the room
    emit('game_start', {'players': players}, room=room_name)

def emit_player_update(room_name):
    """Helper function to emit updated player list to a room"""
    players = db.get_room_users(room_name)
    while len(players) < Config.MAX_PLAYERS:
        players.append("None")
    
    emit('player_update', {'players': players}, room=room_name)

# ------------------------
# Main Application Entry
# ------------------------
if __name__ == '__main__':
    # Start the app with eventlet
    socketio.run(app, host='0.0.0.0', port=Config.PORT)

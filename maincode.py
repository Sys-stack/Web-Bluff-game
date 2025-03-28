from flask import Flask, request, redirect, url_for, render_template_string, make_response, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import requests
from supabase import create_client, Client
import os

# ------------------------
# SUPABASE SETUP
# ------------------------

url = os.environ.get("supabase_url")
key = os.environ.get("supabase_api")

if not url or not key:
    raise Exception("Supabase URL or API key not set in environment variables.")

supabase: Client = create_client(url, key)

# ------------------------
# FLASK APP INITIALIZATION
# ------------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Add a secret key for security
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')  # Specify async_mode

# Dictionary to track active rooms and users for quick access
active_rooms = {}

# ------------------------
# ROUTES
# ------------------------

@app.route("/", methods=["GET", "POST"])
def home():
    action = request.form.get("action")
    if action == "play":
        return redirect(url_for("rooms"))
    elif action == "about":
        return redirect(url_for("credits"))

    html = requests.get("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/Bluff.html").text
    return html

@app.route("/credits")
def credits():
    return "<h2>Game Credits Page</h2>"

@app.route("/rooms", methods=["POST", "GET"])
def rooms():
    roomaction = request.form.get("action")

    if roomaction == "newroom":
        return redirect(url_for("newroom"))
    elif roomaction == "oldroom":
        return redirect(url_for("oldroom"))

    username = request.form.get("username")
    color = request.form.get("color")

    html = requests.get("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/rooms.html").text

    if username:
        resp = make_response(html)
        resp.set_cookie("username", username, max_age=60 * 60 * 24)
        resp.set_cookie("color", color or "#ffffff", max_age=60 * 60 * 24)
        return resp

    return html

@app.route("/newroom", methods=["GET", "POST"])
def newroom():
    username = request.cookies.get("username")
    color = request.cookies.get("color")
    password = request.form.get("password")
    roomname = request.form.get("roomname")
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    if not username:
        return "Please set your profile before creating a room.", 400

    supabase.table('rooms').upsert({
        "id": user_ip,
        "password": password,
        "name": roomname
    }, on_conflict=["id"]).execute()

    supabase.table('userinfo').upsert({
        "ip": user_ip,
        "username": username,
        "color": color,
        "roomname": roomname
    }, on_conflict=["ip"]).execute()

    if password and roomname:
        return redirect(url_for("lobby", roomname=roomname))

    newroom_github_html = "https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/newroom.html"
    page = requests.get(newroom_github_html)
    return render_template_string(page.text, password=password, roomname=roomname)

@app.route("/room/<roomname>")
def lobby(roomname):
    response = supabase.table("rooms").select("password").eq("name", roomname).single().execute()
    if not response.data:
        return "Room not found", 404

    room_password = response.data["password"]
    user_response = supabase.table("userinfo").select("username").eq("roomname", roomname).execute()
    usernames = [user["username"] for user in user_response.data] if user_response.data else []

    # Update active_rooms dictionary for quick access during WebSocket operations
    active_rooms[roomname] = usernames[:4]  # Limit to 4 players

    html = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@main/lobby.html").text

    # Fill player slots with current users or "None"
    return render_template_string(html, roomname=roomname, password=room_password,
                                  p1=usernames[0] if len(usernames) > 0 else "None",
                                  p2=usernames[1] if len(usernames) > 1 else "None",
                                  p3=usernames[2] if len(usernames) > 2 else "None",
                                  p4=usernames[3] if len(usernames) > 3 else "None")

# Add an API endpoint to get updated player lists
@app.route("/api/room/<roomname>/players")
def get_room_players(roomname):
    user_response = supabase.table("userinfo").select("username").eq("roomname", roomname).execute()
    usernames = [user["username"] for user in user_response.data] if user_response.data else []
    
    # Ensure we have 4 slots, filling with None as needed
    players = {
        "p1": usernames[0] if len(usernames) > 0 else "None",
        "p2": usernames[1] if len(usernames) > 1 else "None",
        "p3": usernames[2] if len(usernames) > 2 else "None",
        "p4": usernames[3] if len(usernames) > 3 else "None"
    }
    
    return jsonify(players)

@app.route("/oldroom", methods=["GET", "POST"])
def oldroom():
    username = request.cookies.get("username")
    color = request.cookies.get("color")
    if not username or not color:
        return redirect(url_for("rooms"))

    roomname = request.form.get("roomname")
    password = request.form.get("password")
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    if roomname and password:
        room_data = supabase.table('rooms').select("*").eq("name", roomname).execute()
        if room_data.data:
            stored_password = room_data.data[0]['password']
            if password == stored_password:
                supabase.table('userinfo').upsert({
                    "ip": user_ip,
                    "username": username,
                    "color": color,
                    "roomname": roomname
                }, on_conflict=["ip"]).execute()
                return redirect(url_for("lobby", roomname=roomname))

    page = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/oldroom.html").text
    return render_template_string(page)

@app.route("/user-left", methods=["POST"])
def user_left():
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_entry = supabase.table("userinfo").select("roomname, username").eq("ip", user_ip).single().execute()

    if not user_entry.data:
        return "User not found", 404

    roomname = user_entry.data["roomname"]
    username = user_entry.data["username"]
    
    supabase.table("userinfo").delete().eq("ip", user_ip).execute()

    # Update the active_rooms dictionary
    if roomname in active_rooms and username in active_rooms[roomname]:
        active_rooms[roomname].remove(username)

    remaining = supabase.table("userinfo").select("ip").eq("roomname", roomname).execute()
    if not remaining.data:
        supabase.table("rooms").delete().eq("name", roomname).execute()
        if roomname in active_rooms:
            del active_rooms[roomname]

    # Get fresh user data from the database
    user_response = supabase.table("userinfo").select("username").eq("roomname", roomname).execute()
    usernames = [user["username"] for user in user_response.data] if user_response.data else []
    
    # Format player list in the way the client expects
    players = {
        "p1": usernames[0] if len(usernames) > 0 else "None",
        "p2": usernames[1] if len(usernames) > 1 else "None",
        "p3": usernames[2] if len(usernames) > 2 else "None",
        "p4": usernames[3] if len(usernames) > 3 else "None"
    }
    
    # Broadcast the updated user list to all clients in the room
    socketio.emit('update_players', players, room=roomname)

    return "User and possibly empty room removed", 200

# ------------------------
# SOCKET.IO EVENTS
# ------------------------

@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('join')
def handle_join(data):
    username = data.get('username')
    roomname = data.get('room')
    
    if not username or not roomname:
        return
    
    join_room(roomname)
    print(f"User {username} joined room: {roomname}")
    
    # Query the database for the current list of users in the room
    user_response = supabase.table("userinfo").select("username").eq("roomname", roomname).execute()
    usernames = [user["username"] for user in user_response.data] if user_response.data else []
    
    # Update the active_rooms dictionary
    active_rooms[roomname] = usernames[:4]
    
    # Format player list in the way the client expects
    players = {
        "p1": usernames[0] if len(usernames) > 0 else "None",
        "p2": usernames[1] if len(usernames) > 1 else "None",
        "p3": usernames[2] if len(usernames) > 2 else "None",
        "p4": usernames[3] if len(usernames) > 3 else "None"
    }
    
    # Broadcast the updated user list to all clients in the room
    emit('update_players', players, room=roomname)

@socketio.on('leave')
def handle_leave(data):
    roomname = data.get('room')
    username = data.get('username')
    
    if not username or not roomname:
        return
    
    leave_room(roomname)
    print(f"User {username} left room: {roomname}")

    # Update the database
    user_entry = supabase.table("userinfo").select("ip").eq("username", username).eq("roomname", roomname).execute()
    if user_entry.data:
        supabase.table("userinfo").delete().eq("ip", user_entry.data[0]["ip"]).execute()
    
    # Update the active_rooms dictionary
    if roomname in active_rooms and username in active_rooms[roomname]:
        active_rooms[roomname].remove(username)
    
    # Check if the room is now empty
    remaining = supabase.table("userinfo").select("ip").eq("roomname", roomname).execute()
    if not remaining.data:
        supabase.table("rooms").delete().eq("name", roomname).execute()
        if roomname in active_rooms:
            del active_rooms[roomname]
    
    # Get the updated list of users
    updated = supabase.table("userinfo").select("username").eq("roomname", roomname).execute()
    usernames = [user["username"] for user in updated.data] if updated.data else []
    
    # Format player list in the way the client expects
    players = {
        "p1": usernames[0] if len(usernames) > 0 else "None",
        "p2": usernames[1] if len(usernames) > 1 else "None",
        "p3": usernames[2] if len(usernames) > 2 else "None",
        "p4": usernames[3] if len(usernames) > 3 else "None"
    }
    
    # Broadcast the updated player list to all clients in the room
    emit('update_players', players, room=roomname)

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

# ------------------------
# RUN THE SERVER
# ------------------------

# Only run when executing directly
if __name__ == "__main__":
    import eventlet
    import eventlet.wsgi
    eventlet.monkey_patch()
    
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

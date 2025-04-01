from flask import Flask, request, redirect, url_for, render_template_string, make_response, jsonify
import requests
from flask_socketio import SocketIO, send, emit
from supabase import create_client, Client
import os
import random
import string
import uuid
import eventlet
import eventlet.wsgi
# ------------------------
# Helper Function: Generate Unique ID
# ------------------------
def generate_unique_id():
    """Generate a unique ID using UUID4 (more collision-resistant than 4 characters)"""
    return str(uuid.uuid4())[:8]  # Using first 8 chars of UUID for readability

# ------------------------
# Supabase Setup
# ------------------------
url = os.environ.get("supabase_url")
key = os.environ.get("supabase_api")

if not url or not key:
    raise ValueError("Supabase credentials are missing. Set 'supabase_url' and 'supabase_api' in environment variables.")

supabase: Client = create_client(url, key)

# ------------------------
# Flask App Initialization
# ------------------------
app = Flask(__name__)
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*", ping_interval=25)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24))  # Added secret key


# ------------------------
# Routes
# ------------------------

@app.route("/", methods=["GET", "POST"])
def home():
    action = request.form.get("action")
    if action == "play":
        return redirect(url_for("rooms"))
    elif action == "about":
        return redirect(url_for("credits"))
    
    try:
        response = requests.get("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/Bluff.html")
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.text
    except requests.RequestException as e:
        return f"Failed to load home page: {str(e)}", 500

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

    username = request.form.get("username", "Username")
    color = request.form.get("color", "#ffffff")

    try:
        # Fetch the HTML page
        response = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/rooms.html")
        response.raise_for_status()
        
        # Create response object with the fetched HTML
        resp = make_response(render_template_string(response.text, username=username))
        
        # Set cookies only if username is not the default
        if username != "Username":
            resp.set_cookie("username", username, max_age=60 * 60 * 24, httponly=True)
            resp.set_cookie("color", color, max_age=60 * 60 * 24, httponly=True)
        
        return resp
    except requests.RequestException as e:
        return f"Failed to load rooms page: {str(e)}", 500

@app.route("/newroom", methods=["GET", "POST"])
def newroom():
    username = request.cookies.get("username")
    color = request.cookies.get("color")
    password = request.form.get("password")
    roomname = request.form.get("roomname")
    
    # Check if the username and color are set
    if not username:
        return redirect(url_for("rooms"))
    
    # Generate a unique user ID
    user_id = generate_unique_id()
    
    # If form is submitted with roomname and password
    if request.method == "POST" and roomname and password:
        try:
            # Check if room name already exists
            existing_room = supabase.table("rooms").select("*").eq("name", roomname).execute()
            if existing_room.data:
                return "Room name already exists. Please choose another name.", 400
                
            # Save room info
            supabase.table("rooms").insert({
                "id": user_id,
                "password": password,
                "name": roomname
            }).execute()
            
            # Save user info
            supabase.table("userinfo").insert({
                "ip": user_id,
                "username": username,
                "color": color,
                "roomname": roomname
            }).execute()
            
            resp = make_response(redirect(url_for("lobby", roomname=roomname)))
            resp.set_cookie("user_id", user_id, max_age=60 * 60 * 24, httponly=True)
            return resp
        except Exception as e:
            return f"Error creating room: {str(e)}", 500
    
    try:
        response = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/newroom.html")
        response.raise_for_status()
        return render_template_string(response.text, password=password, roomname=roomname)
    except requests.RequestException as e:
        return f"Failed to load new room page: {str(e)}", 500

@app.route("/room/<roomname>")
def lobby(roomname):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return redirect(url_for("rooms"))
    
    try:
        # Check if room exists
        room_response = supabase.table("rooms").select("password").eq("name", roomname).single().execute()
        if not room_response.data:
            return "Room not found", 404
        
        # Check if user is part of this room
        user_check = supabase.table("userinfo").select("*").eq("ip", user_id).eq("roomname", roomname).execute()
        if not user_check.data:
            return "You don't have access to this room", 403
        
        room_password = room_response.data.get("password")
        user_response = supabase.table("userinfo").select("username").eq("roomname", roomname).execute()
        
        # Limit to 4 players
        usernames = [user["username"] for user in user_response.data[:4]] if user_response.data else []
        
        # Fill remaining slots with "None"
        while len(usernames) < 4:
            usernames.append("None")
        
        html_response = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@main/lobby.html")
        html_response.raise_for_status()
        
        return render_template_string(
            html_response.text, 
            roomname=roomname, 
            password=room_password,
            p1=usernames[0],
            p2=usernames[1],
            p3=usernames[2],
            p4=usernames[3]
        )
    except Exception as e:
        return f"Error loading lobby: {str(e)}", 500

@app.route("/oldroom", methods=["GET", "POST"])
def oldroom():
    username = request.cookies.get("username")
    color = request.cookies.get("color")
    if not username or not color:
        return redirect(url_for("rooms"))
    
    roomname = request.form.get("roomname")
    password = request.form.get("password")
    
    if request.method == "POST" and roomname and password:
        try:
            # Check if room exists and password matches
            room_data = supabase.table("rooms").select("*").eq("name", roomname).execute()
            if not room_data.data or room_data.data[0]["password"] != password:
                return "Invalid room name or password", 400
            
            # Check if room is full (max 4 players)
            user_count = supabase.table("userinfo").select("count").eq("roomname", roomname).execute()
            if user_count.count >= 4:
                return "Room is full", 400
            
            # Generate a unique user ID
            user_id = generate_unique_id()
            
            # Save user info
            supabase.table("userinfo").insert({
                "ip": user_id,
                "username": username,
                "color": color,
                "roomname": roomname
            }).execute()
            
            resp = make_response(redirect(url_for("lobby", roomname=roomname)))
            resp.set_cookie("user_id", user_id, max_age=60 * 60 * 24, httponly=True)
            return resp
        except Exception as e:
            return f"Error joining room: {str(e)}", 500
    
    try:
        response = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/oldroom.html")
        response.raise_for_status()
        return render_template_string(response.text)
    except requests.RequestException as e:
        return f"Failed to load join room page: {str(e)}", 500

@app.route("/leave_room")
def leave_room():
    user_id = request.cookies.get("user_id")
    if user_id:
        try:
            # Remove user from room
            supabase.table("userinfo").delete().eq("ip", user_id).execute()
            
            # Check if room is empty and delete if so
            user_info = supabase.table("userinfo").select("roomname").eq("ip", user_id).single().execute()
            if user_info.data:
                roomname = user_info.data.get("roomname")
                remaining_users = supabase.table("userinfo").select("count").eq("roomname", roomname).execute()
                if remaining_users.count == 0:
                    supabase.table("rooms").delete().eq("name", roomname).execute()
        except Exception:
            pass  # If there's an error, just continue to redirect
            
        resp = make_response(redirect(url_for("rooms")))
        resp.delete_cookie("user_id")
        return resp
    
    return redirect(url_for("rooms"))
    
# ------------------------
# SOCKETS
# ------------------------

@socketio.on('connect')
def connection():
    username = request.cookies.get("username")
    user_id = request.cookies.get("user_id")

    print(f"{username} with ID of {user_id} has connected")
    data = {"username":username, "user_id":user_id}
    
    send("connect_response", data, broadcast = True)

@socketio.on('disconnect')
def disconnection:
    username = request.cookies.get("username")
    user_id = request.cookies.get("user_id")

    print(f"{username} with ID of {user_id} has disconnected")
    data = {"username":username, "user_id":user_id}
    
    send("disconnect_response", data, broadcast = True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port
    socketio.run(app, host='0.0.0.0', port=port)

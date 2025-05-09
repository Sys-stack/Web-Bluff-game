
# IMPORTS: DUAL COMMUNICATON

import eventlet
eventlet.monkey_patch()  # Add this at the top before any other imports
import eventlet.wsgi

# IMPORTS: FLASK

from flask import Flask, request, redirect, url_for, render_template, make_response, jsonify
import requests
from flask_socketio import SocketIO, send, emit, join_room, leave_room

# IMPORTS: SUPABASE

from supabase import create_client, Client
import os

# IMPORTS: MISC USES

from gamelogic import BluffGame
import random
import string
import uuid


# ------------------------
# Helper Function: Generate Unique ID
# ------------------------
def generate_unique_id():
    """Generate a unique ID using UUID4 (more collision-resistant than 4 characters)"""
    return str(uuid.uuid4())[:8]  # Using first 8 chars of UUID for readability
def fetchroom(userid):
    roomthing = supabase.table("userinfo").select("roomname").eq("ip", userid).execute().data
    return roomthing

usernames = []
userids = {}  
gamerooms = {}
connectedusers = {}

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
ready_players = {}
intentional_leavers = set()
@app.route("/", methods=["GET", "POST"])
def home():
    action = request.form.get("action")
    if action == "play":
        return redirect(url_for("rooms"))
    elif action == "about":
        return redirect(url_for("credits"))
    
    return render_template("bluff.html")

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


    resp = make_response(render_template("rooms.html", username=username))
        
        # Set cookies only if username is not the default
    if username != "Username":
        resp.set_cookie("username", username, max_age=60 * 60 * 24, httponly=True)
        resp.set_cookie("color", color, max_age=60 * 60 * 24, httponly=True)
        
    return resp

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
    
    return render_template("newroom.html", password=password, roomname=roomname)
    

@app.route("/room/<roomname>", methods = ["POST", "GET"])
def lobby(roomname):
    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")
    if not user_id:
        return redirect(url_for("rooms"))
    
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
        
        
    return render_template(
            "lobby.html", 
            roomname=roomname, 
            password=room_password,
            username=username
        )

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
            user_count = supabase.table("userinfo").select("*").eq("roomname", roomname).execute()
            if len(user_count.data) >= 4:
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

        
    return render_template("oldroom.html")



@app.route("/game/<roomname>", methods = ["GET", "POST"])
def game(roomname):
    try: 
        userid = request.cookies.get("userid")
        
            
        return render_template("gameroom.html", userid = userid)
            
    except Exception as e:
        app.logger.error(f"Database insert error: {e}")
        return f"<h1> error: {e}</h1>"
     
    
    

    
# ------------------------
# SOCKETS
# ------------------------

@socketio.on('connect')
def connection():
    try:
        if hasattr(request, 'cookies'):
            username = request.cookies.get("username")
            user_id = request.cookies.get("user_id")
            connectedusers[user_id] = request.sid
            roomname = supabase.table("userinfo").select("roomname").eq("ip", user_id).single().execute().data["roomname"]
            user_data = supabase.table("userinfo").select("username").eq("roomname", roomname).execute().data
            usernames_list = [user["username"] for user in user_data]
            while len(usernames_list)<=4:
                usernames_list.append("Waiting...")

            userlabeldict = {"p1":usernames_list[0],"p2":usernames_list[1],"p3":usernames_list[2],"p4":usernames_list[3]}
            join_room(roomname)
        else:
            # Fall back to session data or connection data
            username = "Unknown"
            user_id = request.sid  # Socket.IO session ID
            userlabeldict = {"p1":"Waiting...","p2":"Waiting...","p3":"Waiting...","p4":"Waiting..."}
        print(f"{username} with ID of {user_id} has connected")
        data = {"username": username, "user_id": user_id, "userlist": userlabeldict}
        
        # Make sure you're not creating an endless loop by emitting to all clients
        emit("connect_response", data, to=roomname)
    except Exception as e:
        print(f"Error in connection handler: {e}")


@socketio.on("player-ready")
def handle_player_ready():
    username = request.cookies.get("username")
    user_id = request.cookies.get("user_id")
    intentional_leavers.add(request.sid)
    # Get the player's room
    roomname = supabase.table("userinfo")\
        .select("roomname")\
        .eq("ip", user_id)\
        .single()\
        .execute().data["roomname"]

    join_room(roomname)  # Ensure user is in the correct room

    # Initialize room entry if missing
    if roomname not in ready_players:
        ready_players[roomname] = set()

    ready_players[roomname].add(username)

    # Broadcast to all clients in the room
    emit("player-is-ready", {"username": username}, room=roomname)

    # Check total number of players in the room
    total_users = 4

    if len(ready_players[roomname]) == total_users:

        
        # All players are ready — start the game
        emit("redirect", {"url": url_for("game", roomname=roomname)}, room=roomname)
            
        ready_players.pop(roomname)  # Optional: clear room after starting

@socketio.on('game-connect')
def to_start_game():
    try:
        
        user_id = request.cookies.get("user_id")
        roomname = supabase.table("userinfo")\
            .select("roomname")\
            .eq("ip", user_id)\
            .single()\
            .execute().data["roomname"]

        # Store user_id under that room
        if roomname not in userids:
            userids[roomname] = [user_id]
        else:
            if user_id not in userids[roomname]:
                userids[roomname].append(user_id)

        # Once room has 4 players, start the game
        if len(userids[roomname]) == 4:
            if roomname not in gamerooms:
                # Create the BluffGame instance
                gamerooms[roomname] = BluffGame(userids, roomname)
                gamerooms[roomname].start()
                

                # DO NOT CHANGE THIS LINE AS PER YOUR REQUEST
                for id in gamerooms[roomname].userids:
                    index = gamerooms[roomname].userids.index(id)
                    nextinorder = [0,0,0]
                    diff = 4 - index 
                    gamerooms[roomname].display_hand(id)
                    for other in range(1,4):
                        if (index + other) < 4:
                            nextinorder[other - 1] = gamerooms[roomname].userids[index + other]
                        else:
                            nextinorder[other - 1] = gamerooms[roomname].userids[index + other - diff]
                
                    
                    emit("game-start", {"html": gamerooms[roomname].player_html[id],
                                       "next": gamerooms[roomname].back_hand(nextinorder[0]),
                                        "nextnext": gamerooms[roomname].back_hand(nextinorder[1]),
                                        "nextnextnext": gamerooms[roomname].back_hand(nextinorder[2]),
                                        "currentplayer": gamerooms[roomname].current_player
                                        }, to=connectedusers[id])

    except Exception as e:
        print(f"Error in to_start_game: {e}")

@socketio.on('disconnect')
def disconnection():
    try:
        if request.sid in intentional_leavers:
            intentional_leavers.remove(request.sid)
            
        elif (hasattr(request, 'cookies') ):
            username = request.cookies.get("username")
            user_id = request.cookies.get("user_id")
            rooms = supabase.table("userinfo").select("roomname").eq("ip", user_id).execute().data
            roomname = rooms[0]["roomname"]
            connectedusers.pop(user_id)
            delete = supabase.table("userinfo").delete().eq("ip", user_id).execute()
            users = supabase.table("userinfo").select("username").eq("roomname", roomname).execute().data
            if not users:
                supabase.table("rooms").delete().eq("name", roomname).execute()

            user_data = supabase.table("userinfo").select("username").eq("roomname", roomname).execute().data
            usernames_list = [user["username"] for user in user_data]
            while len(usernames_list)<=4:
                usernames_list.append("Waiting...")

            userlabeldict = {"p1":usernames_list[0],"p2":usernames_list[1],"p3":usernames_list[2],"p4":usernames_list[3]}
            
            leave_room(roomname)
            print(f"{username} with ID of {user_id} has disconnected")
            data = {"username": username, "user_id": user_id, "userlist": userlabeldict}
        
            emit("disconnect_response", data, to=roomname)
        else:
            username = "Unknown"
            user_id = request.sid
            userlabeldict = {"p1":"Waiting...","p2":"Waiting...","p3":"Waiting...","p4":"Waiting..."}
            print(f"{username} with ID of {user_id} has disconnected")
            data = {"username": username, "user_id": user_id, "userlist": userlabeldict}
        
            emit("disconnect_response", data, to=roomname)
            
        
    except Exception as e:
        print(f"Error in disconnection handler: {e}")

@socketio.on('player-turned')
def handchange(selectedCards):
    userid = request.cookies.get('userid')
    played = []
    for cardval in selectedCards:
        played.append((cardval[1], int(cardval[0])))
    roomname = fetchroom(userid)

    gamerooms[roomname].after_play(played)
    gamerooms[roomname].next_player_shift()
    for id in gamerooms[roomname].userids:
        index = gamerooms[roomname].userids.index(id)
        nextinorder = [0,0,0]
        diff = 4 - index 
        gamerooms[roomname].display_hand(id)
        for other in range(1,4):
            if (index + other) < 4:
                nextinorder[other - 1] = gamerooms[roomname].userids[index + other]
            else:
                nextinorder[other - 1] = gamerooms[roomname].userids[index + other - diff]
                
                    
        emit("switch", {"html": gamerooms[roomname].player_html[id],
                            "next": gamerooms[roomname].back_hand(nextinorder[0]),
                            "nextnext": gamerooms[roomname].back_hand(nextinorder[1]),
                            "nextnextnext": gamerooms[roomname].back_hand(nextinorder[2]),
                            "currentplayer": gamerooms[roomname].current_player
                             }, to=connectedusers[id])
    




if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port
    socketio.run(app, host='0.0.0.0', port=port)

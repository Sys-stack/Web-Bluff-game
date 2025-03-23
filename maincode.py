from flask import Flask, request, redirect, url_for, render_template_string, make_response
from flask_socketio import SocketIO, emit, join_room, leave_room
import requests
from supabase import create_client, Client
import os

# Setup Supabase
url = os.environ.get("supabase_url")
key = os.environ.get("supabase_api")

if not url or not key:
    raise Exception("Supabase URL or API key not set in environment variables.")

supabase: Client = create_client(url, key)

# Flask app setup
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

@app.route("/", methods=["GET", "POST"])
def home():
    action = request.form.get("action")
    if action == "play":
        return redirect(url_for("rooms"))
    elif action == "about":
        return redirect(url_for("credits"))

    html = requests.get("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/Bluff.html").text
    return html


@app.route("/credits", methods=["GET"])
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

    if username:
        html = requests.get("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/rooms.html").text
        resp = make_response(html)
        resp.set_cookie("username", username, max_age=60 * 60 * 24)
        resp.set_cookie("color", color or "#ffffff", max_age=60 * 60 * 24)
        return resp

    html = requests.get("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/rooms.html").text
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


@app.route("/room/<roomname>", methods=["GET"])
def lobby(roomname):
    response = supabase.table("rooms").select("password").eq("name", roomname).single().execute()
    if response.data:
        room_password = response.data["password"]
    else:
        return "Room not found", 404

    # Get players (initially static)
    user_response = supabase.table("userinfo").select("username").eq("roomname", roomname).execute()
    usernames = [user["username"] for user in user_response.data] if user_response.data else []
    auto_refresh = len(usernames) < 4

    html = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@main/lobby.html").text
    return render_template_string(html, roomname=roomname, password=room_password,
                                  p1=usernames[0] if len(usernames) > 0 else None,
                                  p2=usernames[1] if len(usernames) > 1 else None,
                                  p3=usernames[2] if len(usernames) > 2 else None,
                                  p4=usernames[3] if len(usernames) > 3 else None,
                                  auto_refresh=auto_refresh)


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
    user_entry = supabase.table("userinfo").select("roomname").eq("ip", user_ip).single().execute()
    if not user_entry.data:
        return "User not found", 404

    roomname = user_entry.data["roomname"]
    supabase.table("userinfo").delete().eq("ip", user_ip).execute()
    remaining = supabase.table("userinfo").select("ip").eq("roomname", roomname).execute()

    if not remaining.data:
        supabase.table("rooms").delete().eq("name", roomname).execute()

    return "User and empty room removed", 200

# ------------------------
# SOCKET.IO EVENTS
# ------------------------

@socketio.on('join')
def handle_join(data):
    roomname = data['room']
    join_room(roomname)
    user_response = supabase.table("userinfo").select("username").eq("roomname", roomname).execute()
    usernames = [user["username"] for user in user_response.data]
    emit('update_users', usernames, room=roomname)


@socketio.on('leave')
def handle_leave(data):
    roomname = data['room']
    username = data.get('username')
    leave_room(roomname)

    user_entry = supabase.table("userinfo").select("ip").eq("username", username).eq("roomname", roomname).single().execute()
    if user_entry.data:
        supabase.table("userinfo").delete().eq("ip", user_entry.data["ip"]).execute()

    # Check if room is now empty
    remaining = supabase.table("userinfo").select("ip").eq("roomname", roomname).execute()
    if not remaining.data:
        supabase.table("rooms").delete().eq("name", roomname).execute()

    # Update everyone
    updated = supabase.table("userinfo").select("username").eq("roomname", roomname).execute()
    usernames = [user["username"] for user in updated.data]
    emit('update_users', usernames, room=roomname)


@socketio.on('disconnect')
def handle_disconnect():
    print("A user disconnected — consider cleanup via heartbeat or timeout")

from flask import Flask, request, redirect, url_for, render_template_string, make_response, jsonify
import requests
from supabase import create_client, Client
import os
import random
import string

# ------------------------
# Helper Function: Generate Unique 4-Character Code
# ------------------------
def generate_4_char_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=4))

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
    
    response = requests.get("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/Bluff.html")
    if response.status_code != 200:
        return "Failed to load home page", 500
    return response.text

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

    # Fetch the HTML page
    response = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/rooms.html")
    if response.status_code != 200:
        return "Failed to load rooms page", 500

    # Create response object with the fetched HTML
    resp = make_response(response.text)

    # Only set cookies if username is not the default
    if username != "Username":
        resp.set_cookie("username", username, max_age=60 * 60 * 24)
        resp.set_cookie("color", color, max_age=60 * 60 * 24)

    return render_template_string(resp, username =(  username or "Username" ))# Return the response


@app.route("/newroom", methods=["GET", "POST"])
def newroom():
    username = request.cookies.get("username")
    color = request.cookies.get("color")
    password = request.form.get("password")
    roomname = request.form.get("roomname")
    
    # Check if the username and color are set
    if not username or not color:
        return "Please set your profile before creating a room.", 400
    
    # Generate a unique user IP
    user_ip = generate_4_char_code()
    while supabase.table("userinfo").select("ip").eq("ip", user_ip).execute().data:
        user_ip = generate_4_char_code()
    
    # Save room info
    supabase.table("rooms").upsert({
        "id": user_ip,
        "password": password,
        "name": roomname
    }, on_conflict=["id"]).execute()
    
    # Save user info
    supabase.table("userinfo").upsert({
        "ip": user_ip,
        "username": username,
        "color": color,
        "roomname": roomname
    }, on_conflict=["ip"]).execute()
    
    response = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/newroom.html")
    if response.status_code != 200:
        return "Failed to load new room page", 500
    
    resp = make_response(response.text)
    resp.set_cookie("user_ip", user_ip, max_age=60 * 60 * 24)
    if roomname and password:
        return redirect(url_for("lobby", roomname = roomname))
    return render_template_string(response.text, password=password, roomname=roomname)

@app.route("/room/<roomname>")
def lobby(roomname):
    response = supabase.table("rooms").select("password").eq("name", roomname).single().execute()
    if not response.data:
        return "Room not found", 404
    
    room_password = response.data.get("password")
    user_response = supabase.table("userinfo").select("username").eq("roomname", roomname).execute()
    usernames = [user["username"] for user in user_response.data] if user_response.data else []
    
    html_response = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@main/lobby.html")
    if html_response.status_code != 200:
        return "Failed to load lobby page", 500
    
    return render_template_string(html_response.text, roomname=roomname, password=room_password,
                                  p1=usernames[0] if len(usernames) > 0 else "None",
                                  p2=usernames[1] if len(usernames) > 1 else "None",
                                  p3=usernames[2] if len(usernames) > 2 else "None",
                                  p4=usernames[3] if len(usernames) > 3 else "None")

@app.route("/oldroom", methods=["GET", "POST"])
def oldroom():
    username = request.cookies.get("username")
    color = request.cookies.get("color")
    if not username or not color:
        return redirect(url_for("rooms"))
    
    roomname = request.form.get("roomname")
    password = request.form.get("password")
    user_ip = generate_4_char_code()
    while supabase.table("userinfo").select("ip").eq("ip", user_ip).execute().data:
        user_ip = generate_4_char_code()
    
    if roomname and password:
        room_data = supabase.table("rooms").select("*").eq("name", roomname).execute()
        if room_data.data and room_data.data[0]["password"] == password:
            supabase.table("userinfo").upsert({
                "ip": user_ip,
                "username": username,
                "color": color,
                "roomname": roomname
            }, on_conflict=["ip"]).execute()
            return redirect(url_for("lobby", roomname=roomname))
    
    response = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/oldroom.html")
    if response.status_code != 200:
        return "Failed to load old room page", 500
    
    return render_template_string(response.text)

if __name__ == "__main__":
    app.run(debug=True)

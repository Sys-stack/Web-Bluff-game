from flask import Flask, request, redirect, url_for, render_template_string, make_response, jsonify
import requests
from supabase import create_client, Client
import os

# ------------------------
# SUPABASE SETUP
# ------------------------

url = os.environ.get("supabase_url")
key = os.environ.get("supabase_api")

supabase: Client = create_client(url, key)

# ------------------------
# FLASK APP INITIALIZATION
# ------------------------

app = Flask(__name__)

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

    if request.form.get("username"):
        username = request.form.get("username")
    else:
        username = "Username"
    color = request.form.get("color")

    html = requests.get("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/rooms.html")

    if request.form.get("username"):
        resp = make_response(html)
        resp.set_cookie("username", username, max_age=60 * 60 * 24)
        resp.set_cookie("color", color or "#ffffff", max_age=60 * 60 * 24)
        return render_template_string(html.text, username = username)

    return html.text

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

    html = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@main/lobby.html").text

    # Fill player slots with current users or "None"
    return render_template_string(html, roomname=roomname, password=room_password,
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

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, request, redirect, url_for, render_template, render_template_string, make_response
import requests
from supabase import create_client, Client
import os

url = os.environ.get("supabase_url")
key = os.environ.get("supabase_api")
supabase: Client = create_client(url, key)

app = Flask(__name__)


@app.route("/", methods=["GET","POST"])
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

    username = request.cookies.get("username", "")
    color = request.cookies.get("color", "#ffffff")

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


@app.route("/room/<roomname>", methods=["GET","POST"])
def lobby(roomname):
    response = supabase.table("rooms").select("password").eq("name", roomname).single().execute()

    if response.data:
        room_password = response.data["password"]
    else:
        return "Room not found", 404

    user_response = supabase.table("userinfo").select("username").eq("roomname", roomname).execute()
    usernames = [user["username"] for user in user_response.data] if user_response.data else []
    while username:
        p1 = usernames[0] if len(usernames) > 0 and usernames[0] else None
        p2 = usernames[1] if len(usernames) > 1 and usernames[1] else None
        p3 = usernames[2] if len(usernames) > 2 and usernames[2] else None
        p4 = usernames[3] if len(usernames) > 3 and usernames[3] else None

    html = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@main/lobby.html").text
    return render_template_string(html, roomname=roomname, password=room_password, p1=p1, p2=p2, p3=p3, p4=p4)


@app.route("/oldroom", methods=["GET", "POST"])
def oldroom():
    username = request.cookies.get("username")
    color = request.cookies.get("color")

    if not username or not color:
        return redirect(url_for("rooms"))

    roomname = request.form.get("roomname")
    password = request.form.get("password")
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    error_message = None

    if roomname and password:
        try:
            room_data = supabase.table('rooms').select("*").eq("name", roomname).execute()

            if room_data.data and len(room_data.data) > 0:
                stored_password = room_data.data[0]['password']
                if password == stored_password:
                    supabase.table('userinfo').upsert({
                        "ip": user_ip,
                        "username": username,
                        "color": color,
                        "roomname": roomname
                    }, on_conflict=["ip"]).execute()

                    return redirect(url_for("lobby", roomname=roomname))  
                else:
                    error_message = "Incorrect password. Please try again."
            else:
                error_message = "Room not found. Please check the room name."
        except Exception as e:
            error_message = "An error occurred. Please try again later."

    oldroom_github_html = "https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/oldroom.html"
    page = requests.get(oldroom_github_html).text

    return render_template_string(page, error=error_message)


if __name__ == "__main__":
    app.run(debug=True)

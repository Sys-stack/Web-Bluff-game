from flask import Flask, request, redirect, url_for, render_template, render_template_string, make_response
import requests
from supabase import create_client, Client
import os

url = os.environ.get("supabase_url")
key = os.environ.get("supabase_api")
supabase: Client = create_client(url, key)

app = Flask(__name__)

@app.route("/room/<roomname>")
def lobby(roomname):
   
    response = supabase.table("rooms").select("password").eq("name", roomname).single().execute()
    
    if response.data:
        room_password = response.data["password"]
    else:
        return "Room not found", 404

   
    html = requests.get("https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@main/lobby.html").text
    return render_template_string(html, roomname=roomname, password=room_password)

    
@app.route("/newroom", methods=["GET", "POST"])
def newroom():
    username = request.cookies.get("username")  
    color = request.cookies.get("color")  
    password = request.form.get("password")
    roomname = request.form.get("roomname")
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    if not username:
        return "Please set your profile before creating a room.", 400

    response_room = supabase.table('rooms').upsert({
    "id": user_ip,  
    "password": password,
    "name": roomname
    }, on_conflict=["id"]).execute()


    response_user = supabase.table('userinfo').upsert({
    "ip": user_ip,
    "username": username,
    "color": color,
    "roomname": roomname
     }, on_conflict=["ip"]).execute()
     
    if password and roomname:
        return redirect(url_for("lobby", roomname=roomname))

    
    newroom_github_html = "https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@latest/newroom.html"
    page = requests.get(newroom_github_html)
    return render_template_string(page.text, password = password, roomname = roomname)
    
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
        resp.set_cookie("username", username, max_age=60*60*24)
        resp.set_cookie("color", color or "#ffffff", max_age=60*60*24)
        return resp


    username = request.cookies.get("username", "")
    color = request.cookies.get("color", "#ffffff")

    html = requests.get("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/rooms.html").text
    return html

    
@app.route("/credits")
def credits():
    return "<h2>Game Credits Page</h2>"

@app.route("/", methods=["POST", "GET"])
def home():
    action = request.form.get("action")

    if action == "play":
        return redirect(url_for("rooms"))
    elif action == "about":
        return redirect(url_for("credits"))

    html = requests.get("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/Bluff.html").text
    return html

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, request, redirect, url_for, render_template, make_response
import requests
from supabase import create_client, Client
import os

url = os.environ.get("supabase_url")
key = os.environ.get("supabase_api")
supabase: Client = create_client(url, key)


app = Flask(__name__)

@app.route("/newroom", methods=["POST"])
def newroom:
    username = request.cookies.get(username)
    return render_template("<h> Welcome {{ username }} </h>", username = username)
@app.route("/rooms", methods=["POST","GET"])
def rooms():
    roomaction = request.form.get("action")  # Fix variable name

    if roomaction == "newroom":
        return redirect(url_for("newroom"))
    elif roomaction == "oldroom":
        return redirect(url_for("oldroom"))

    username = request.form.get("username")  # Fix: Use .get() to prevent errors
    color = request.form.get("color")  # Fix: Use .get()

    github_room_html_url = "https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/rooms.html"
    roomrender = requests.get(github_room_html_url)
    roomresponse = make_response(render_template(roomrender.text)
    roomresponse.set_cookie('username', username, max_age = 60*60*24)
    roomresponse.set_cookie('color', color, max_age = 60*60*24)
    return roomresponse

@app.route("/credits")
def credits():
    return "<h2>Game Credits Page</h2>"
    
@app.route("/", methods=["POST", "GET"])
def home():
    # Check which button was clicked
    action = request.form.get("action")  # Gets the value of the clicked button

    if action == "play":
        return redirect(url_for("rooms"))
    elif action == "about":
        return redirect(url_for("credits"))

    # Fetching HTML from GitHub (Not Recommended for Live Apps)
    github_html_url = "https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/Bluff.html"
    response = requests.get(github_html_url)

    return response.text  # Returns the HTML content

if __name__ == "__main__":
    app.run(debug=True)

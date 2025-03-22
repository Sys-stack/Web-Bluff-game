from flask import Flask, request, redirect, url_for, render_template, render_template_string, make_response
import requests
from supabase import create_client, Client
import os

url = os.environ.get("supabase_url")
key = os.environ.get("supabase_api")
supabase: Client = create_client(url, key)

app = Flask(__name__)

@app.route("/newroom", methods=["GET", "POST"])
def newroom():
    username = request.cookies.get("username")  # FIXED: use string key
    return render_template_string("<h1>Welcome, {{ username }}!</h1>", username=username)

@app.route("/rooms", methods=["POST", "GET"])
def rooms():
    roomaction = request.form.get("action")

    if roomaction == "newroom":
        return redirect(url_for("newroom"))
    elif roomaction == "oldroom":
        return redirect(url_for("oldroom"))  # Make sure this route exists

    # Handle profile form submission
    username = request.form.get("username")
    color = request.form.get("color")

    
    html = requests.get("https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/rooms.html").text
    resp = make_response(render_template_string(html))  # using render_template_string for raw HTML
    resp.set_cookie('username', username, max_age=60*60*24)
    resp.set_cookie('color', color, max_age=60*60*24)
    return resp
    
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

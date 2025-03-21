from flask import Flask, request, redirect, url_for, render_template
import requests
from supabase import create_client, Client
import os

url: str = os.environ.get("https://gsimtnnbcszbitjibtdn.supabase.co")
key: str = os.environ.get("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdzaW10bm5iY3N6Yml0amlidGRuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI0NTgxNDMsImV4cCI6MjA1ODAzNDE0M30.DIi45qbB4GLYyKLT0lGliI7aQuo4TPVgr-OPn-cbKVQ")
supabase: Client = create_client(url, key)


app = Flask(__name__)

@app.route("/rooms")
def rooms():
    return "<h2>Welcome to the Rooms Page</h2>"

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

from flask import Flask, request, redirect, url_for, render_template
import requests

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
    github_html_url = "https://cdn.jsdelivr.net/gh/Sys-stack/Web-Bluff-game@main/Bluff.html"
    response = requests.get(github_html_url)

    return response.text  # Returns the HTML content

if __name__ == "__main__":
    app.run(debug=True)

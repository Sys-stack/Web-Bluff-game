from flask import Flask
import requests as req

app = Flask(__name__)

@app.route(methods = ["POST"])
def home():
    if play:
        reroute(url_for('rooms'))
    elif about:
        reroute(url_for('credits'))
    return render_template(req.get('https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/main/Bluff.html'))

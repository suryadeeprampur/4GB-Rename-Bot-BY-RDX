import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '@JishuDeveloper'

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)

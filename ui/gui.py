import requests
from flask import Flask, jsonify, redirect, render_template, request, url_for

app = Flask(__name__)

# API Endpoint
API_URL = "http://localhost:8080"

@app.route("/")
def index():
    """Render homepage."""
    return render_template("index.html")

@app.route("/search")
def search():
    """Render search results page."""
    query = request.args.get("q", "")
    index = request.args.get("index", "inverted")
    limit = int(request.args.get("limit", 10))
    offset = int(request.args.get("offset", 0))
    spellcheck = request.args.get("spellcheck", "true") == "true"
    summary_type = request.args.get("summary_type", "dynamic")

    if not query:
        return redirect(url_for("index"))

    # Call API
    response = requests.get(
        f"{API_URL}/search",
        params={"q": query, "index": index, "limit": limit, "offset": offset, "spellcheck": spellcheck, "summary_type": summary_type}
    )
    data = response.json()

    return render_template(
        "search.html",
        query=query,
        results=data.get("results", []),
        spellchecked=data.get("spellchecked", query),
        suggested_query=None if query == data.get("query") else data.get("query"),
        index=index,
        limit=limit,
        offset=offset,
        spellcheck=spellcheck,
        summary_type=summary_type,
    )

@app.route("/autocomplete")
def autocomplete():
    """Return autocomplete suggestions."""
    query = request.args.get("q", "")
    response = requests.get(f"{API_URL}/autocomplete", params={"q": query})
    return jsonify(response.json())

if __name__ == "__main__":
    app.run(debug=True)

# -*- coding: utf-8 -*-
"""Trollservice – single-page landing site (Flask + HTML/CSS)."""

from flask import Flask, abort, render_template, request, send_from_directory

from translations import TRANSLATIONS

app = Flask(__name__)


def render_page(lang, sent=False, errors=None, form=None):
    return render_template(
        "index.html",
        lang=lang,
        t=TRANSLATIONS[lang],
        sent=sent,
        errors=errors or {},
        form=form or {},
    )


@app.route("/")
def index():
    return render_page("sv", sent=request.args.get("sent") == "1")


@app.route("/en")
def index_en():
    return render_page("en", sent=request.args.get("sent") == "1")


@app.route("/style.css")
def stylesheet():
    """Stylesheet at the site root: referenced as /style.css in the HTML."""
    return send_from_directory(app.static_folder, "css/style.css")


_ROOT_IMAGES = {"favicon", "logo-mark", "logo-full"}


@app.route("/<name>.png")
def root_image(name):
    """Root-level image aliases: /favicon.png, /logo-mark.png, /logo-full.png."""
    if name not in _ROOT_IMAGES:
        abort(404)
    return send_from_directory(app.static_folder, f"img/{name}.png")


@app.errorhandler(404)
def not_found(_error):
    body = render_template(
        "404.html", lang="sv", t=TRANSLATIONS["sv"], sent=False, errors={}, form={}
    )
    return body, 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

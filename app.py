# -*- coding: utf-8 -*-
"""Trollservice – single-page landing site (Flask + HTML/CSS)."""

import re
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request

from translations import TRANSLATIONS

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "messages.log"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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


@app.post("/kontakt")
def kontakt():
    lang = request.form.get("lang", "sv")
    if lang not in TRANSLATIONS:
        lang = "sv"

    form = {
        "namn": request.form.get("namn", "").strip(),
        "epost": request.form.get("epost", "").strip(),
        "meddelande": request.form.get("meddelande", "").strip(),
    }

    err = TRANSLATIONS[lang]["errors"]
    errors = {}
    if not form["namn"]:
        errors["namn"] = err["name"]
    if not EMAIL_RE.match(form["epost"]):
        errors["epost"] = err["email"]
    if len(form["meddelande"]) < 10:
        errors["meddelande"] = err["message"]

    if errors:
        return render_page(lang, errors=errors, form=form)

    stamp = datetime.now().isoformat(timespec="seconds")
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(
            f"{stamp} | {lang} | {form['namn']} | {form['epost']} | {form['meddelande']}\n"
        )

    return redirect(("/en" if lang == "en" else "/") + "?sent=1#kontakt")


@app.errorhandler(404)
def not_found(_error):
    body = render_template(
        "404.html", lang="sv", t=TRANSLATIONS["sv"], sent=False, errors={}, form={}
    )
    return body, 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

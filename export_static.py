# -*- coding: utf-8 -*-
"""Build the static site at the project root for GitHub Pages.

Renders the Flask templates to plain HTML and copies the root assets:

  index.html        Swedish (site root, "/")
  en/index.html     English ("/en/")
  404.html          error page (GitHub Pages picks it up automatically)
  style.css         from static/css/style.css
  favicon.png, logo-mark.png, logo-full.png   from static/img/
  .nojekyll         skip Jekyll processing on GitHub Pages

The exported form posts straight to FormSubmit (tomsta61@gmail.com) with
browser-side validation + an AJAX success message; the Flask dev site keeps
posting to /kontakt with its own validation and messages.log.

Run after any copy/CSS/template change:

  .venv\\Scripts\\python.exe export_static.py
"""

import shutil
from pathlib import Path

from app import app

BASE = Path(__file__).resolve().parent
FORM_EMAIL = "tomsta61@gmail.com"
PAGES = {
    "index.html": "/",        # Swedish
    "en/index.html": "/en",   # English
    "404.html": "/finns-inte",  # any unknown path -> renders 404.html
}
ROOT_ASSETS = ("favicon.png", "logo-mark.png", "logo-full.png")


def main():
    # Static build: form goes straight to FormSubmit, browser validates.
    app.config.update(
        FORM_ACTION=f"https://formsubmit.co/{FORM_EMAIL}",
        SERVER_VALIDATION=False,
    )
    client = app.test_client()
    for rel, url in PAGES.items():
        resp = client.get(url)
        expected = 404 if rel == "404.html" else 200
        assert resp.status_code == expected, (rel, resp.status_code)
        out = BASE / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(resp.data)
        print(f"  {rel}  {resp.status_code}  {len(resp.data)} bytes")

    shutil.copyfile(BASE / "static" / "css" / "style.css", BASE / "style.css")
    print("  style.css")
    for name in ROOT_ASSETS:
        shutil.copyfile(BASE / "static" / "img" / name, BASE / name)
        print(f"  {name}")
    (BASE / ".nojekyll").touch()
    print("  .nojekyll")
    print("done -> static site ready at repo root")


if __name__ == "__main__":
    main()

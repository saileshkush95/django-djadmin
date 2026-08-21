from django.http import HttpResponse
from django.urls import reverse


def storefront(request):
    """A stand-in public site, so the admin's "View site" link goes somewhere."""
    admin_url = reverse("admin:index")
    return HttpResponse(
        f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Northwind Trading</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ margin:0; min-height:100vh; display:grid; place-items:center; background:#0d0f13; color:#e8eaed;
         font-family: ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  .card {{ text-align:center; padding:40px; }}
  h1 {{ font-size:28px; margin:0 0 8px; letter-spacing:-.02em; }}
  p {{ color:#a1a8b4; margin:0 0 24px; }}
  a {{ display:inline-block; padding:10px 18px; border-radius:9px; background:#5b5bd6; color:#fff;
       text-decoration:none; font-weight:600; }}
</style></head>
<body><div class="card">
  <h1>Northwind Trading</h1>
  <p>The storefront is a placeholder — the interesting part is the admin.</p>
  <a href="{admin_url}">Open the admin →</a>
</div></body></html>"""
    )

import pytest


@pytest.fixture
def checkup_html() -> str:
    return {
        "html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Test Page Title</title>
</head>
<body>
  <a href="https://google.com/">Root domain link</a>
  <a href="https://google.com/1.html">Normal link 1</a>
  <a href="https://google.com/2.html">Normal link 2</a>
  <a href="https://google.com/2.html">Duplicate link 2</a>
  <a href="https://google.com/3.html#test">Normal link 3 with anchor</a>
  <a href="https://google.com/picture.png">Link to an image.</a>
  <a href="https://mail.google.com/">Subdomain link</a>
  <a href="/4.html">Relative link</a>
  <a rel="nofollow" href="https://google.com/nofollow">Nofollow link</a>
  <a href="https://yandex.ru">Foreign link</a>
  <a href="mailto:admin@gmail.com">Email link</a>
  <a href="#fragment">Fragment link</a>
  <a href="ftp://google.com">Non HTTP(S) link</a>
  <a href="">Link with empty href</a>
  <a>Link without a URL</a>
  <title>Incorrect Title</title>
  <p>Some stuff.</p>
</body>
</html>
""",
        "title_nonempty_links": (
            "Test Page Title",
            {
                "#fragment",
                "/4.html",
                "ftp://google.com",
                "https://google.com/",
                "https://google.com/1.html",
                "https://google.com/2.html",
                "https://google.com/3.html#test",
                "https://google.com/picture.png",
                "https://mail.google.com/",
                "https://yandex.ru",
                "mailto:admin@gmail.com",
            },
        ),
        "filter_result_wo_subdomains": [
            "https://google.com/1.html",
            "https://google.com/2.html",
            "https://google.com/3.html",
            "https://google.com/4.html",
        ],
        "filter_result_subdomains": [
            "https://google.com/1.html",
            "https://google.com/2.html",
            "https://google.com/3.html",
            "https://google.com/4.html",
            "https://mail.google.com",
        ],
    }

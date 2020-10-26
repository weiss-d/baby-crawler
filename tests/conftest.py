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
        "result_subd": (
            "Test Page Title",
            {
                "/4.html",
                "https://google.com/",
                "https://google.com/1.html",
                "https://google.com/2.html",
                "https://google.com/3.html#test",
                "https://mail.google.com/",
            },
        ),
        "result_wo_subd": (
            "Test Page Title",
            {
                "/4.html",
                "https://google.com/",
                "https://google.com/1.html",
                "https://google.com/2.html",
                "https://google.com/3.html#test",
            },
        ),
    }

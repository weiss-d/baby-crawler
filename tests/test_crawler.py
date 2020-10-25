import pytest
from baby_crawler import crawler


def test_crawler_instance():
    cr = crawler.Crawler(
        "https://google.com",
        splash_address="0.0.0.0:8050",
        allow_subdomains=True,
        concurrency=5,
        max_sleep_interval=10.0,
    )
    assert isinstance(cr, crawler.Crawler)


@pytest.mark.parametrize(
    "allow_subd,subd_result", [(True, True), (False, False)]
)
def test_crawler_has_root_domain(allow_subd, subd_result):
    cr = crawler.Crawler("https://google.com", "", allow_subdomains=allow_subd)

    assert cr._has_root_url("https://google.com/search") == True
    assert cr._has_root_url("https://yandex.ru/search") == False

    assert cr._has_root_url("https://mail.google.com") == subd_result


@pytest.mark.parametrize(
    "allow_subd,subd_result", [(True, True), (False, False)]
)
def test_crawler_is_valid_link(allow_subd, subd_result):
    cr = crawler.Crawler("https://google.com", "", allow_subdomains=allow_subd)

    assert cr._is_valid_link("https://google.com/search") == True
    assert cr._is_valid_link("/help") == True
    assert cr._is_valid_link("#help") == False
    assert cr._is_valid_link("https://yandex.ru/search") == False

    assert cr._is_valid_link("https://mail.google.com") == subd_result


@pytest.mark.parametrize(
    "allow_subd,result", [(True, "result_subd"), (False, "result_wo_subd")]
)
def test_crawler_get_links(checkup_html, allow_subd, result):
    cr = crawler.Crawler("https://google.com", "", allow_subdomains=allow_subd)

    assert cr.get_page_data(checkup_html["html"]) == checkup_html[result]


def test_crawler_normalize_link():
    cr = crawler.Crawler("", "")

    assert (
        cr._normalize_link("https://google.com/", "https://google.com/help")
        == "https://google.com/help"
    )
    assert (
        cr._normalize_link("https://google.com/", "/help")
        == "https://google.com/help"
    )
    assert (
        cr._normalize_link(
            "https://google.com/", "https://mail.google.com/help#fragment"
        )
        == "https://mail.google.com/help"
    )

"""Testing syncronous functions of the Crawler class."""

import pytest
from baby_crawler import crawler


def test_crawler_instance():
    cr = crawler.Crawler(
        "https://google.com",
        splash_address="0.0.0.0:8050",
        allow_subdomains=True,
        allow_queries=True,
        depth_by_desc=3,
        concurrency=5,
        max_pause=10.0,
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

    assert (
        cr._is_valid_link("https://google.com/search", "https://google.com")
        == True
    )
    assert cr._is_valid_link("/help", "https://google.com") == True
    assert cr._is_valid_link("#help", "https://google.com") == False
    assert (
        cr._is_valid_link("https.google.com/#help", "https://google.com")
        == False
    )
    assert (
        cr._is_valid_link("https://yandex.ru/search", "https://google.com")
        == False
    )

    assert (
        cr._is_valid_link("https://mail.google.com", "https://google.com")
        == subd_result
    )


def test_crawler_get_page_data(checkup_html):
    cr = crawler.Crawler("https://google.com", "")

    assert (
        cr.get_page_data(checkup_html["html"])
        == checkup_html["title_nonempty_links"]
    )


@pytest.mark.parametrize(
    "allow_subd,result",
    [
        (True, "filter_result_subdomains"),
        (False, "filter_result_wo_subdomains"),
    ],
)
def test_crawler_filter_links(checkup_html, allow_subd, result):
    cr = crawler.Crawler("https://google.com", "", allow_subdomains=allow_subd)

    filter_result = list(
        cr._filter_links(
            checkup_html["title_nonempty_links"][1], "https://google.com"
        )
    )
    filter_result.sort()
    assert filter_result == checkup_html[result]


def test_crawler_normalize_link():
    cr = crawler.Crawler("https://google.com", "")

    assert (
        cr._normalize_link("https://google.com/help", "https://google.com/")
        == "https://google.com/help"
    )
    assert (
        cr._normalize_link("/help", "https://google.com/")
        == "https://google.com/help"
    )
    assert (
        cr._normalize_link(
            "https://mail.google.com/help#fragment", "https://google.com/"
        )
        == "https://mail.google.com/help"
    )


def test_remove_query():
    cr = crawler.Crawler("https://google.com", "")

    assert (
        cr._remove_query("https://google.com/search?page=42")
        == "https://google.com/search"
    )

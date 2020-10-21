import pytest

from baby_crawler import crawler


def test_crawler_instance():
    cr = crawler.Crawler(
            "https://google.com",
            allow_subdomains=True,
            concurrency=5,
            max_sleep_interval=10.0,
            )
    assert isinstance(cr, crawler.Crawler)

@pytest.mark.parametrize("allow_subd,subd_result", [(True, True), (False, False)])
def test_crawler_has_root_domain(allow_subd, subd_result):
    cr = crawler.Crawler("https://google.com", allow_subdomains=allow_subd)

    assert cr._has_root_domain("https://google.com/search") == True
    assert cr._has_root_domain("https://yandex.ru/search") == False

    assert cr._has_root_domain("https://mail.google.com") == subd_result


@pytest.mark.parametrize("allow_subd,result", [(True, "result_subd"), (False, "result_wo_subd")])
def test_crawler_get_links(checkup_html, allow_subd, result):
    cr = crawler.Crawler("https://google.com", allow_subdomains=allow_subd)

    assert cr.get_page_data(checkup_html["html"]) == checkup_html[result]


import urllib.parse
from typing import Set, Tuple

import gazpacho


class Crawler:

    def __init__(self,
            root_url:str,
            splash_address: str,
            allow_subdomains: bool = True,
            concurrency: int = 5,
            max_sleep_interval: float = 10.0
            ) -> None:
        self.root_url = root_url
        self._root_url_base = urllib.parse.urlsplit(root_url)[1]
        self.splash_address = splash_address

        self.allow_subdomains = allow_subdomains


    def _has_root_domain(self, url: str) -> bool:
        url_base = urllib.parse.urlsplit(url)[1]
        if self.allow_subdomains:
            if ".".join(url_base.split(".")[-2:]) == self._root_url_base:
                return True
        else:
            if url_base == self._root_url_base:
                return True
        return False


    def get_page_data(self, html: str) -> Tuple[str, Set]:
        soup = gazpacho.Soup(html)

        title = soup.find("title", mode="first").text

        valid_links = set()
        for anchor in soup.find("a", attrs={"href":""}, partial=True, mode="all"):
            if (not "rel" in anchor.attrs) or (anchor.attrs["rel"] != "nofollow"):
                link = anchor.attrs["href"]
                if self._has_root_domain(link):
                    valid_links.add(urllib.parse.urldefrag(link).url)

        return (title, valid_links)

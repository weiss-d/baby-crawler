from typing import Set, Tuple

import asyncio
import urllib.parse

import aiohttp
import gazpacho
import networkx

from .setqueue import SetQueue


class Crawler:
    def __init__(
        self,
        start_url: str,
        splash_address: str,
        allow_subdomains: bool = True,
        concurrency: int = 5,
        max_sleep_interval: float = 10.0,
    ) -> None:
        self.start_url = start_url
        self.root_url = urllib.parse.urlsplit(start_url)[1]
        self.splash_address = urllib.parse.urljoin(
            splash_address, "render.html?timeout=10&wait=0.5&url="
        )

        self.allow_subdomains = allow_subdomains
        self.concurrency = concurrency
        self.max_sleep_interval = max_sleep_interval

        self.site_graph = networkx.DiGraph()
        self.crawled_links = set()

    ### Blocking stuff

    def _has_root_url(self, url: str) -> bool:
        url_base = urllib.parse.urlsplit(url)[1]
        if self.allow_subdomains:
            if ".".join(url_base.split(".")[-2:]) == self.root_url:
                return True
        else:
            if url_base == self.root_url:
                return True
        return False

    def _is_valid_link(self, url: str) -> bool:
        if (url[0] == "/" and url[:2] != "//") or (
            self._has_root_url(url) and url[:4] == "http"
        ):
            return True
        return False

    def _remove_query(self, url: str) -> str:
        split = list(urllib.parse.urlsplit(url))
        split[3] = ""
        return urllib.parse.urlunsplit(split)

    def _normalize_link(self, base_url: str, url: str) -> str:
        if url[0] == "/":
            normalized_link = urllib.parse.urljoin(base_url, url)
        else:
            normalized_link = url

        return urllib.parse.urldefrag(
            self._remove_query(normalized_link)
        ).url.strip("/")

    def get_page_data(self, html: str) -> Tuple[str, Set]:
        soup = gazpacho.Soup(html)

        valid_links = set()
        for anchor in soup.find(
            "a", attrs={"href": ""}, partial=True, mode="all"
        ):
            if (not "rel" in anchor.attrs) or (
                anchor.attrs["rel"] != "nofollow"
            ):
                link = anchor.attrs["href"]
                if self._is_valid_link(link):
                    valid_links.add(link)

        title = soup.find("title", mode="first")

        return (title.text if title else "", valid_links)

    ### Async stuff

    async def fetch_page(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            print("Requesting from Splash:", self.splash_address + url)
            async with session.get(self.splash_address + url) as response:
                page_data = await response.read()
                return page_data.decode()

    async def process_links(self, number: int, queue: asyncio.Queue) -> None:
        while True:
            page_link = await queue.get()
            if not page_link in self.crawled_links:
                self.crawled_links.add(page_link)
                print(f"Task number {number} is processing {page_link}")
                page_html = await self.fetch_page(page_link)
                page_data = self.get_page_data(page_html)
                print(f"{len(page_data[1])} links found.")

                for link in page_data[1]:
                    link = self._normalize_link(page_link, link)
                    if not link in self.crawled_links:
                        self.site_graph.add_edge(page_link, link)
                        await queue.put(link)
            queue.task_done()

    async def run_crawler(self) -> None:
        queue = SetQueue()
        queue.put_nowait(self.start_url)
        workers = [
            asyncio.create_task(self.process_links(i, queue))
            for i in range(self.concurrency)
        ]
        await queue.join()
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    ### Main Runner
    def make_site_map(self):
        asyncio.run(self.run_crawler())
        print("Site map building done!")

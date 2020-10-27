from typing import Set, Tuple, Union

import asyncio
import json
import urllib.parse
from collections import defaultdict

import aiohttp
import gazpacho
import networkx

from .crawlerqueue import CrawlerQueue
from .exceptions import FetchError


class Crawler:
    """Class that performs crawling and gathers data into Networkx graph.

    Instantiate it, then run make_site_map() to crawl the site.
    After that you will have access to the data in form of Networkx graph.
    """

    def __init__(
        self,
        start_url: str,
        splash_address: str,
        allow_subdomains: bool = True,
        allow_queries: bool = False,
        depth_by_url: Union[int, None] = None,
        depth_by_desc: Union[int, None] = None,
        concurrency: int = 5,
        max_pause: float = 10.0,
    ) -> None:
        """__init__.

        Parameters
        ----------
        start_url : str
            Typically a website address, like "https://google.com".
            Must contain protocol prefix i.e. "http://" or "https://".
        splash_address : str
            Address of Splash renderer instance.
        allow_subdomains : bool
            Allow indexing subdomains like "https://mail.google.com"
        allow_queries: bool
            Allow indexing URLs containing queries i.e. something after '?' sign.
        depth_by_url : Union[int, None]
            Limit crawling depth by number of URL path segments.
            I.e. 3: "http://site.com/part1/part2/part3".
            Unlimited if not specified.
        depth_by_desc : Union[int, None]
            Limit crawling depth by number of descendant pages.
            I.e. 3: "http://site.com/part1/part2/part3".
            Unlimited if not specified.
        concurrency : int
            Maximum ammount of concurrent requests.
        max_pause : float
            Maximum pause between requests made by one of concurrent tasks.

        Returns
        -------
        None

        """
        self.start_url = start_url.strip("/")
        self.root_url = urllib.parse.urlsplit(start_url)[1]
        self.splash_address = urllib.parse.urljoin(
            splash_address, "render.html?timeout=10&wait=0.5&url="
        )

        self.allow_subdomains = allow_subdomains
        self.concurrency = concurrency
        self.max_pause = max_pause

        self.site_graph = networkx.DiGraph()
        self.site_graph.add_node(0, url=self.start_url)

        self.crawled_links = set()

        self.error_count = defaultdict(int)

    ### Blocking functions

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

    def _add_edge(self, node_id: int, node_url: str, parent_id: int) -> None:
        """Add and edge to the site graph.

        Parameters
        ----------
        node_id : int
            Unique ID given by CrawlerQueue.
        node_url : str
            URL of the page represented by this node.
        parent_id : int
            Parent page ID, i.e. the page in which the node URL was found.

        Returns
        -------
        None

        """
        self.site_graph.add_node(node_id, url=node_url)
        self.site_graph.add_edge(parent_id, node_id)

    ### Async funtions

    async def fetch_page(self, url: str) -> str:
        """Asyncronously fetch a page from given URL using aiohttp and Splash HTTP API.

        Parameters
        ----------
        url : str
            Absolute page URL.

        Returns
        -------
        str
            String of fetched page HTML.

        Raises
        ------
        FetchError
            Raised on every error associated with HTTP errors or exceeded timeouts.
            Attribute 'error_type' contains 'Splash Timeout', 'Splash Unreachable'
            or HTTP error code, while 'message' contains original error message by aiohttp.

        """
        async with aiohttp.ClientSession() as session:
            print("Requesting from Splash:", self.splash_address + url)
            try:
                async with session.get(self.splash_address + url) as response:
                    response.raise_for_status()
                    page_data = await response.read()
                    return page_data.decode()
            except aiohttp.client_exceptions.ClientConnectorError:
                print("Splash instance is unreachable.")
                raise FetchError("Splash Unreachable", "Splash unreachable.")
            #  except aiohttp.ClientConnectionError:
            #      raise
            except asyncio.TimeoutError:
                raise FetchError("Splash Timeout", "Splash timeout.")
            except aiohttp.ClientResponseError as e:
                raise FetchError(str(e.status), e.message)

    async def process_links(
        self, worker_number: int, queue: asyncio.Queue
    ) -> None:
        """Function from which concurrent workers for processing links are made.

        Parameters
        ----------
        worker_number : int
            Task number for logging.
        queue : asyncio.Queue
            CrawlerQueue to take items for processing from.

        Returns
        -------
        None

        """
        while True:
            page_id, page_link, parent_id = await queue.get()
            if not page_link in self.crawled_links:
                try:
                    self._add_edge(page_id, page_link, parent_id)
                    self.crawled_links.add(page_link)
                    print(
                        f"Task worker_number {worker_number} is processing {page_link}"
                    )
                    page_html = await self.fetch_page(page_link)
                    page_data = self.get_page_data(page_html)
                    print(f"{len(page_data[1])} links found.")

                    for link in page_data[1]:
                        link = self._normalize_link(page_link, link)
                        if not link in self.crawled_links:
                            await queue.put((link, page_id))
                except FetchError as e:
                    self.error_count[e.error_type] += 1
                    # TODO add logging for page url, or adding info to graph
            queue.task_done()

    async def run_crawler(self) -> None:
        """Asyncronous function to initiate concurrent site crawling.

        Returns
        -------
        None

        """
        queue = CrawlerQueue()
        queue.put_nowait((self.start_url, 0))
        workers = [
            asyncio.create_task(self.process_links(i, queue))
            for i in range(self.concurrency)
        ]
        await queue.join()
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    ### Main Runner
    def make_site_map(self) -> None:
        """Sycncronous function to make the site map using async run_crawler().

        Returns
        -------
        None

        """
        asyncio.run(self.run_crawler())
        print("Site map building done!")

from typing import Generator, List, Set, Tuple, Union

import asyncio
import json
import logging
import random
import re
from collections import defaultdict
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

import aiohttp
import gazpacho
import ipdb
import jellyfish
import networkx
from baby_crawler import crawler_config
from baby_crawler.crawlerqueue import CrawlerQueue
from baby_crawler.exceptions import FetchError


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
        self.root_url = urlsplit(start_url)[1]
        self.splash_address = urljoin(
            splash_address,
            f"render.html?timeout={crawler_config.splash_timeout}&wait={crawler_config.splash_wait}{crawler_config.splash_params}&url=",
        )

        self.allow_subdomains = allow_subdomains
        self._has_root_url = (
            self._has_root_url_or_subdomain
            if allow_subdomains
            else self._has_root_url_only
        )

        self.allow_queries = allow_queries

        self.depth_by_desc = depth_by_desc

        self.concurrency = concurrency
        self.max_pause = max_pause

        self.site_graph = networkx.DiGraph()
        self.site_graph.add_node(0, url=self.start_url)

        self.crawled_links = {self._normalize_link(start_url, "")}
        self.added_tasks = set()

        self.error_count = defaultdict(int)

        self.logger = logging.getLogger("asyncio")

    ### Blocking functions

    def _has_root_url_only(self, url: str) -> bool:
        """Check if the given link starts with root URL.

        Parameters
        ----------
        url : str
            URL to be checked.

        Returns
        -------
        bool
            True if the link starts only with root URL, no subdomain allowed.

        """
        url_base = urlsplit(url)[1]
        if url_base == self.root_url:
            return True
        return False

    def _has_root_url_or_subdomain(self, url: str) -> bool:
        """Check if the given link starts with root URL or its subdomain.

        Parameters
        ----------
        url : str
            URL to be checked.

        Returns
        -------
        bool
            True if the links contains root URL.

        """
        url_base = urlsplit(url)[1]
        if ".".join(url_base.split(".")[-2:]) == self.root_url:
            return True
        return False

    def _is_valid_link(self, link: str, parent_link: str) -> bool:
        """Validates given URL against several rules to exclude unrelated links and some spider traps.

        Parameters
        ----------
        link : str
            URL for checking.
        parent_link : str
            URL of the page where given link was found.

        Returns
        -------
        bool
            True if all conditionsa are met.

        """
        if link[0] == "#":
            return False
        if link[0] == "/":
            if link[:2] == "//":
                return False
        else:
            if not self._has_root_url(link):
                return False
            if link[:4] != "http":
                return False

        extension = re.findall(r"\A.*\.([a-zA-Z]+)\\?\Z", link)
        if extension and extension[0] in crawler_config.unwanded_file_exts:
            return False

        if (
            self.allow_queries
            and jellyfish.jaro_winkler(
                urlsplit(parent_url).query, urlsplit(url).query
            )
            >= 0.85
        ):
            return False

        if (
            len(self._normalize_link(link, parent_link))
            > crawler_config.max_url_length
        ):
            return False

        return True

    def _remove_query(self, url: str) -> str:
        """Removes query part of a URL (i.e. anythin after "?").

        Parameters
        ----------
        url : str
            URL with or without query part.

        Returns
        -------
        str
            Guaranteed clean URL.

        """
        split = list(urlsplit(url))
        split[3] = ""
        return urlunsplit(split)

    def _normalize_link(self, link: str, parent_link: str) -> str:
        """Set relative link to absolute. Remove fragment if present. Remove trailing slash.

        Parameters
        ----------
        link : str
            URL for normalizing that passed _is_valid_link().
        parent_link : str
            URL of the page where given link was found.

        Returns
        -------
        str
            Clean absolute URL.

        """
        if link[0] == "/":
            normalized_link = urljoin(parent_link, link)
        else:
            normalized_link = link

        return urldefrag(normalized_link).url.strip("/")

    def _filter_links(
        self, links: List[str], parent_link: str
    ) -> Generator[str, None, None]:
        """Filters out links that are invalid or not unique.

        Parameters
        ----------
        links : List[str]
            A list of links found on a page.

        Returns
        -------
        List[str]
            A list of links, that are valid and not yet been crawled.

        """
        for link in links:
            if self._is_valid_link(link, parent_link):
                if not self.allow_queries:
                    link = self._remove_query(link)
                link = self._normalize_link(link, parent_link)
                if not link in self.crawled_links:
                    yield link

    def get_page_data(self, html: str) -> Tuple[str, Set]:
        """get_page_data.

        Parameters
        ----------
        html : str
            String of page html.

        Returns
        -------
        Tuple[str, Set]
            Tuple containing page title (or "" if none) and a list of validated links.

        """
        soup = gazpacho.Soup(html)

        title = soup.find("title", mode="first")

        links = set()
        for anchor in soup.find(
            "a", attrs={"href": ""}, partial=True, mode="all"
        ):
            if (not "rel" in anchor.attrs) or (
                anchor.attrs["rel"] != "nofollow"
            ):
                links.add(anchor.attrs["href"])

        return (title.text if title else "", links)

    def _add_graph_edge(self, node_id: int, parent_id: int, **kwargs) -> None:
        """Add and edge to the site graph.

        Parameters
        ----------
        node_id : int
            Unique ID given by CrawlerQueue.
        parent_id : int
            Parent page ID, i.e. the page in which the node URL was found.
        kwargs
            Node attributes i.e. URL, Title etc.

        Returns
        -------
        None

        """
        self.site_graph.add_node(node_id, **kwargs)
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
            self.logger.info(
                ">>> Requesting Splash: " + self.splash_address + url
            )
            try:
                async with session.get(self.splash_address + url) as response:
                    response.raise_for_status()
                    page_data = await response.read()
                    return page_data.decode()
            except aiohttp.client_exceptions.ClientConnectorError:
                self.logger.error("Splash instance is unreachable.")
                raise FetchError("Splash Unreachable", "Splash unreachable.")
            except aiohttp.ClientConnectionError as e:
                raise FetchError(str(e.status), e.message)
            except asyncio.TimeoutError:
                raise FetchError("Splash Timeout", "Splash timeout.")
            except aiohttp.ClientResponseError as e:
                raise FetchError(str(e.status), e.message)

    async def _process_link(
        self,
        queue,
        page_id: int,
        page_link: str,
        parent_id: int,
        desc_level: int,
    ) -> None:
        """Adds a page to site map graph and then processes all the links found on this page.
        Adds found links to the queue if they are not yet been crawled.

        Parameters
        ----------
        queue : asyncio.Queue
            CrawlerQueue to take items for processing from.
        page_id : int
            Unique page ID from queue.
        page_link : str
            Page URL.
        parent_id : int
            Unique ID of a page, where current page URL was found.
        desc_level : int
            Descendance level of page, from queue.

        Returns
        -------
        None

        """
        try:

            page_html = await self.fetch_page(page_link)
            # If any arror occures during fetch process, the link is not added to the Site Graph
            self.crawled_links.add(page_link)
            page_data = self.get_page_data(page_html)
            self._add_graph_edge(
                page_id, parent_id, url=page_link, title=page_data[0]
            )

            if not self.depth_by_desc or desc_level < self.depth_by_desc:
                self.logger.info(
                    f"<<< {len(page_data[1])} links found on {page_link}."
                )

                for link in self._filter_links(page_data[1], page_link):
                    if not link in self.added_tasks:
                        self.added_tasks.add(link)
                        await queue.put((link, page_id, desc_level + 1))
        except FetchError as e:
            self.error_count[e.error_type] += 1
            # TODO add logging for page url, or adding info to graph

    async def _link_worker(
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
            page_id, page_link, parent_id, desc_level = await queue.get()
            await asyncio.sleep(random.uniform(0, self.max_pause))
            self.logger.info(
                f"=> Task worker_number {worker_number} is processing {page_link}. Desc_level: {desc_level}."
            )
            await self._process_link(
                queue, page_id, page_link, parent_id, desc_level
            )
            queue.task_done()

    async def _run_crawler(self) -> None:
        """Asyncronous function to initiate concurrent site crawling.

        Returns
        -------
        None

        """
        queue = CrawlerQueue()
        queue.put_nowait((self.start_url, 0, 0))
        workers = [
            asyncio.create_task(self._link_worker(i, queue))
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
        asyncio.run(self._run_crawler())
        networkx.freeze(self.site_graph)
        self.logger.info("Site map building done!")

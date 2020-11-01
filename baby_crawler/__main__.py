"""
CLI utility to either build and save website map or draw it using previously saved data.
"""
import datetime
import json
import logging
import re

# type: ignore[attr-defined]
import time

import click
import networkx as nx
from baby_crawler import __version__, crawler
from click import echo


@click.group()
def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        datefmt="%d-%m-%y %H:%M:%S",
    )
    logging.info(f"Baby-Crawler {__version__}")


@main.command()
@click.version_option(version=__version__)
@click.argument("url", required=True, type=str)
@click.option(
    "-s",
    "--splash-address",
    type=str,
    default="http://localhost:8051",
    help="Address of Splash instance. Default is http://localhost:8050.",
)
@click.option(
    "--subdomains",
    is_flag=True,
    help="Include subdomains. I.e. mail.google.com. Default: True.",
)
@click.option(
    "--queries",
    is_flag=True,
    help="Include queries, i.e. everything after '?' sing in URL. Default: False.",
)
@click.option(
    "-d",
    "--depth",
    type=int,
    help="Limit crawling depth by number of descendant pages",
)
@click.option(
    "-c",
    "--concurrency",
    type=int,
    default=5,
    help="Maximum ammount of concurrent requests",
)
@click.option(
    "-p",
    "--max-pause",
    type=float,
    default=10.0,
    help="Maximum pause between requests made by one of concurrent tasks",
)
@click.option(
    "-o",
    "--file-prefix",
    nargs=1,
    type=str,
    help="Prefix of generated filenames instead of site URL.",
)
def save(
    url,
    splash_address,
    subdomains,
    queries,
    depth,
    concurrency,
    max_pause,
    file_prefix,
):
    """Perform the crawling and save crawled data as JSON graph representaiont
    and TAB-formatted text file in case of success.

    EXAMPLE:
        python baby_crawler save http://scrapethissite.com -s http://localhost:8050
    """

    # Perfom crawling and measure time

    cr = crawler.Crawler(
        url,
        splash_address,
        subdomains,
        queries,
        depth,
        concurrency,
        max_pause,
    )

    start = time.perf_counter()
    cr.make_site_map()
    elapsed = time.perf_counter() - start

    # Count processed links and errors

    links_found = len(cr.added_tasks)
    links_crawled = len(cr.crawled_links) - 1

    echo(f"Found {links_found} unique links on {url}.", color="green")
    echo(f"Successfully crawled {links_crawled} links.", color="green")
    echo(
        "Elapsed time {}".format(datetime.timedelta(seconds=elapsed)),
        color="green",
    )

    if cr.error_count:
        echo("Errors:", color="red")
        for error in cr.error_count:
            echo(f"{error.key}: {error.value}", color="red")

    # Write files in case of successfull crawling

    if links_found:
        if not file_prefix:
            file_prefix = re.sub("[^a-zA-Z0-9]", "_", url)
        file_prefix += time.strftime("_%y-%m-%d_%H-%M-%S", time.localtime())
        with open(f"{file_prefix}.json", "w+", encoding="utf-8") as json_file:
            json.dump(
                nx.node_link_data(cr.site_graph), json_file, ensure_ascii=False
            )
            echo(f"Written graph data to {file_prefix}.json", color="green")

        with open(f"{file_prefix}.txt", "w+") as txt_file:

            def writegraph(graph, start_node, level):
                level += 1
                for i in graph.successors(start_node):
                    txt_file.write("\t" * level + graph.nodes[i]["url"] + "\n")
                    writegraph(graph, i, level)

            writegraph(cr.site_graph, 0, -1)

            echo(f"Written found links to {file_prefix}.txt", color="green")


@main.command()
@click.argument("input_file", type=click.File("r"))
def draw(input_file):
    from urllib.parse import urlsplit

    import matplotlib.pyplot as plt
    from baby_crawler.eon import hierarchy_pos as hp

    limits = plt.axis("off")

    graph_dict = json.load(input_file)

    graph = nx.node_link_graph(graph_dict)
    graph.remove_node(0)

    pos = hp(graph, root=1)

    labels_dict = {}
    for node in graph.nodes:
        labels_dict[node] = urlsplit(graph.nodes[node]["url"]).path.split("/")[
            -1
        ]
    labels_dict[1] = graph.nodes[1]["url"]

    nx.draw_networkx(graph, pos, labels=labels_dict, node_size=5000)
    plt.show()


main()

#!/usr/bin/python3

import requests
import json
import sys
import unicodedata
import re
import os
import argparse
from termcolor import colored, cprint
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup


class WebsiteConfig:
    """Class containing various URLs and selectors needed to do a lookup on a particular site"""

    def __init__(self,
                 URL: str,
                 searchURLPattern: str,
                 itemSelector: str,
                 linkSelector: str,
                 titleSelector: str,
                 cookie: str):
        self.URL = URL
        self.searchURLPattern = searchURLPattern
        self.itemSelector = itemSelector
        self.linkSelector = linkSelector
        self.titleSelector = titleSelector
        self.cookie = cookie


class SearchResult:
    """Class to represent a single movie"""

    def __init__(self,
                 title: str,
                 URL: str):
        self.title = title
        self.URL = URL

    def __repr__(self):
        return f'{self.title} -> {self.URL}'


def isAbsolute(url):
    """Check if a given URL is absolute"""
    return bool(urlparse(url).netloc)


def search(story: str, config: WebsiteConfig):
    """Search a given website for specified movie"""

    searchURL = config.searchURLPattern.format(story=story)
    cprint(f'Searching on {config.URL}', 'cyan')

    headers = {'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
               'accept-language': 'en-US,en;q=0.9,fr-FR;q=0.8,fr;q=0.7',
               'cache-control': 'no-cache',
               'dnt': '1',
               'pragma': 'no-cache',
               'referer': 'https://www.google.com',
               'sec-fetch-mode': 'navigate',
               'sec-fetch-site': 'same-origin',
               'sec-fetch-user': '?1',
               'upgrade-insecure-requests': '1',
               'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
               }

    if config.cookie is not None:
        print(f'    ->using cookie: {config.cookie}')
        headers['cookie'] = config.cookie

    try:
        data = requests.get(searchURL, headers=headers, timeout=1)
    except requests.exceptions.Timeout:
        cprint(f'    ->timeout', 'red')
        return []

    soup = BeautifulSoup(data.text, 'html.parser')
    results = []

    for item in soup.select(config.itemSelector):
        link = item.select_one(config.linkSelector)
        title = item.select_one(config.titleSelector)
        # If URL is relative, convert to absolute URL
        movieURL = link['href']
        if not isAbsolute(movieURL):
            movieURL = urljoin(config.URL, movieURL)
        results.append(SearchResult(title.text, movieURL))

    return results


def loadConfig(filePath: str):
    """Load website configurations from json file"""

    with open(filePath, "r") as read_file:
        return json.load(read_file)


def levenshteinDistance(s1, s2):
    """Return the edit distance between two strings"""

    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(
                    1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]


def normalize(story: str):
    """Return a lower case normal form of input string (strips accents...)"""

    # Remove non alphanumeric characters
    story = re.sub('[\W_]+', '', story)
    # Remove accents and make lower case
    return unicodedata.normalize('NFKD', story).encode('ASCII', 'ignore').lower()


def sortResults(story: str, results):
    """Sort search results using edit distance"""

    # For each normalized title in results, compute an edit distance to
    # normalized story
    storyNorm = normalize(story)
    distances = []
    for result in results:
        distances.append(levenshteinDistance(
            storyNorm, normalize(result.title)))

    # Return input results but sorted bprinty edit distance
    return [x for _, x in sorted(zip(distances, results), key=lambda pair: pair[0])]


def main(argv):
    parser = argparse.ArgumentParser(description='Search for a movie across multiple streaming websites.')
    parser.add_argument('story', type=str, nargs='?', default=None, help='keywords to be forwarded to the websites search engines')
    parser.add_argument('-l', '--list', action='store_true', help='display a list of websites stored in config')
    parser.add_argument('-s', '--site', type=int, help='search on a single website using an index (as displayed in list mode)')
    args = parser.parse_args(argv)

    # Load website configs
    # Script can be called via a symlink, so we need to be careful with file paths
    selfdir = os.path.dirname(os.path.realpath(__file__))
    configPath = os.path.join(selfdir, "config.json")
    cfgData = loadConfig(configPath)
    configs = []
    for data in cfgData:
        cookie = None
        if 'cookie' in data and data['cookie'] is not None:
            cookie = data['cookie']
        configs.append(WebsiteConfig(data['URL'], data['searchURLPattern'],
                       data['itemSelector'], data['linkSelector'], data['titleSelector'], cookie))

    # List mode: print websites with their respective index and exit
    if args.list:
        for idx, config in enumerate(configs):
            print(f'[{idx}] {config.URL}')
        return

    # Make sure user did provide search keywords
    story = args.story
    if story is None:
        parser.error('Missing search keywords')
        return

    results = []
    numWebsites = len(configs)
    if args.site is not None:
        if args.site >= len(configs):
            print('Website index out of bounds')
            return
        results = search(story, configs[args.site])
        numWebsites = 1
    else:
        # For all websites, search / scrap
        for config in configs:
            results = results + search(story, config)

    # Sort results by relevance
    sorted = sortResults(story, results)

    # Display results
    print('\n')
    cprint(
        f'Found {len(sorted)} results accross {numWebsites} websites:', 'green')

    for result in sorted:
        print(result)


if __name__ == '__main__':
    main(sys.argv[1:])

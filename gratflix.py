#!/usr/bin/python3

from termcolor import colored, cprint
import requests
import json
import sys
import unicodedata
import re
from bs4 import BeautifulSoup


class WebsiteConfig:
    """Class containing various URLs and selectors needed to do a lookup on a particular site"""

    def __init__(self,
                 website: str,
                 searchURLPattern: str,
                 itemSelector: str,
                 linkSelector: str,
                 titleSelector: str):
        self.website = website
        self.searchURLPattern = searchURLPattern
        self.itemSelector = itemSelector
        self.linkSelector = linkSelector
        self.titleSelector = titleSelector


class SearchResult:
    """Class to represent a single movie"""

    def __init__(self,
                 title: str,
                 URL: str):
        self.title = title
        self.URL = URL

    def __repr__(self):
        return f'{self.title} -> {self.URL}'


def search(story: str, config: WebsiteConfig):
    """Search a given website for specified movie"""

    searchURL = config.searchURLPattern.format(story=story)
    cprint(f'Searching on {config.website}', 'cyan')

    data = requests.get(searchURL)
    soup = BeautifulSoup(data.text, 'html.parser')
    results = []

    for item in soup.select(config.itemSelector):
        link = item.select_one(config.linkSelector)
        title = item.select_one(config.titleSelector)
        results.append(SearchResult(title.text, link['href']))

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
    # Load website configs
    cfgData = loadConfig("config.json")
    configs = []
    for data in cfgData:
        configs.append(WebsiteConfig(data['website'], data['searchURLPattern'],
                       data['itemSelector'], data['linkSelector'], data['titleSelector']))

    # For all websites, search / scrap
    story = argv[0]
    results = []
    for config in configs:
        results = results + search(story, config)

    # Sort results by relevance
    sorted = sortResults(story, results)

    # Display results
    print('\n')
    cprint(f'Found {len(sorted)} results accross {len(configs)} websites:', 'green')

    for result in sorted:
        print(result)


if __name__ == '__main__':
    main(sys.argv[1:])

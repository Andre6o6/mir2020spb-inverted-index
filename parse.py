"""This module implements parsing song lyrics from Genius.com.
"""
import argparse
import os
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple

GENIUS_API_TOKEN = os.environ['GENIUS_API_TOKEN']


def get_artist_id(artist_name: str) -> int:
    """Get artist id corresponding to given name.

    Args:
        artist_name: Artist or band name.

    Returns:
        Artist ID.

    """
    base_url = "https://api.genius.com"
    headers = {"Authorization": "Bearer " + GENIUS_API_TOKEN}
    search_url = "{}/search?q={}".format(base_url, artist_name)
    response = requests.get(search_url, headers=headers)
    hits = response.json()["response"]["hits"]
    for hit in hits:
        if (
            hit["result"]["primary_artist"]["name"].lower()
            == artist_name.lower()
        ):
            id = hit["result"]["primary_artist"]["id"]
            return id


def get_songs_page(artist_id: int, page: int) -> requests.models.Response:
    """Request a page (with 20 songs per page) of artist with certain id.

    Args:
        artist_id: Artist ID.
        page: Page number to request.

    Returns:
        Requst response.

    """
    url = "https://api.genius.com/artists/{}/songs?page={}".format(
        artist_id, page
    )
    headers = {"Authorization": "Bearer " + GENIUS_API_TOKEN}
    response = requests.get(url, headers=headers)
    return response


def get_songs(artist_id: int) -> List[Tuple[str, str]]:
    """Get a list of all songs' urls of artist with certain id.

    Args:
        artist_id: Artist ID.

    Returns:
        List of (song title, song url) for all artist' songs.

    """
    page = 1
    songs = []
    while page:
        response = get_songs_page(artist_id, page)
        response = response.json()["response"]
        for song in response["songs"]:
            if song["primary_artist"]["id"] == artist_id:
                songs.append((song["title"], song["url"]))
        page = response["next_page"]
    return songs


def scrape_song_lyrics(url: str) -> str:
    """Scrape song text from song web page.

    Args:
        url: Song url.

    Returns:
        Song text.

    """
    try:
        page = requests.get(url)
        html = BeautifulSoup(page.text, "html.parser")
        lyrics = html.find("div", class_="lyrics").get_text()
        # remove identifiers like [chorus], [verse], etc
        lyrics = re.sub(r"[\(\[].*?[\)\]]", "", lyrics)
        # remove empty lines
        lyrics = os.linesep.join([s for s in lyrics.splitlines() if s])
    except AttributeError:
        lyrics = None
    return lyrics


def arg_parse() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Parser")
    parser.add_argument(
        "--artists",
        dest="artists_file",
        help="Text file containing artists' names",
        default="bands.txt",
        type=str,
    )
    parser.add_argument(
        "--save_dir",
        dest="save_dir",
        help="Directory for saving parsed files",
        default="lyrics",
        type=str,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = arg_parse()

    artists_list = []
    with open(args.artists_file, "r") as f:
        artists_list = f.read().splitlines()

    for artist_name in artists_list:
        artist_id = get_artist_id(artist_name)
        if not artist_id:
            print("{} not found".format(artist_name))
            continue

        print("Collecting {} songs".format(artist_name))
        os.mkdir("{}/{}".format(args.save_dir, artist_name))

        songs = get_songs(artist_id)
        for (song_name, song_url) in songs:
            song_name = re.sub(
                r"/", "_", song_name
            )  # remove '/' from song name
            text = scrape_song_lyrics(song_url)
            if text:
                with open(
                    "{}/{}/{}.txt".format(
                        args.save_dir, artist_name, song_name
                    ),
                    "w",
                ) as f:
                    f.write(text)

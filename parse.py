import requests
from bs4 import BeautifulSoup
import os
import re
import argparse

GENIUS_API_TOKEN='zDRVkBx0XfCETizJ7PSjDq7BmAWzNiIxGxeA9TIZXZbuWWLxVBY7GIqY9BJQY9jK'

def get_artist_id(artist_name):
    base_url = 'https://api.genius.com'
    headers = {'Authorization': 'Bearer ' + GENIUS_API_TOKEN}
    search_url = "{}/search?q={}".format(base_url, artist_name)
    response = requests.get(search_url, headers=headers)
    hits = response.json()['response']['hits']
    for hit in hits:
        if hit['result']['primary_artist']['name'].lower() == artist_name.lower():
            id = hit['result']['primary_artist']['id']
            return id


def get_songs_page(artist_id, page):
    url = "https://api.genius.com/artists/{}/songs?page={}".format(artist_id, page)
    headers = {'Authorization': 'Bearer ' + GENIUS_API_TOKEN}
    response = requests.get(url, headers=headers)
    return response


def get_songs(artist_id):
    page = 1
    songs = []
    while page:
        response = get_songs_page(artist_id, page)
        response = response.json()['response']
        for song in response['songs']:
            if song['primary_artist']['id'] == artist_id:
                songs.append((song['title'], song['url']))
        page = response['next_page']
    return songs


def scrape_song_lyrics(url):
    try:
        page = requests.get(url)
        html = BeautifulSoup(page.text, 'html.parser')
        lyrics = html.find('div', class_='lyrics').get_text()
        #remove identifiers like [chorus], [verse], etc
        lyrics = re.sub(r'[\(\[].*?[\)\]]', '', lyrics)
        #remove empty lines
        lyrics = os.linesep.join([s for s in lyrics.splitlines() if s])
    except:
        lyrics = None
    return lyrics


def arg_parse():
    parser = argparse.ArgumentParser(description='Parser')
    parser.add_argument("--artists", dest = 'artists_file',
                        help = "Text file containing artists' names",
                        default = "bands.txt", type = str)
    parser.add_argument("--save_dir", dest = 'save_dir',
                        help = "Directory for saving parsed files",
                        default = "lyrics", type = str)
    return parser.parse_args()


if __name__ == "__main__":
    args = arg_parse()
    
    artists_list = []
    with open(args.artists_file, 'r') as f:
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
            song_name = re.sub(r'/', '_', song_name)	#remove '/' from song name
            text = scrape_song_lyrics(song_url)
            if text:
                with open("{}/{}/{}.txt".format(args.save_dir, artist_name, song_name), 'w') as f:
                    f.write(text)
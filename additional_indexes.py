"""This module implements additional indexes, such as index over song names.
"""
import argparse
import shelve
from collections import defaultdict
from gensim.parsing.porter import PorterStemmer
from typing import List, Any


def pretty_doc(filename: str) -> str:
    """Convert filename to pretty string 'band - song'."""
    band, name = filename.split("/")[-2:]
    name = name.split(".")[0]
    return "{} - {}".format(band, name)


def build_name_index(
    docs: List[str], stemmer: PorterStemmer
) -> None:
    """Build index from list of song names."""
    index_names = defaultdict(dict)
    for docId, doc in enumerate(docs):
        for token in pretty_doc(doc).split():
            term = stemmer.stem(token)
            index_names[term][docId] = 1
    with shelve.open("index_names") as index:
        index.update(index_names)


def arg_parse() -> Any:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Additional indexes")
    parser.add_argument(
        "--root",
        dest="root",
        help="Lyrics root directory",
        default="lyrics/",
        type=str,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = arg_parse()
    docs = [
        dir + "/" + f
        for dir in os.listdir(args.root)
        for f in os.listdir(args.root + dir)
    ]
    stemmer = PorterStemmer()
    build_name_index(docs, stemmer)

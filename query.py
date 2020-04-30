"""This module implements index querying.
"""
import argparse
import os
import re
import shelve
from gensim.parsing.porter import PorterStemmer
from math import log2
from merge_operations import or_postings, and_postings, not_postings
from typing import List, Dict, Tuple

Posting = Tuple[int, float]


class Indexer:
    """Class that implements querying and printing results.

    Attributes:
        root: Directory where songs lyrics is.
        docs: List of documents filenames, that is used to get docID.
        word_count: Length of each document.
        stemmer: Gensim porter stemmer.
        index: Index file descriptor.

    """

    def __init__(
        self, docs: List[str], index_path: str, root: str = "lyrics/"
    ) -> None:
        """Initialize Indexer by assigning attributes and opening index file.

        Args:
            docs: List of documents filenames.
            index_path: Path to index file.
            root: Directory where songs lyrics is.

        """
        self.root = root
        self.docs = docs
        self.stemmer = PorterStemmer()
        self.get_word_count()
        self.index = shelve.open(index_path)

    def get_word_count(self) -> None:
        """Get length of each document."""
        self.word_count = []
        for _, doc in enumerate(self.docs):
            with open(self.root + doc, "r") as f:
                self.word_count.append(sum(len(line.split()) for line in f))

    def tfidf(self, posting: Dict[int, int]) -> List[Posting]:
        """Calculate tf-idf for documents in posting list.

        Args:
            posting: Posting list with term frequences of some term.

        Returns:
            List of (docID, tf-idf score), sorted by docID.

        """
        return [
            (k, v / self.word_count[k] * log2(len(self.docs) / len(posting)))
            for k, v in sorted(posting.items())
        ]

    def query_boolean(self, tokens: List[str]) -> List[Posting]:
        """Recursively parse boolean query in DNF.

        Args:
            tokens: List of tokens.

        Returns:
            List of (docID, tf-idf score) of query hits.

        """
        try:
            split_idx = tokens.index("OR")
            return or_postings(
                self.query_boolean(tokens[:split_idx]),
                self.query_boolean(tokens[split_idx + 1:]),
            )
        except ValueError:
            pass
        try:
            split_idx = tokens.index("AND")
            return and_postings(
                self.query_boolean(tokens[:split_idx]),
                self.query_boolean(tokens[split_idx + 1:]),
            )
        except ValueError:
            pass
        try:
            split_idx = tokens.index("NOT")
            return not_postings(
                self.query_boolean(tokens[split_idx + 1:]), len(self.docs)
            )
        except ValueError:
            pass
        term = self.stemmer.stem(tokens[0])
        try:
            posting = self.tfidf(self.index[term])
        except KeyError:
            return []
        return posting

    def render_file(
        self, tokens: List[str], filename: str, offset: int = 20
    ) -> None:
        """Print song name and text snippet.

        Args:
            tokens: List of query tokens.
            filename: Song filename.
            offset: How much to extend text snippet in symbols.

        """
        # Print band and song name
        print("\033[4m{}\033[0m:".format(pretty_doc(filename)))
        # Try to find term in song text
        with open(self.root + filename) as f:
            text = "".join(f.readlines())
            lowered_text = text.lower()
            for token in tokens:
                try:
                    w = self.stemmer.stem(token)
                    w_match = re.search(r"\b{}\w*\b".format(w), lowered_text)
                    l_match = re.search(r"\b{}.*?\n".format(w), lowered_text)
                    if w_match.start() > offset:
                        print("...", end="")
                    start = max(0, w_match.start() - offset)
                    print(
                        "{}\033[1m{}\033[0m{}".format(
                            text[start:w_match.start()],
                            text[w_match.start():w_match.end()],
                            text[w_match.end():l_match.end() - 1],
                        )
                    )
                except AttributeError:
                    print("-")

    def render(
        self, tokens: List[str], hits: List[Posting], count: int
    ) -> None:
        """Print the results of query.

        Args:
            tokens: List of query tokens.
            hits: Query results as a list of (docID, tf-idf score).
            count: How many hits to print.

        """
        if not hits:
            print("Nothing found")
            return
        tokens = [t for t in tokens if t not in ["AND", "OR", "NOT"]]
        print("{} hits found.\n".format(len(hits)))
        for docId, v in hits[:count]:
            print("[relevance = {:.3f}]".format(v))
            self.render_file(tokens, self.docs[docId])
            print()

    def query(self, query: str, count: int = 10) -> None:
        """Query index and print results, sorted by tf-idf.

        Args:
            query: Query string.
            count: How many hits to print.

        """
        tokens = query.split()
        hits = self.query_boolean(tokens)
        hits = sorted(hits, key=lambda item: item[1], reverse=True)
        self.render(tokens, hits, count)

    def close(self) -> None:
        """Close index file."""
        self.index.close()


def pretty_doc(filename: str) -> str:
    """Convert filename to pretty string 'band - song'.

    Args:
        filename: Path to a file.

    Returns:
        Pretty formatted song name.

    """
    band, name = filename.split("/")[-2:]
    name = name.split(".")[0]
    return "{} - {}".format(band, name)


def arg_parse() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Querying inverted index")
    parser.add_argument(
        "--root",
        dest="root",
        help="Lyrics root directory",
        default="lyrics/",
        type=str,
    )
    parser.add_argument(
        "--index", dest="index", help="Index", default="index", type=str
    )
    parser.add_argument(
        "--q", dest="query", help="Query", default="", type=str
    )
    parser.add_argument(
        "--count",
        dest="count",
        help="How many hits to show",
        default=10,
        type=int,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = arg_parse()
    docs = [
        dir + "/" + f
        for dir in os.listdir(args.root)
        for f in os.listdir(args.root + dir)
    ]
    docs = sorted(docs)

    index = Indexer(docs, args.index, args.root)
    index.query(args.query, args.count)

    index.close()

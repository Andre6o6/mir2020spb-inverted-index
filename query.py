import os
import argparse
import shelve
from math import log2
from gensim.parsing.porter import PorterStemmer
from merge_operations import *


class Indexer:
    root = ""
    docs = []
    word_count = []
    stemmer = None
    index = None

    def __init__(self, docs, index_path, root="lyrics/"):
        self.root = root
        self.docs = docs
        self.stemmer = PorterStemmer()
        self.get_word_count()
        self.index = shelve.open(index_path)

    def get_word_count(self):
        self.word_count = []
        for _, doc in enumerate(self.docs):
            with open(self.root + doc, "r") as f:
                self.word_count.append(sum(len(line.split()) for line in f))

    def tfidf(self, posting):
        return [
            (k, v / self.word_count[k] * log2(len(self.docs) / len(posting)))
            for k, v in sorted(posting.items())
        ]

    def query_boolean(self, tokens):
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
                self.query_boolean(tokens[split_idx + 1:], len(self.docs))
            )
        except ValueError:
            pass
        term = self.stemmer.stem(tokens[0])
        try:
            posting = self.tfidf(self.index[term])
        except KeyError:
            return []
        return posting

    def render_file(self, tokens, file, offset=20):
        # Print band and song name
        print("\033[4m{}\033[0m:".format(pretty_doc(file)))
        # Try to find term in song text
        with open(self.root + file) as f:
            text = "".join(f.readlines())
            lowered_text = text.lower()
            for token in tokens:
                try:
                    n = lowered_text.index(self.stemmer.stem(token))
                    if n > offset:
                        print("...", end="")
                    start = max(0, n - offset)
                    end = lowered_text.index("\n", n)
                    print(
                        "{}\033[1m{}\033[0m{}".format(
                            text[start:n],
                            text[n:n + len(token)],
                            text[n + len(token):end],
                        )
                    )
                except ValueError:
                    print("-")

    def render(self, tokens, hits, count):
        if not hits:
            print("Nothing found")
            return

        tokens = [t for t in tokens if t not in ["AND", "OR", "NOT"]]
        for docId, v in hits[:count]:
            print("[{:.3f}]".format(v))
            self.render_file(tokens, self.docs[docId])
            print()

    def query(self, query, count=10):
        tokens = query.split()
        hits = self.query_boolean(tokens)
        hits = sorted(hits, key=lambda item: item[1], reverse=True)
        self.render(tokens, hits, count)

    def close(self):
        self.index.close()


def pretty_doc(filename):
    band, name = filename.split("/")[-2:]
    name = name.split(".")[0]
    return "{} - {}".format(band, name)


def arg_parse():
    parser = argparse.ArgumentParser(description="Querying inverted index")
    parser.add_argument(
        "--root", dest="root", help="Lyrics root directory", default="lyrics/", type=str
    )
    parser.add_argument(
        "--index", dest="index", help="Index", default="index", type=str
    )
    parser.add_argument("--q", dest="query", help="Query", default="", type=str)
    parser.add_argument(
        "--count", dest="count", help="How many hits to show", default=10, type=int
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = arg_parse()
    docs = [
        dir + "/" + f
        for dir in os.listdir(args.root)
        for f in os.listdir(args.root + dir)
    ]

    index = Indexer(docs, args.index, args.root)
    index.query(args.query, args.count)

    index.close()

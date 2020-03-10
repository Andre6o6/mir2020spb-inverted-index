import os
import argparse
import shelve
from math import log2
from gensim.parsing.porter import PorterStemmer
from .merge_operations import *

def tfidf(posting):
    return [(k, v/word_count[k] * log2(len(docs)/len(posting)))
            for k,v in sorted(posting.items())]


def query_boolean(index, query, stemmer):
    op = ""
    prev_posting = []
    for token in query.split():
        #Save and skip operations tokens
        if token in ['AND', 'NOT', 'OR']:
            op += token
            continue

        #Get posting list for new query term
        term = stemmer.stem(token)
        posting = tfidf(index[term])

        #Merge posting list according to operation
        if op == "":
            prev_posting = posting
        elif op == "NOT":
            prev_posting = not_postings(posting, len(docs))
        elif op == "AND":
            prev_posting = and_postings(prev_posting, posting)
        elif op == "OR":
            prev_posting = or_postings(prev_posting, posting)
        elif op == "ANDNOT":
            prev_posting = not_and_postings(posting, prev_posting)
        elif op == "ORNOT":
            prev_posting = not_or_postings(posting, prev_posting)
        else:
            raise Exception("Invalid operation: " + op)
        op = ""
    return sorted(prev_posting, key=lambda item: item[1], reverse=True)


def pretty_doc(filename):
    band, name = filename.split('/')[-2:]
    name = name.split('.')[0]
    return "{} - {}".format(band, name)


def render_file(tokens, file, root='lyrics/', offset=20):
    print("\033[4m{}\033[0m:".format(pretty_doc(file)))
    with open(root+file) as f:
        text = "".join(f.readlines())
        lowered_text = text.lower()
        for token in tokens:
            try:
                n = lowered_text.index(stemmer.stem(token))
                if n > offset:
                    print("...", end='')
                start = max(0, n - offset)
                end = lowered_text.index('\n', n)
                print("{}\033[1m{}\033[0m{}".format(text[start:n],
                                                    text[n:n+len(token)],
                                                    text[n+len(token):end]))
            except:
                print("...")


def render(query, posting, count=10):
    tokens = [t for t in query.split() if t not in ['AND', 'OR', 'NOT']]
    for docId,v in posting[:count]:
        print("[{:.3f}]".format(v))
        render_file(tokens, docs[docId])
        print()


def arg_parse():
    parser = argparse.ArgumentParser(description='Querying inverted index')
    parser.add_argument("--root", dest = 'root',
                        help = "Lyrics root directory",
                        default = "lyrics/", type = str)
    parser.add_argument("--index", dest = 'index',
                        help = "Index",
                        default = "index", type = str)
    parser.add_argument("--q", dest = 'query',
                        help = "Query",
                        default = "", type = str)
    parser.add_argument("--count", dest = 'count',
                        help = "How many hits to show",
                        default = 10, type = int)
    return parser.parse_args()


if __name__ == "__main__":
    args = arg_parse()
    docs = [dir+'/'+f for dir in os.listdir(args.root) for f in os.listdir(args.root+dir)]
    stemmer = PorterStemmer()
    
    #Word count in each document for tf-idf
    word_count = []
    for _, doc in enumerate(docs):
        with open(args.root+doc, 'r') as f:
            word_count.append(sum(len(line.split()) for line in f))

    with shelve.open(args.index) as index:
        hits = query_boolean(index, args.query, stemmer)
        render(args.query, hits, args.count)
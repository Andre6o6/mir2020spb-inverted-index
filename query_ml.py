import argparse
import os
import re
import numpy as np
from query import Indexer
from embedder import Embedder, get_text_reduced
from merge_operations import not_and_postings
from scipy.spatial.distance import cosine

def query_expand(query: str) -> str:
    m = re.search(r" NOT", query)
    if m:
        q_pos = query[:m.start()]
        q_neg = query[m.end():].strip('()')
    else:
        q_pos = query
        q_neg = None
    return q_pos, q_neg


def query_reduce(query: str) -> str:
    query = re.sub(r"NOT", "", query)
    query = re.sub(r"[()]", "", query)
    return query


def batch_embed(embedder: Embedder, texts: [str], batch_size: int) -> np.ndarray:
    embeddings = np.zeros((len(texts), 768))
    
    iters = len(texts)//batch_size
    if  len(texts)%batch_size > 0:
        iters += 1

    for i in range(iters):
        batch = texts[i*batch_size:(i+1)*batch_size]
        emb_batch = embedder.embed(batch)
        embeddings[i*batch_size:(i+1)*batch_size] = emb_batch
    return embeddings


def arg_parse() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Querying with ML")
    parser.add_argument(
        "--root",
        dest="root",
        help="Lyrics root directory",
        default="lyrics/",
        type=str,
    )
    parser.add_argument(
        "--index", dest="index", help="Index file", default="index", type=str
    )
    parser.add_argument(
        "--q",
        dest="query",
        help="Query string. Syntax: 'word1 word2 NOT(word3 word4)'",
        default="",
        type=str,
    )
    parser.add_argument(
        "--L0",
        dest="l0_size",
        help="How many hits from L0 are reranked with ML",
        default=100,
        type=int,
    )
    parser.add_argument(
        "--L1",
        dest="l1_size",
        help="How many hits to show",
        default=20,
        type=int,
    )
    parser.add_argument(
        "--bs",
        dest="batch_size",
        help="Batch size to use in L1, decrease if GPU rans out of memory",
        default=100,
        type=int,
    )
    return parser.parse_args()


def main():
    args = arg_parse()
    docs = [
        os.path.join(dir, f)
        for dir in os.listdir(args.root) 
        for f in os.listdir(os.path.join(args.root, dir))
    ]
    docs = sorted(docs)
    
    index = Indexer(docs, args.index, args.root)
    embedder = Embedder()
    
    #L0
    q_pos, q_neg = query_expand(args.query)
    #Get all OR-ed tokens
    q_pos_expand = re.sub(r" ", " OR ", q_pos)
    hits = index.query_boolean(q_pos_expand.split())
    #Remove all NOT-ed tokens
    if q_neg:
        for token in q_neg.split():
            term = index.stemmer.stem(token)
            try:
                not_posting = index.tfidf(index.index[term])
            except KeyError:
                not_posting = []
            hits = not_and_postings(not_posting, hits)
    
    if not hits:
        print("nothing found")
        return
    
    hits = sorted(hits, key=lambda item: item[1], reverse=True)
    hits = hits[:args.l0_size]
    
    #L1
    doc_ids = [x[0] for x in hits]
    filenames = [os.path.join(args.root, docs[i]) for i in doc_ids]
    texts = [get_text_reduced(x, maxlen=512) for x in filenames]
    
    #Embed in batches if GPU memory is small
    if args.batch_size >= args.l0_size:
        embeddings = embedder.embed(texts)
    else:
        embeddings = batch_embed(embedder, texts, args.batch_size)
    query_emb = embedder.embed([q_pos])[0]
    dist_cos = [cosine(query_emb, e) for e in embeddings]
    idx_cos = np.argsort(dist_cos)
    
    #Render
    q_red = query_reduce(args.query)
    resorted = [doc_ids[i] for i in idx_cos]
    for i,id in enumerate(resorted[:args.l1_size]):
        print("\n{}:".format(i))
        index.render_file(q_red.split(), docs[id])
        orig_pos = idx_cos[i]
        print("\tL0 rank = {}; tf-idf = {:.3f}; cos-sim = {:.3f}".format(orig_pos, hits[orig_pos][1], 1-dist_cos[orig_pos]))

if __name__ == "__main__":
    main()
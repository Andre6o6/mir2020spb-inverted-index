import os
from query import Indexer
from embedder import Embedder
from scipy.spatial.distance import cosine, euclidean

#FIXME mb this should be in embedder.py, as it is actually its preprocessing
def get_text(filename):
    with open(filename, 'r')as f:
        lines = [line.rstrip() for line in f]
        text = ' '.join(x for x in lines if x != "")
    return text


def main():
    #TODO clean up
    
    root = "lyrics/"
    docs = [
        dir+'/'+f 
        for dir in os.listdir(root) 
        for f in os.listdir(root+dir)
    ]
    docs = sorted(docs)
    
    index = Indexer(docs, "index", root)
    embedder = Embedder()
    l0_count=20
    
    #L0
    #TODO expand free-text query to OR, add support for NOT 
    q = "nothing OR else OR matters"
    tokens = q.split()
    hits = index.query_boolean(tokens)
    hits = sorted(hits, key=lambda item: item[1], reverse=True)
    
    doc_ids = [x[0] for x in hits[:l0_count]]
    filenames = [root + docs[i] for i in doc_ids]
    texts = [get_text(x) for x in filenames]
    
    #L1
    q = "nothing else matters"  #FIXME remove ORs
    embeddings = embedder.embed(texts)
    query_emb = embedder.embed([q])[0]
    
    dist_euq = [euclidean(query_emb, e) for e in embeddings]
    dist_cos = [cosine(query_emb, e) for e in embeddings]
    idx_euq = np.argsort(dist_euq)
    idx_cos = np.argsort(dist_cos)
    
    #Render
    indexes = idx_cos
    resorted = [doc_ids[i] for i in indexes]

    for i,id in enumerate(resorted):
        print("\n{}:".format(i))
        index.render_file(q.split(), docs[id])

        orig_pos = indexes[i]
        print("\tOriginal rank: ", orig_pos)
        print("\ttf-idf = ", hits[orig_pos][1])
        print("\tcos-sim = ", 1-dist_cos[orig_pos])

if __name__ == "__main__":
    main()
"""This module implements duplicate search.

The key idea is to get embeddings for all texts in corpus, and then use some
similarity search to find the closest neighbours for every embedding,
thresholded with some value.
"""
import argparse
import faiss
import Levenshtein
import numpy as np
import os
import pickle
from collections import defaultdict
from embedder import Embedder, get_text_reduced
from sklearn.preprocessing import normalize
from tqdm import trange
from typing import List, Dict, Tuple


def calc_embeddings(
    docs: List[str], batch_size: int, root: str
) -> np.ndarray:
    """Calculate embeddings (in batches).

    Args:
        docs: List of documents filenames.
        batch_size: Batch size.
        root: Root directory.

    Returns:
        Numpy array of (N, 768) of texts embeddings.

    """
    embedder = Embedder()
    all_embeddings = np.zeros((len(docs), 768), dtype=np.float32)

    iters = len(docs) // batch_size
    if len(docs) % batch_size > 0:
        iters += 1

    for i in trange(iters):
        batch = docs[i * batch_size: (i + 1) * batch_size]
        filenames = [os.path.join(root, doc) for doc in batch]
        texts = [get_text_reduced(x, maxlen=512) for x in filenames]
        embeddings = embedder.embed(texts)
        all_embeddings[i * batch_size: (i + 1) * batch_size] = embeddings
    return all_embeddings


def get_embeddings(docs: List[str], args: argparse.Namespace) -> np.ndarray:
    """Load cached (or calculate) embeddings and normalize them.

    Args:
        docs: List of documents filenames.
        args: Command-line arguments.

    Returns:
        Numpy array of (N, 768) of normalized embeddings.

    """
    try:
        all_embeddings = np.load(args.emb_file)
    except FileNotFoundError:
        print("Embeddings not found. Calculating embeddings...")
        all_embeddings = calc_embeddings(docs, args.batch_size, args.root)
        np.save(args.emb_file, all_embeddings)
    all_embeddings = all_embeddings.astype(np.float32)
    all_embeddings = normalize(all_embeddings, axis=1)
    return all_embeddings


def get_bands(docs: List[str]) -> Dict[str, Tuple[int, int]]:
    """Get unique bands and corresponding start docID and end docID.

    Args:
        docs: List of documents filenames.

    Returns:
        Dictionary of bands' start and end docIDs.

    """
    bands = {}
    last_band = ""
    for i, d in enumerate(docs):
        band = d.split("/")[0]
        if last_band != band:
            if last_band != "":
                start = bands[last_band]
                bands[last_band] = (start, i)
            last_band = band
            bands[band] = i
    return bands


def get_band_duplicates(
    duplicates: Dict[int, List[int]],
    band_name: str,
    bands: Dict[str, Tuple[int, int]],
) -> Dict[int, List[int]]:
    """Get duplicates of songs of a band.

    Args:
        duplicates: Dictionary of duplicates.
        band_name: Name of the band.
        bands: Dictionary of bands' start and end docIDs.

    Returns:
        Subdictionary of duplicates of songs of a band.

    """
    # Spellcheck against bands names
    dists = [
        Levenshtein.distance(band_name.lower(), b.lower())
        for b in bands.keys()
    ]
    idx = np.argmin(dists)
    if dists[idx] > len(band_name) // 2:
        print("Band not found")
        return
    band_name = list(bands.keys())[idx]

    start, end = bands[band_name]
    duplicates_batch = {
        k: v for k, v in duplicates.items() if k >= start and k < end
    }
    return duplicates_batch


def print_duplicates(docs: List[str], duplicates: Dict[int, List[int]]):
    """Print names of songs from dictionary of duplicates.

    Args:
        docs: List of documents filenames.
        duplicates: Dictionary of duplicates.

    """
    for k, v in duplicates.items():
        print(docs[k])
        for d in v:
            print("\t" + docs[d])


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
        "--emb",
        dest="emb_file",
        help="Numpy file with embeddings for all texts",
        default="embeddings.npy",
        type=str,
    )
    parser.add_argument(
        "--dict",
        dest="duplicate_dict",
        help="Pickled duplicate dictionary",
        default="duplicates.pkl",
        type=str,
    )
    parser.add_argument(
        "--bs",
        dest="batch_size",
        help="Batch size to use, decrease if GPU rans out of memory",
        default=10,
        type=int,
    )
    parser.add_argument(
        "--k",
        dest="k",
        help="Maximum number of duplicates",
        default=5,
        type=int,
    )
    parser.add_argument(
        "--threshold",
        dest="threshold",
        help="Cos-sim threshold for duplicate",
        default=0.99,
        type=float,
    )
    parser.add_argument(
        "--out",
        dest="out_file",
        help="Text file where all duplicates will be written",
        default="duplicates.txt",
        type=str,
    )
    parser.add_argument(
        "--save",
        help="Write all duplicates in text file",
        action="store_true",
    )
    parser.add_argument(
        "--band",
        dest="band_name",
        help="Band name to find duplicates for",
        default="",
        type=str,
    )
    parser.add_argument(
        "--find",
        dest="find_file",
        help="Find duplicates for specified text",
        default="",
        type=str,
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

    try:
        # Load duplicates dict
        with open(args.duplicate_dict, "rb") as f:
            duplicates = pickle.load(f)
    except FileNotFoundError:
        # Get BERT embeddings for all texts
        all_embeddings = get_embeddings(docs, args)
        # kNN then with faiss
        print("Duplicates dict not found. Calculating duplicates dict...")
        index = faiss.IndexFlatIP(768)
        index.add(all_embeddings)
        D, I = index.search(all_embeddings, args.k)

        duplicates = defaultdict(list)
        for i, row in enumerate(D):
            for j in range(1, args.k):
                if row[j] > args.threshold:
                    duplicates[i].append(I[i][j])

        with open(args.duplicate_dict, "wb") as f:
            pickle.dump(duplicates, f)

    # Write all duplicates into text file
    if args.save:
        with open(args.out_file, "w") as f:
            for k, v in duplicates.items():
                if v[0] > k:
                    f.write(docs[k] + "\n")
                    for d in v:
                        f.write("\t" + docs[d] + "\n")

    # Print duplicates in some band's songs
    if args.band_name != "":
        bands = get_bands(docs)
        d = get_band_duplicates(duplicates, args.band_name, bands)
        if d:
            print_duplicates(docs, d)

    # Find duplicates for some song
    if args.find_file != "":
        try:
            # Search file in duplicates dict
            name = os.path.join(*args.find_file.split("/")[-2:])
            idx = docs.index(name)

            if not duplicates[idx]:
                print("No duplicates found")
                return

            for d in duplicates[idx]:
                print(docs[d])
            print("... are duplicates of ", args.find_file)
        except ValueError:
            print("File is not found in duplicates dict.")
            # TODO and I'm to lazy to do proper embedding search


if __name__ == "__main__":
    main()

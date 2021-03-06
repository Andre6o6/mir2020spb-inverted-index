"""This module implements Single-pass in-memory Indexing.
"""
import argparse
import os
import shelve
import string
import sys
from gensim.parsing.porter import PorterStemmer
from typing import List, Dict, Tuple, Iterator


def token_stream(files: List[str]) -> Iterator[Tuple[int, str]]:
    """Convert text files to a stream of docID-tokens pairs.

    Args:
        files: List of filepaths.

    Yields:
        Pair of docID, token.

    """
    for fileno, filepath in enumerate(files):
        with open(filepath, "r") as f:
            for line in f:
                line = line.translate(
                    str.maketrans("", "", string.punctuation)
                ).rstrip()
                for token in line.split():
                    yield fileno, token


def spimi_invert(
    files: List[str],
    stemmer: PorterStemmer,
    blocks_dir: str,
    memory_available: int,
) -> List[str]:
    """SPIMI-Invert procedure.

    Collect terms, docIDs, term-frequencies into a block (dictionary
    of dictionaries) that fits in available memory, write each block's
    dictionary to disk, and start a new dictionary for the next block.

    Args:
        files: List of filepaths.
        stemmer: Gensim porter stemmer.
        blocks_dir: Directory where blocks are saved.
        memory_available: Available memory in bytes.

    Returns:
        List of filenames of saved blocks.

    """
    memory_used = 0
    outputed_blocks = []
    block_index = 0
    dictionary = {}
    for docId, token in token_stream(files):
        memory_used += sys.getsizeof(token)

        term = stemmer.stem(token)
        if term not in dictionary.keys():
            dictionary[term] = {}
        if docId not in dictionary[term].keys():
            dictionary[term][docId] = 0
        dictionary[term][docId] += 1  # save term freq. in document

        if memory_used > memory_available:
            # Sort terms and write to disk
            with shelve.open(blocks_dir + "block" + str(block_index)) as f:
                for k in sorted(dictionary.keys()):
                    f[k] = dictionary[k]
            outputed_blocks.append("block" + str(block_index))
            block_index += 1
            memory_used = 0
            dictionary = {}

    # Save last block
    if dictionary:
        with shelve.open(blocks_dir + "block" + str(block_index)) as f:
            for k in sorted(dictionary.keys()):
                f[k] = dictionary[k]
        outputed_blocks.append("block" + str(block_index))
    return outputed_blocks


def merge_dicts(
    dict1: Dict[int, int], dict2: Dict[int, int]
) -> Dict[int, int]:
    """Merge ans sort two dictionaries.

    Args:
        dict1: One dictionary.
        dict2: Another dictionary.

    Returns:
        Merged dictionary.

    """
    if dict1 == {}:
        return dict2
    # Merge
    for k, v in dict2.items():
        if k in dict1.keys():
            dict1[k] += v
        else:
            dict1[k] = v
    # Sort
    return {k: dict1[k] for k in sorted(dict1)}


def merge_all_blocks(
    outputed_blocks: List[str], blocks_dir: str = "blocks/"
) -> None:
    """Merge the resulting blocks of SPIMI-Invert.

    Open all blocks simultaneously, then read a term from each block,
    choose minimal term and write merged posting lists corresponding
    to this term to disk. Then read next term only from blocks where
    minimal term was. Repeat until all blocks are emptied.

    Args:
        outputed_blocks: List of filenames of saved blocks.
        blocks_dir: Directory where blocks are saved.

    """
    files = [shelve.open(blocks_dir + b) for b in outputed_blocks]
    iterators = [iter(sorted(f.keys())) for f in files]
    buffer = [None for i in iterators]

    output = shelve.open("index")
    while True:
        # Iterate in reverse order for removing
        for i in range(len(iterators))[::-1]:
            # Skip if buffer for this block is not empty
            if buffer[i] is not None:
                continue

            # Read next (term, posting_list) from block
            try:
                k = next(iterators[i])
                buffer[i] = (k, files[i][k])  # put into buffer
            except (
                StopIteration,
                KeyError,
            ):  # remove emptied block from lists
                iterators.pop(i)
                buffer.pop(i)
                continue

        # Stop if no more blocks left to merge
        if not iterators:
            break

        # Merge and save postings corresponding to minimal term
        min_term = min([b[0] for b in buffer])
        dictionary = {}
        for i, (termId, doc_dict) in enumerate(buffer):
            if termId == min_term:
                dictionary = merge_dicts(dictionary, doc_dict)
                buffer[i] = None  # clear buffer
        output[min_term] = dictionary

    for f in files:
        f.close()
    output.close()


def arg_parse() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="inverted index via SPIMI")
    parser.add_argument(
        "--root",
        dest="root",
        help="Root directory",
        default="lyrics/",
        type=str,
    )
    parser.add_argument(
        "--memory",
        dest="memory_mb",
        help="Available memory in Mb",
        default=10,
        type=int,
    )
    parser.add_argument(
        "--temp_dir",
        dest="blocks_dir",
        help="Temporary directory for saving blocks",
        default="blocks/",
        type=str,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = arg_parse()
    # Get list of documents and use index as docID
    docs = [
        dir + "/" + f
        for dir in os.listdir(args.root)
        for f in os.listdir(args.root + dir)
    ]
    docs = sorted(docs)
    with open("docs_list.txt", "w") as f:   # TODO file name to args
        for d in docs:
            f.write(d+'\n')

    files = [args.root + d for d in docs]
    stemmer = PorterStemmer()
    # Generate fitting in memory blocks using SPIMI-Invert
    memory_available = args.memory_mb * 1024 * 1024
    try:
        os.mkdir(args.blocks_dir)
    except FileExistsError:
        pass
    outputed_blocks = spimi_invert(
        files, stemmer, args.blocks_dir, memory_available
    )
    merge_all_blocks(outputed_blocks, args.blocks_dir)

"""This module implements boolean operations on posting lists.
"""
from typing import List, Dict, Tuple, Iterator, Any

Posting = Tuple[int, float]


def and_postings(
    posting1: List[Posting], posting2: List[Posting]
) -> List[Posting]:
    """Intersection of posting lists. x AND y.

    Args:
        posting1: Posting list of (docID, tf-idf score), sorted by docID.
        posting2: Another sorted posting list.

    Returns:
        Sorted posting list of documents containig both terms.

    """
    result = []
    i, j = 0, 0
    while i < len(posting1) and j < len(posting2):
        if posting1[i][0] < posting2[j][0]:
            i += 1
        elif posting1[i][0] > posting2[j][0]:
            j += 1
        else:
            result.append((posting1[i][0], posting1[i][1] + posting2[j][1]))
            i += 1
            j += 1
    return result


def or_postings(
    posting1: List[Posting], posting2: List[Posting]
) -> List[Posting]:
    """Union of posting lists. x OR y.

    Args:
        posting1: Posting list of (docID, tf-idf score), sorted by docID.
        posting2: Another sorted posting list.

    Returns:
        Sorted posting list of documents containig either terms.

    """
    result = []
    i, j = 0, 0
    while i < len(posting1) and j < len(posting2):
        if posting1[i][0] < posting2[j][0]:
            result.append(posting1[i])
            i += 1
        elif posting1[i][0] > posting2[j][0]:
            result.append(posting2[j])
            j += 1
        else:
            # FIXME mb max(., .) instead of sum(., .)
            result.append((posting1[i][0], posting1[i][1] + posting2[j][1]))
            i += 1
            j += 1
    result.extend(posting1[i:])
    result.extend(posting2[j:])
    return result


def not_postings(
    posting: List[Posting], max_docId: int
) -> List[Posting]:
    """Complement of posting list. NOT x.

    Args:
        posting: Posting list of (docID, tf-idf score), sorted by docID.
        max_docId: Last docID.

    Returns:
        Sorted posting list of documents not containig term.

    """
    result = []
    last_docId = -1  # to account for docId=0
    for docId, _ in posting:
        result.extend([(i, 0) for i in range(last_docId + 1, docId)])
        last_docId = docId
    result.extend([(i, 0) for i in range(last_docId + 1, max_docId)])
    return result


def not_and_postings(
    not_posting: List[Posting], posting: List[Posting]
) -> List[Posting]:
    """Optimized NOT x AND y.

    Args:
        not_posting: Posting list of term after NOT, sorted by docID.
        posting: Another sorted posting list.

    Returns:
        Sorted posting list of documents containig term y and not x.

    """
    result = []
    last_docId = 0
    i, j = 0, 0
    while i < len(posting) and j < len(not_posting):
        if posting[i][0] < not_posting[j][0]:
            if last_docId < posting[i][0]:
                result.append(posting[i])
            i += 1
        elif posting[i][0] >= not_posting[j][0]:
            last_docId = not_posting[j][0]
            j += 1
    result.extend([p for p in posting[i:] if last_docId < p[0]])
    return result


def not_or_postings(
    not_posting: List[Posting],
    posting: List[Posting],
    max_docId: int,
) -> List[Posting]:
    """Shortcut for NOT x OR y.

    Args:
        not_posting: Posting list of term after NOT, sorted by docID.
        posting: Another sorted posting list.
        max_docId: Last docID.

    Returns:
        Sorted posting list of documents containig term y or not x.

    """
    return or_postings(not_postings(not_posting, max_docId), posting)

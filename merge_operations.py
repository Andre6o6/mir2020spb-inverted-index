def and_postings(posting1, posting2):
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


def or_postings(posting1, posting2):
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


def not_postings(posting, max_docId):
    result = []
    last_docId = -1  # to account for docId=0
    for docId, _ in posting:
        result.extend([(i, 0) for i in range(last_docId + 1, docId)])
        last_docId = docId
    result.extend([(i, 0) for i in range(last_docId + 1, max_docId)])
    return result


def not_and_postings(not_posting, posting):
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


def not_or_postings(not_posting, posting, max_docId):
    return or_postings(not_postings(not_posting, max_docId), posting)

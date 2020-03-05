import os
from gensim.parsing.porter import PorterStemmer
import string
import pickle
from collections import defaultdict, deque

def merge_dicts(dict1, dict2):
    for k,v in dict2.items():
        if k not in dict1.keys():
            dict1[k] = v
        else:
            dict1[k] = {**dict1[k], **dict2[k]}
    return dict1


def arg_parse():
    parser = argparse.ArgumentParser(description='inverted index via SPIMI')
    parser.add_argument("--root", dest = 'root',
                        help = "Root directory",
                        default = "lyrics/", type = str)
    parser.add_argument("--memory", dest = 'memory_mb',
                        help = "Available memory in Mb",
                        default = 1, type = int)
    return parser.parse_args()


if __name__ == "__main__":
    args = arg_parse()
    docs = [dir+'/'+f for dir in os.listdir(args.root) for f in os.listdir(args.root+dir)]
    stemmer = PorterStemmer()
    
    memory_available = args.memory_mb*1024*1024
    memory_used = 0
    dictionary = defaultdict(dict)
    block_index = 0
    for docId, d in enumerate(docs):
        filepath = root+d
        size = os.stat(filepath).st_size

        if (memory_used + size > memory_available):
            with open('blocks/block'+str(block_index)+'.p', 'wb') as output:
                pickle.dump(dictionary, output, protocol=pickle.HIGHEST_PROTOCOL)
            block_index +=1
            memory_used = 0
            dictionary.clear()

        memory_used += size
        with open(filepath, 'r') as f:
            data = f.read().replace('\n', ' ')
            data = data.translate(str.maketrans('', '', string.punctuation))
            for token in data.split():
                term = stemmer.stem(token)

                if docId not in dictionary[term].keys():
                    dictionary[term][docId] = 0

                dictionary[term][docId] += 1

    #save last block
    if dictionary:
        with open('blocks/block'+str(block_index)+'.p', 'wb') as output:
            pickle.dump(dictionary, output, protocol=pickle.HIGHEST_PROTOCOL)
        dictionary.clear()

    all_blocks = sorted([f for f in os.listdir('blocks/')])
    q = deque(all_blocks)
    i=0
    while len(q)>1:
        #Read first 2 blocks from queue
        with open('blocks/'+q.popleft(), 'rb') as f1:
            block1 = pickle.load(f1)
        with open('blocks/'+q.popleft(), 'rb') as f2:
            block2 = pickle.load(f2)

        #Merge
        new_block = merge_dicts(block1, block2)

        #Save and push merged block into queue
        block_name = 'merged'+str(i)+'.p'
        with open('blocks/'+block_name, 'wb') as f:
            pickle.dump(new_block, f, protocol=pickle.HIGHEST_PROTOCOL)
        q.append(block_name)
        i+=1
    
    with open('index.p', 'wb') as f:
        pickle.dump(new_block, f, protocol=pickle.HIGHEST_PROTOCOL)
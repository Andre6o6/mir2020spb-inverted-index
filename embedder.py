"""Text embedder.

This module implements Embedder class, that uses pretrained DistilBERT
to get text embeddings.
"""
import numpy as np
import torch
import transformers as ppb
from typing import List

def get_text_reduced(filename, maxlen=-1):
    with open(filename, 'r')as f:
        lines = [line.rstrip() for line in f]
        text = ' '.join(x for x in lines if x != "")
        if maxlen > 0:
            text = ' '.join(text.split()[:maxlen])
    return text


class Embedder:
    """Class that is used to get dense text embeddings.

    Attributes:
        device: Specifies, should pytorch use cpu or gpu.
        tokenizer: Pretrained DistilBERT tokenizer.
        model: Pretrained DistilBERT model.

    """

    def __init__(self):
        """Initialize Embedder by loading models and weights."""
        model_class = ppb.DistilBertModel
        tokenizer_class = ppb.DistilBertTokenizer
        pretrained_weights = "distilbert-base-uncased"

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = tokenizer_class.from_pretrained(pretrained_weights)
        self.model = model_class.from_pretrained(pretrained_weights).to(self.device)
    
    def embed(self, texts:List[str]) -> np.ndarray:
        """Get dense embeddings for a collection of texts.

        Args:
            texts: List of texts, striped of '\n' and squashed into one string.

        Returns:
            Numpy array of shape (N, 768) with text embeddings.

        """
        #Tokenize
        tokenized = [self.tokenizer.encode(x, add_special_tokens=True) for x in texts]
        
        #Pad to make everything the same length
        max_len = max(len(x) for x in tokenized)
        padded = np.array([x + [0]*(max_len-len(x)) for x in tokenized])
        mask = np.where(padded != 0, 1, 0)    #mask out padding

        #Feed to BERT
        input_ids = torch.tensor(padded).to(self.device)
        mask = torch.tensor(mask).to(self.device)
        with torch.no_grad():
            last_hidden_states = self.model(input_ids, attention_mask=mask)

        #Get embedding
        #TODO it's emb. of [CLS] token, try different 
        embedding = last_hidden_states[0][:,0,:].cpu().numpy()
        return embedding
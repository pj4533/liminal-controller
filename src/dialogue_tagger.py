# Averaged perceptron inference adapted from NLTK perceptron.py (MIT).
# Copyright NLTK contributors; attribution and license in licenses/nltk-MIT.txt.
import json,time,zipfile,sys,resource
from collections import defaultdict
class Tagger:
 START=['-START-','-START2-'];END=['-END-','-END2-']

 def normalize(self, word):
     """
         Normalization used in pre-processing.
         - All words are lower cased
         - Groups of digits of length 4 are represented as !YEAR;
         - Other digits are represented as !DIGITS
 
         :rtype: str
         """
     if '-' in word and word[0] != '-':
         return '!HYPHEN'
     if word.isdigit() and len(word) == 4:
         return '!YEAR'
     if word and word[0].isdigit():
         return '!DIGITS'
     return word.lower()

 def _get_features(self, i, word, context, prev, prev2):
     """Map tokens into a feature representation, implemented as a
         {hashable: int} dict. If the features change, a new model must be
         trained.
         """
 
     def add(name, *args):
         features[' '.join((name,) + tuple(args))] += 1
     i += len(self.START)
     features = defaultdict(int)
     add('bias')
     add('i suffix', word[-3:])
     add('i pref1', word[0] if word else '')
     add('i-1 tag', prev)
     add('i-2 tag', prev2)
     add('i tag+i-2 tag', prev, prev2)
     add('i word', context[i])
     add('i-1 tag+i word', prev, context[i])
     add('i-1 word', context[i - 1])
     add('i-1 suffix', context[i - 1][-3:])
     add('i-2 word', context[i - 2])
     add('i+1 word', context[i + 1])
     add('i+1 suffix', context[i + 1][-3:])
     add('i+2 word', context[i + 2])
     return features

 def __init__(self,path):
  with zipfile.ZipFile(path) as z:
   for kind in ['weights','classes','tagdict']:
    setattr(self,kind,json.loads(z.read('averaged_perceptron_tagger_eng/averaged_perceptron_tagger_eng.'+kind+'.json')))
 def tag(self,words):
  prev,prev2=self.START;context=self.START+[self.normalize(w) for w in words]+self.END;out=[]
  for i,word in enumerate(words):
   tag=self.tagdict.get(word)
   if not tag:
    scores=defaultdict(float)
    for f,v in self._get_features(i,word,context,prev,prev2).items():
     for label,weight in self.weights.get(f,{}).items():scores[label]+=v*weight
    tag=max(self.classes,key=lambda label:(scores[label],label))
   out.append([word,tag]);prev2,prev=prev,tag
  return out

"""Text-aware Liminal D124–127 selection, adapted from PJ Gray's MIT source.
NLTK POS is not NER: protection is local, independent of cut availability.
"""
import json
import math
from pathlib import Path
import re
from dialogue_tagger import Tagger
from sampler import SR
DATA=json.loads(Path(__file__).with_name('dialogue_lexicon.json').read_text())
FUNCTION=set(DATA['functionWords']);MARKERS=set(DATA['discourseMarkers'])
NEGATIONS={'not','no','never','neither','nor','nothing','nobody','cannot'}
INFLECTIONS=('s','es',"'s",'ed','d','ing','er','ers','y')
def normalize(w):return ''.join(c for c in w.replace('’',"'").lower() if c.isalnum() or c=="'")
def lexical(w):
    if w in DATA['falseFriends']:return 0
    best=0
    for cat in DATA['categories']:
        for e in cat['entries']:
            hit=w.startswith(e[:-1]) if e.endswith('*') else w==e
            if not cat['exact'] and not hit:
                hit=any(w==e+s for s in INFLECTIONS) or (e.endswith('e') and any(w==e[:-1]+s for s in ('ing','ed','er','ers')))
            if hit:best=max(best,cat['weight'])
    return best

def weights(words,tags):
    result=[]
    for i,(word,tag) in enumerate(zip(words,tags)):
        raw=word['text'];w=normalize(raw);value=lexical(w)
        if not w or (not value and w in FUNCTION):result.append(0);continue
        value=max(.25,value)
        initial=i==0 or words[i-1]['text'][-1:] in '.?!'
        name=tag in ('NNP','NNPS') or (raw[0].isupper() and not initial and w!='i') or (initial and raw.endswith(',') and w not in MARKERS)
        if name:value=max(value,.8)
        if tag=='CD' or w.isnumeric():value=max(value,.5)
        if len(w)>=8 and tag.startswith(('NN','VB','JJ')):value=max(value,.4)
        result.append(value)
    return result

def interest(words,values,tags):
    if not words:return 0
    ordered=sorted(values,reverse=True);peak=ordered[0];second=ordered[1] if len(ordered)>1 else 0
    score=.5*peak+.2*second+.3*min(1,sum(v>0 for v in values)/len(words)/.6)
    first=normalize(words[0]['text']);last=normalize(words[-1]['text'])
    if words[-1]['text'][-1:] in ('!','?'):score+=.08
    if words[0]['text'].endswith(',') and values[0]>=.75:score+=.1
    if len(words)>1 and first not in FUNCTION and tags[0].startswith('VB'):score+=.06
    if 2<=len(words)<=7:score+=.05
    if first in DATA['openStarts']:score*=.8
    if last in FUNCTION and last not in DATA['closingFunctionWords']:score*=.75
    if len(words)>10:score*=.9
    return min(1,max(0,score))

def protected(words,tags):
    """Protect local names and grammatical atoms, never a capitalized sentence.
    POS alone is noisy on archive speech. A name needs noninitial capitalization
    or adjacent capitalized proper nouns; sentence starts are ordinary words.
    """
    spans=[];n=len(words)
    for i,(word,tag) in enumerate(zip(words,tags)):
        raw=word['text'];w=normalize(raw)
        capital=raw[:1].isupper() and w not in FUNCTION|MARKERS and w!='i'
        adjacent=i+1<n and words[i+1]['text'][:1].isupper() and tags[i+1] in ('NNP','NNPS')
        if capital and tag in ('NNP','NNPS') and (i>0 or adjacent):
            end=i+1
            while end<n and words[end]['text'][:1].isupper() and tags[end] in ('NNP','NNPS') and words[end-1]['text'][-1:] not in ',.;:!?':end+=1
            spans.append((i,end))
        if w in NEGATIONS or "n't" in w:
            end=min(n,i+4)
            for j in range(i+1,end):
                if words[j-1]['text'][-1:] in ',.;:!?':end=j;break
                if tags[j].startswith(('VB','JJ','NN')):end=j+1;break
            spans.append((max(0,i-1) if i and tags[i-1].startswith(('VB','MD')) else i,end))
        elif tag in ('DT','PRP','CD'):
            wanted=('VB',) if tag=='PRP' else ('NN',)
            for j in range(i+1,min(n,i+5)):
                if words[j-1]['text'][-1:] in ',.;:!?':break
                if tags[j].startswith(wanted):spans.append((i,j+1));break
    merged=[]
    for a,b in sorted(spans):
        if merged and a<merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else:merged.append((a,b))
    return merged

def refine(pcm,start,end):
    """Snap edges within20ms to a quiet2ms window; reject inactive units."""
    frames=len(pcm)//2;start=max(0,min(frames-1,round(start*SR)));end=max(start+1,min(frames,round(end*SR)))
    def energy(at):
        lo=max(0,at-44);hi=min(frames,at+44)
        return sum(pcm[k*2]**2+pcm[k*2+1]**2 for k in range(lo,hi,8))/max(1,len(range(lo,hi,8)))
    radius=round(.020*SR)
    a=min(range(max(0,start-radius),min(end,start+radius)+1,44),key=lambda k:(energy(k),abs(k-start)))
    b=min(range(max(a+1,end-radius),min(frames,end+radius)+1,44),key=lambda k:(energy(k),abs(k-end)))
    active=[energy(k) for k in range(a,b,max(44,(b-a)//64))]
    if not active or max(active)<1e-7 or b-a<round(.04*SR):return None
    return a,b-a

class Selector:
    def __init__(self,model):self.tagger=Tagger(model)
    def select(self,pcm,transcript,revision):
        candidates=[]
        # Recognition segments may split a sentence; join contiguous runs until
        # terminal punctuation, so the intro is a line rather than an arbitrary token.
        joined=[];pending=[]
        for line in transcript['lines']:
            if pending and line['start']-pending[-1]['end']>.35:joined.append(pending);pending=[]
            for word in line['words']:
                pending.append(word)
                if word['text'][-1:] in '.?!':joined.append(pending);pending=[]
        if pending:joined.append(pending)
        for words in joined:
            tags=[t for _,t in self.tagger.tag([w['text'].strip('.,;:!?\"()') for w in words])]
            values=weights(words,tags);span=refine(pcm,words[0]['start'],words[-1]['end'])
            if span and .2<=span[1]/SR<=10:candidates.append((interest(words,values,tags),words,tags,values,span))
        if not candidates:raise ValueError('No audible text line; keeping current bank')
        candidates.sort(key=lambda c:(-c[0],c[1][0]['start']))
        # Prefer usable vocabulary over a high-interest indivisible statement.
        # Local guards and lexical atoms determine availability independently of
        # whether Auto may reorder them. True one-word sources stay explicit.
        usable=[]
        for candidate in candidates:
            _,ws,ts,vs,span=candidate;gs=protected(ws,ts)
            atoms=[(a,b) for a,b in gs if b-a>1]
            atoms += [(i,i+1) for i,v in enumerate(vs) if v>0 and not any(a<=i<b for a,b in gs if b-a>1)]
            shorter={cut for a,b in atoms if (cut:=refine(pcm,ws[a]['start'],ws[b-1]['end'])) and cut[1]<span[1]*.85}
            if len(shorter)>=2:usable.append(candidate)
        choices=usable or candidates
        chosen_line=choices[(revision//4)%min(3,len(choices))]
        _,words,tags,values,whole=chosen_line;guards=protected(words,tags)
        protected_units={0}
        units=[whole];texts=[' '.join(w['text'] for w in words)];scores=[0]
        for a,b in guards:
            cut=refine(pcm,words[a]['start'],words[b-1]['end'])
            if cut and cut not in units:
                protected_units.add(len(units));units.append(cut);texts.append(' '.join(w['text'] for w in words[a:b]));scores.append(max(values[a:b]))
        for i,word in enumerate(words):
            if values[i]<=0 or any(a<=i<b and b-a>1 for a,b in guards):continue
            cut=refine(pcm,word['start'],word['end'])
            if cut and cut not in units:
                units.append(cut);texts.append(word['text']);scores.append(values[i]-(0 if .18<=cut[1]/SR<=.75 else .1))
        # Add meaningful contiguous mixed cuts without splitting protected phrases.
        for i in range(len(words)-1):
            a,b=i,i+2
            if any(x<a<y or x<b<y for x,y in guards):continue
            if max(values[a:b])<.5:continue
            cut=refine(pcm,words[a]['start'],words[b-1]['end'])
            if cut and cut not in units:units.append(cut);texts.append(' '.join(w['text'] for w in words[a:b]));scores.append(max(values[a:b])*.8)
        ranked=sorted(range(1,len(units)),key=lambda i:(-scores[i],-i))[:7]
        # Eight automatic PCM slots; manual pads share this unique bank. Full line
        # always slot0; signature and response are actual highest-interest words.
        chosen=[0]+sorted(ranked,key=lambda i:units[i][0])
        role=sorted(range(1,len(chosen)),key=lambda j:(-scores[chosen[j]],-j))
        signature=role[0] if role else 0
        response=role[1] if len(role)>1 and scores[chosen[role[1]]]>.25 else 0
        cuts=[units[i] for i in chosen];labels=[texts[i] for i in chosen]
        return dict(cuts=cuts,labels=labels,line=texts[0],interest=chosen_line[0],protected=guards,protected_cuts=[j for j,i in enumerate(chosen) if i in protected_units],reorder=not guards,quality='TEXT' if len(cuts)>=3 else 'LIMITED TEXT',signature=signature,response=response)

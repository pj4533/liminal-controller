"""D123 acoustic fallback: durable per-film played-line ledger, never reset by Stop."""
import json
import os
from pathlib import Path
class DialogueLedger:
    def __init__(self,path,content):
        self.path=Path(path);self.content=content;self.data=json.loads(self.path.read_text()) if self.path.exists() else {};self.committed=set()
    def choose(self,exclude=None):
        history=self.data.get(self.content,{})
        choices=[i for i in range(6) if i!=exclude]
        return min(choices,key=lambda i:(history.get(str(i),{}).get('count',0),history.get(str(i),{}).get('order',-1),i))
    def commit(self,line,revision):
        if revision in self.committed:return None
        self.committed.add(revision);history=self.data.setdefault(self.content,{});record=history.setdefault(str(line),{'count':0})
        record['count']+=1;record['order']=sum(x['count'] for x in history.values())
        return json.dumps(self.data,sort_keys=True)
    def save(self,text):
        self.path.parent.mkdir(parents=True,exist_ok=True);tmp=self.path.with_suffix('.tmp');tmp.write_text(text)
        with tmp.open('rb') as f:os.fsync(f.fileno())
        os.replace(tmp,self.path)

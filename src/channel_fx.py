"""Channel FX contract: ABI16 IDs, physical units, pages and native bounds.

Generate the checked-in native table with scripts/generate-fx.py after edits.
Legacy tone is an additional fixed baseline filter, preserving the dry voicing.
"""
from dataclasses import dataclass,replace
import math

@dataclass(frozen=True)
class Parameter:
    id:int
    label:str
    low:float
    high:float
    default:float
    step:float
    unit:str=''
    choices:tuple=()
    logarithmic:bool=False
    def clamp(self,value):
        if not math.isfinite(value):raise ValueError('finite FX value required')
        value=max(self.low,min(self.high,value))
        return math.floor(value+.5) if self.choices else value
    def edit(self,value,delta):
        if self.logarithmic:
            if value==0:return self.low or 20 if delta>0 else 0
            value=value*2**(delta/24)
            if self.low==0 and value<20:value=0
        else:value+=delta*self.step
        return self.clamp(value)
    def display(self,value):
        if self.choices:return self.choices[int(value)]
        if self.unit=='Hz':return 'OFF' if value==0 else ('%.1fK HZ'%(value/1000) if value>=1000 else '%d HZ'%round(value))
        if self.unit=='%':return '%d%%'%round(value*100)
        if self.unit=='dB':return '%+.1f DB'%value
        if self.unit=='s':return '%.2f S'%value
        if self.unit=='ms':return '%.1f MS'%value
        if self.unit=='rate':return '%.2f HZ'%value
        return '%.2f'%value

# label, topology (0 transient / 1 low shelf / 2 high shelf), corner Hz
CHARACTERS=(('TRANSIENT',0,3000),('BODY',1,180),('PRESENCE',2,3000),
            ('WARMTH',1,500),('BITE',2,2400),('CLARITY',2,1800))
DIVISIONS=('1/16','1/8','1/8 D','1/4','1/4 D','1/2')
PARAMETERS=(
 Parameter(0,'LEVEL',0,1,.65,.01,'%'),
 Parameter(1,'LOW CUT',0,1200,0,1,'Hz',logarithmic=True),
 Parameter(2,'HIGH CUT',800,18000,18000,1,'Hz',logarithmic=True),
 Parameter(3,'DRIVE',0,18,0,.25,'dB'),
 Parameter(4,'PRESENCE',-6,6,0,.25,'dB'),
 Parameter(5,'COMPRESS',0,1,0,.01,'%'),
 Parameter(6,'WIDTH',0,1.5,1,.01,'%'),
 Parameter(7,'PAN',-1,1,0,.02,'%'),
 Parameter(8,'ECHO MIX',0,.4,.12,.01,'%'),
 Parameter(9,'DIVISION',0,5,2,1,choices=DIVISIONS),
 Parameter(10,'FEEDBACK',0,.65,.35,.01,'%'),
 Parameter(11,'ECHO TONE',800,12000,6000,1,'Hz',logarithmic=True),
 Parameter(12,'REVERB',0,.35,.10,.01,'%'),
 Parameter(13,'DECAY',.2,4,1.2,.05,'s'),
 Parameter(14,'DAMPING',1500,12000,6000,1,'Hz',logarithmic=True),
 Parameter(15,'PREDELAY',0,60,0,1,'ms'),
 Parameter(16,'CHORUS',0,.35,0,.01,'%'),
 Parameter(17,'RATE',.05,2,.3,.05,'rate'),
 Parameter(18,'DEPTH',0,6,3,.1,'ms'),
 Parameter(19,'WOW',0,1,0,.01,'%'),
 Parameter(20,'FLUTTER',0,1,0,.01,'%'),
 Parameter(21,'TREMOLO',0,.8,0,.01,'%'),
 Parameter(22,'TREM DIV',0,5,3,1,choices=DIVISIONS),
 Parameter(23,'CRUSH',0,1,0,.01,'%'),
)
PAGES=('EFFECTS','SOUND','SPACE','MOTION')
def pages(channel):return PAGES+('CUTS',) if channel in (4,5) else PAGES

def parameters(channel):
    params=list(PARAMETERS)
    params[4]=replace(params[4],label=CHARACTERS[channel][0])
    if channel==0:
        params[4]=replace(params[4],low=-.5,high=.5,step=.02,unit='%')
        params[5]=replace(params[5],label='GLUE')
        for i in (8,12):params[i]=replace(params[i],default=0)
    if channel==1:
        params[1]=replace(params[1],high=160)
        params[6]=replace(params[6],high=1)
    return tuple(params)

def defaults(channel):return [p.default for p in parameters(channel)]

def page_parameters(channel,page):
    params=parameters(channel)
    if page==0:
        ids=(0,1,2,8,9,10,12,13)
        return tuple(replace(params[i],label={8:'ECHO',9:'ECHO TIME'}.get(i,params[i].label)) for i in ids)
    return params[(page-1)*8:page*8] if page<4 else ()

#define _GNU_SOURCE
#include <stdatomic.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>
#include <dlfcn.h>
#include <errno.h>
#include <time.h>
#include <sched.h>
#define SR 44100
#define NS 256
#define NB 4
#define NE 512
#define NV 64
#define NQ 1024
#define NC 6
#include "fx_dsp.h"
/* Standalone sampler ABI2. All file IO and allocation happen before publication. */
typedef struct { const float *pcm; int frames; } Sample;
typedef struct { int frame,channel,sample,gate; float speed,gain,attack,release,frequency; int pad; } Event;
typedef struct { int length,count,revision; Event events[NE]; } Bank;
typedef struct { int op,a,b,id; Event event; } Command;
typedef struct { int live,bank,id,age,releasing,left; Event e; double pos; float env,body[2]; } Voice;
typedef struct {
 Sample samples[NS]; Bank banks[NB]; _Atomic int state[NB];
 Command queue[NQ]; _Atomic unsigned read,write; Voice voices[NV];
 int stopped_next; int hush,current,next,position,event,playing,manual[NC],muted[NC];
 float level[NC],smooth[NC],tone[NC],master,master_smooth;
 Fx fx[NC];
 int flash_pad[NC],flash_revision[NC],flash_left[NC];
 _Atomic unsigned long long feedback[NC];
 _Atomic int shown_bank,shown_position,shown_playing,overflow,shown_voices;
 _Atomic unsigned long frames,written,xruns; _Atomic float peak;
 _Atomic int running; int started; pthread_t thread; void *alsa,*pcm;
 int (*pcm_open)(void **,const char *,int,int);
 int (*pcm_params)(void *,int,int,unsigned,unsigned,int,unsigned);
 long (*pcm_write)(void *,const void *,unsigned long);
 int (*pcm_prepare)(void *); int (*pcm_nonblock)(void *,int);int (*pcm_close)(void *);
} Engine;
int lm_abi(void){return 2;}
void *lm_create(void){
 Engine *s=calloc(1,sizeof *s);if(!s)return NULL;
 s->stopped_next=s->current=s->next=-1;s->master=.45f;
 for(int i=0;i<NC;i++){s->level[i]=.65f;s->tone[i]=.55f;fx_init(&s->fx[i],i);s->fx[i].target[8]=s->fx[i].value[8]=0;s->fx[i].target[12]=s->fx[i].value[12]=0;}
 atomic_store(&s->shown_bank,-1);return s;
}
int lm_sample(Engine *s,int index,const float *pcm,int frames){
 if(index<0||index>=NS||!pcm||frames<2||s->started)return 0;
 s->samples[index]=(Sample){pcm,frames};return 1;
}
int lm_bank_sample(Engine *s,int slot,int index,const float *pcm,int frames){
 if(slot<0||slot>=NB||index<0||index>=16||!pcm||frames<2||atomic_load(&s->state[slot])!=1)return 0;
 s->samples[192+slot*16+index]=(Sample){pcm,frames};return 1;
}
int lm_reserve(Engine *s){
 for(int i=0;i<NB;i++){int free=0;if(atomic_compare_exchange_strong(&s->state[i],&free,1))return i;}return -1;
}
int lm_bank(Engine *s,int slot,const Bank *b){
 if(slot<0||slot>=NB||atomic_load(&s->state[slot])!=1||b->length<2||b->count<0||b->count>NE)return 0;
 int previous=-1;
 for(int i=0;i<b->count;i++){
  Event e=b->events[i];
  if(e.pad<0||e.pad>255||(e.pad>64&&e.pad<128)||e.frame<previous||e.frame>=b->length||e.channel<0||e.channel>=NC||e.sample<0||e.sample>=NS||!s->samples[e.sample].pcm||e.gate<1||!isfinite(e.speed)||e.speed<=0||e.speed>16||!isfinite(e.gain)||e.gain<0||e.gain>(e.channel==4?16:4)||!isfinite(e.attack)||e.attack<1||!isfinite(e.release)||e.release<1)return 0;
  previous=e.frame;
 }
 s->banks[slot]=*b;return 1;
}
int lm_command(Engine *s,const Command *c){
 if(c->op==16&&(c->a<0||c->a>=NC||c->b<0||c->b>=NP||!isfinite(c->event.gain)))return -1;
 if((c->op==4||c->op==10||(c->op>=11&&c->op<=14))&&!isfinite(c->event.gain))return -1;
 unsigned w=atomic_load(&s->write),r=atomic_load_explicit(&s->read,memory_order_acquire);
 if(w-r>=NQ){atomic_fetch_add(&s->overflow,1);return 0;}
 if(c->op==7){
  if(c->id<=0||c->a<0||c->a>=NB||c->event.frame<0||c->event.sample<0||c->event.sample>=NS)return -1;
  int expected=atomic_load(&s->state[c->a]);
  do {if((expected&3)!=2)return -1;}while(!atomic_compare_exchange_weak(&s->state[c->a],&expected,expected+4));
  if(atomic_load(&s->shown_bank)!=c->a||s->banks[c->a].revision!=c->b){atomic_fetch_sub(&s->state[c->a],4);return -1;}
 }
 s->queue[w%NQ]=*c;atomic_store_explicit(&s->write,w+1,memory_order_release);return 1;
}
static void release(Voice *v){if(v->live&&!v->releasing){v->releasing=1;v->left=(int)v->e.release;}}
static void note(Engine *s,Event e,int bank,int id){
 if(e.channel<0||e.channel>=NC||e.sample<0||e.sample>=NS||!s->samples[e.sample].pcm)return;
 for(int i=0;i<NV;i++)if(!s->voices[i].live){s->voices[i]=(Voice){.live=1,.bank=bank,.id=id,.e=e,.pos=id?fmax(0,e.frame):0};
  if(!id&&e.pad>0&&!s->muted[e.channel]){int ch=e.channel;s->flash_pad[ch]=e.pad;s->flash_revision[ch]=s->banks[bank].revision;int duration=(int)fmin(5292,fmin(e.gate,(s->samples[e.sample].frames-1)/e.speed));s->flash_left[ch]=duration;}
  return;}
 atomic_fetch_add(&s->overflow,1); /* Reject newest onset; never steal a held identity. */
}
static void commands(Engine *s){
 unsigned r=atomic_load(&s->read),w=atomic_load_explicit(&s->write,memory_order_acquire);
 for(unsigned budget=0;r!=w&&budget<NQ;budget++,r++){
  Command c=s->queue[r%NQ];int ch=c.a;
  /* Resolve toggle on the render owner, including rapid queued Play presses. */
  if(c.op==15)c.op=s->playing?2:1;
  switch(c.op){
   case 1:s->hush=0;if(s->current>=0)s->playing=1;break;
   case 2:s->hush=1323;s->playing=0;s->position=s->event=0;for(int ch=0;ch<NC;ch++)s->flash_left[ch]=0;for(int i=0;i<NV;i++){release(&s->voices[i]);if(s->voices[i].left>1323)s->voices[i].left=1323;}for(int ch=0;ch<NC;ch++)fx_clear(&s->fx[ch]);break;
   case 3:if(ch>=0&&ch<NC){s->manual[ch]=c.b;if(c.b)s->flash_left[ch]=0;}break;
   case 4:if(ch>=0&&ch<NC)s->level[ch]=s->fx[ch].target[0]=fminf(1,fmaxf(0,c.event.gain));break;
   case 5:if(ch>=0&&ch<NC){s->muted[ch]=c.b;if(c.b)s->flash_left[ch]=0;}break;
   case 6:if(ch>=0&&ch<NB&&atomic_load(&s->state[ch])==1){atomic_store(&s->state[ch],2);if(s->current<0){s->current=ch;s->event=s->position=0;}else{s->next=ch;s->stopped_next=-1;}}break;
   /* Admission validated current/revision and pinned the onset's source. A
      boundary after admission must not discard that already accepted note. */
   case 7:if(c.event.channel>=0&&c.event.channel<NC){s->hush=0;note(s,c.event,c.a,c.id);}atomic_fetch_sub(&s->state[c.a],4);break;
   case 8:for(int i=0;i<NV;i++)if(s->voices[i].id==c.id)release(&s->voices[i]);break;
   case 9:for(int i=0;i<NV;i++)if(s->voices[i].id)release(&s->voices[i]);break;
   case 10:s->master=fminf(1,fmaxf(0,c.event.gain));break;
   case 11:if(ch>=0&&ch<NC)s->tone[ch]=fminf(1,fmaxf(0,c.event.gain));break;
   case 12:if(ch>=0&&ch<NC)s->fx[ch].target[8]=bound(c.event.gain,0,.4f);break;
   case 13:if(ch>=0&&ch<NC)s->fx[ch].target[12]=bound(c.event.gain,0,.35f);break;
   case 17:if(ch>=0&&ch<NB)s->stopped_next=ch;break;
   case 16:if(ch>=0&&ch<NC&&c.b>=0&&c.b<NP){float v=bound(c.event.gain,fx_specs[ch][c.b][0],fx_specs[ch][c.b][1]);s->fx[ch].target[c.b]=(c.b==9||c.b==22)?roundf(v):v;if(c.b==0)s->level[ch]=v;}break;
   case 14:if(ch>=0&&ch<NC)s->fx[ch].target[7]=bound(c.event.gain,-1,1);break;
  }
 }
 atomic_store_explicit(&s->read,r,memory_order_release);
}
void lm_render(Engine *s,float *out,int count){
 commands(s);float peak=0;
 /* Explicit worker publication while stopped, deferred until every voice and
    admitted onset is clear. Playing publication remains the64-beat boundary.
    The transitional state blocks racing old-bank admissions during the swap. */
 if(!s->playing&&s->next>=0&&s->next==s->stopped_next){
  int busy=0;for(int i=0;i<NV;i++)if(s->voices[i].live)busy=1;
  int old=s->current,expected=2;
  if(!busy&&old>=0&&atomic_compare_exchange_strong(&s->state[old],&expected,3)){
   s->current=s->next;s->next=s->stopped_next=-1;s->position=s->event=0;
   atomic_store(&s->shown_bank,s->current);atomic_store(&s->state[old],2);
   for(int ch=0;ch<NC;ch++)s->flash_left[ch]=0;
  }
 }
 for(int n=0;n<count;n++){
  for(int ch=0;ch<NC;ch++)if(s->flash_left[ch]>0)s->flash_left[ch]--;
  if(s->playing&&s->current>=0){
   Bank *b=&s->banks[s->current];
   if(s->position>=b->length){s->position=s->event=0;if(s->next>=0){s->current=s->next;s->next=s->stopped_next=-1;b=&s->banks[s->current];}}
   while(s->event<b->count&&b->events[s->event].frame<=s->position){Event e=b->events[s->event++];if(!s->manual[e.channel])note(s,e,s->current,0);}
   s->position++;
  }
  float mix[NC][2]={{0}};
  for(int i=0;i<NV;i++){
   Voice *v=&s->voices[i];if(!v->live)continue;
   Sample p=s->samples[v->e.sample];
   if(v->e.channel==3&&v->pos>p.frames*.75)v->pos=p.frames*.35+256;
   int j=(int)v->pos;
   if(j+1>=p.frames||(v->id&&v->e.channel==4&&v->age>=v->e.gate)){v->live=0;continue;}
   int gate=v->e.gate;
   if(v->id&&v->e.channel==4)gate=gate>(int)v->e.release?gate-(int)v->e.release:0;
   if(!v->releasing&&v->age>=gate)release(v);
   if(v->releasing){v->env*=fmaxf(0,(float)(v->left-1)/fmaxf(1,v->left));if(--v->left<=0){v->live=0;continue;}}
   else v->env=fminf(1,(float)(v->age+1)/v->e.attack);
   float f=(float)(v->pos-j),gain=v->e.gain*v->env;
   for(int c=0;c<2;c++){
    float input=p.pcm[j*2+c]+f*(p.pcm[(j+1)*2+c]-p.pcm[j*2+c]);
    if(v->e.channel==3){double end=p.frames*.75;double start=p.frames*.35;if(v->pos>end-256){float blend=(float)((v->pos-(end-256))/256);int other=(int)(start+v->pos-(end-256));if(other+1<p.frames)input=input*(1-blend)+p.pcm[other*2+c]*blend;}}
    if(v->e.channel==1&&v->e.frequency>0){
     v->body[c]+=(input-v->body[c])*.0225f;
     float sub=0;const float amplitudes[4]={1,.199526f,.141254f,.089125f};
     for(int h=1;h<=4;h++){double f0=v->e.frequency*h;double ratio=f0/160;double weight=1/(1+ratio*ratio*ratio*ratio);sub+=(float)(sin(v->age*6.283185307179586*f0/SR)*amplitudes[h-1]*weight);}
     input=(input-v->body[c])*.22f+sub*.30f;
    }
    mix[v->e.channel][c]+=input*gain;
   }
   v->pos+=v->e.speed;v->age++;
  }
  float sum[2]={0};s->master_smooth+=(s->master-s->master_smooth)*.001f;
  for(int ch=0;ch<NC;ch++){
   float target=s->muted[ch]?0:s->level[ch];s->smooth[ch]+=(target-s->smooth[ch])*.001f;
   float value[2];float beat=s->current>=0?s->banks[s->current].length/64.0f:SR*60.0f/69;
   fx_process(&s->fx[ch],ch,beat,mix[ch],value,.025f+.6f*s->tone[ch]);
   for(int c=0;c<2;c++)sum[c]+=value[c]*s->smooth[ch];
  }
  if(s->hush>0&&--s->hush==0){for(int ch=0;ch<NC;ch++)fx_clear(&s->fx[ch]);for(int i=0;i<NV;i++)s->voices[i].live=0;}
  for(int c=0;c<2;c++){float x=sum[c]*s->master_smooth;float y=x/(1+fabsf(x));out[n*2+c]=y;peak=fmaxf(peak,fabsf(y));}
 }
 /* Retire banks only after all onset-owned voices have finished. */
 for(int b=0;b<NB;b++)if(atomic_load(&s->state[b])==2&&b!=s->current&&b!=s->next){int used=0;for(int i=0;i<NV;i++)if(s->voices[i].live&&s->voices[i].bank==b)used=1;if(!used){int expected=2;atomic_compare_exchange_strong(&s->state[b],&expected,0);}}
 for(int ch=0;ch<NC;ch++)atomic_store(&s->feedback[ch],s->flash_left[ch]>0?((unsigned long long)(unsigned)s->flash_revision[ch]<<32)|(unsigned)s->flash_pad[ch]:0);
 int voices=0;for(int i=0;i<NV;i++)voices+=s->voices[i].live;
 atomic_store(&s->shown_voices,voices);atomic_store(&s->shown_bank,s->current);atomic_store(&s->shown_position,s->position);atomic_store(&s->shown_playing,s->playing);atomic_store(&s->peak,peak);atomic_fetch_add(&s->frames,(unsigned long)count);
}
int lm_status(Engine *s,int field){switch(field){case 0:return atomic_load(&s->shown_bank);case 1:return atomic_load(&s->shown_position);case 2:return atomic_load(&s->shown_playing);case 3:return atomic_load(&s->overflow);case 4:return atomic_load(&s->shown_voices);case 5:return atomic_load(&s->running);default:return -1;}}
unsigned long long lm_feedback(Engine *s,int ch){return ch>=0&&ch<NC?atomic_load(&s->feedback[ch]):0;}
int lm_state(Engine *s,int slot){return slot>=0&&slot<NB?(atomic_load(&s->state[slot])&3):-1;}
unsigned long lm_frames(Engine *s){return atomic_load(&s->frames);}
unsigned long lm_written(Engine *s){return atomic_load(&s->written);}
unsigned long lm_xruns(Engine *s){return atomic_load(&s->xruns);}
float lm_peak(Engine *s){return atomic_load(&s->peak);}
/* Display-only BGR565 crossfade. Never called by the audio thread. */
void lm_blend(const uint16_t *a,const uint16_t *b,uint16_t *out,int count,int weight){
 if(count<0||count>163840||weight<0||weight>256)return;
 for(int i=0;i<count;i++){
  unsigned x=a[i],y=b[i];unsigned r=((x&31)*(256-weight)+(y&31)*weight+128)>>8;
  unsigned g=(((x>>5)&63)*(256-weight)+((y>>5)&63)*weight+128)>>8;
  unsigned blue=((x>>11)*(256-weight)+(y>>11)*weight+128)>>8;
  out[i]=(uint16_t)(r|(g<<5)|(blue<<11));
 }
}
static void *audio_loop(void *arg){
 Engine *s=arg;struct sched_param sp={.sched_priority=30};pthread_setschedparam(pthread_self(),SCHED_FIFO,&sp);
 float stereo[256*2];unsigned char packed[256*16*3];
 while(atomic_load(&s->running)){
  lm_render(s,stereo,256);memset(packed,0,sizeof packed);
  for(int n=0;n<256;n++)for(int ch=0;ch<4;ch++){int32_t v=(int32_t)(stereo[n*2+ch%2]*8388607.f);unsigned off=(n*16+ch)*3;packed[off]=v;packed[off+1]=v>>8;packed[off+2]=v>>16;}
  int done=0;while(done<256&&atomic_load(&s->running)){
   long n=s->pcm_write(s->pcm,packed+done*48,256-done);
   if(n==-EAGAIN||n==0){struct timespec pause={.tv_nsec=1000000};nanosleep(&pause,NULL);}
   else if(n==-EPIPE){atomic_fetch_add(&s->xruns,1);if(s->pcm_prepare(s->pcm)<0)atomic_store(&s->running,0);}
   else if(n<0){atomic_fetch_add(&s->xruns,1);atomic_store(&s->running,0);}else{done+=(int)n;atomic_fetch_add(&s->written,(unsigned long)n);}
  }
 }return NULL;
}
int lm_start(Engine *s,const char *device){
 if(s->started)return -1;
 s->alsa=dlopen("libasound.so.2",RTLD_NOW);if(!s->alsa)return -2;
 #define LOAD(name,target) *(void **)(&s->target)=dlsym(s->alsa,name);if(!s->target)return -3
 LOAD("snd_pcm_open",pcm_open);LOAD("snd_pcm_set_params",pcm_params);LOAD("snd_pcm_writei",pcm_write);LOAD("snd_pcm_prepare",pcm_prepare);LOAD("snd_pcm_nonblock",pcm_nonblock);LOAD("snd_pcm_close",pcm_close);
 int e=s->pcm_open(&s->pcm,device,0,1);if(e<0)return e;
 e=s->pcm_params(s->pcm,32,3,16,SR,0,17415);if(e<0){s->pcm_close(s->pcm);return e;}
 atomic_store(&s->running,1);if(pthread_create(&s->thread,NULL,audio_loop,s)){atomic_store(&s->running,0);s->pcm_close(s->pcm);return -4;}s->started=1;return 0;
}
int lm_stop(Engine *s){
 if(!s->started)return 0;
 Command stop={.op=2};if(!lm_command(s,&stop))return -2;
 struct timespec fade={.tv_nsec=100000000};nanosleep(&fade,NULL);atomic_store(&s->running,0);
 struct timespec deadline;clock_gettime(CLOCK_REALTIME,&deadline);deadline.tv_sec+=2;
 if(pthread_timedjoin_np(s->thread,NULL,&deadline))return -1;
 s->pcm_close(s->pcm);s->started=0;return 0;
}
void lm_destroy(Engine *s){if(s&&!s->started){if(s->alsa)dlclose(s->alsa);free(s);}}

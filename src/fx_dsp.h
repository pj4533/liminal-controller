/* Fixed-memory channel insert/send DSP. No allocations in the render owner. */
#include "fx_specs.h"
#define ECHO_FRAMES (SR*3)
#define MOD_FRAMES 2048
#define ROOM_FRAMES 4096
#define TAU 6.283185307179586f
typedef struct {
 float echo[ECHO_FRAMES][2],mod[MOD_FRAMES][2],predelay[ROOM_FRAMES][2];
 float comb[2][4][2048],allpass[2][2][512];
 float hp[2],lp[2],eq[2],bass[2],tone[2],damp[2][4],echo_lp[2];
 float envelope,fast,slow,held[2],phase[4];
 float hp_k,lp_k,eq_k,bass_k,echo_k,room_k,drive,eq_gain,feedback[4];
 float delay_old,delay_new,delay_fade;
 uint64_t clock;
 int ep,mp,rp,hold,echo_dirty,room_dirty,mod_dirty;
} FxMemory;
typedef struct {float target[NP],value[NP];FxMemory m;} Fx;
static const int comb_size[4]={1103,1361,1559,1867};
static const float division_beats[6]={.25f,.5f,.75f,1,1.5f,2};
static float bound(float x,float lo,float hi){return fminf(hi,fmaxf(lo,x));}
static float clean(float x){return fabsf(x)<1e-20f?0:x;}
static float pole(float hz){return 1-expf(-TAU*hz/SR);}
static float triangle(float phase){return 1-4*fabsf(phase-.5f);}
static void fx_init(Fx *f,int ch){
 for(int p=0;p<NP;p++)f->target[p]=f->value[p]=fx_specs[ch][p][2];
 f->m.delay_fade=1;
}
static void fx_clear(Fx *f){memset(&f->m,0,sizeof f->m);f->m.delay_fade=1;}
static float tap(float data[][2],int size,int pos,float delay,int c){
 float index=pos-delay;while(index<0)index+=size;
 int a=(int)index;float w=index-a;
 return data[a%size][c]*(1-w)+data[(a+1)%size][c]*w;
}
static void fx_control(Fx *f,int ch,float beat){
 FxMemory *m=&f->m;float *v=f->value;
 /* Prevent very quiet idle tails entering costly subnormal arithmetic. */
 m->fast=clean(m->fast);m->slow=clean(m->slow);m->envelope=clean(m->envelope);
 for(int c=0;c<2;c++){
  m->hp[c]=clean(m->hp[c]);m->lp[c]=clean(m->lp[c]);m->eq[c]=clean(m->eq[c]);
  m->bass[c]=clean(m->bass[c]);m->tone[c]=clean(m->tone[c]);m->echo_lp[c]=clean(m->echo_lp[c]);
  for(int i=0;i<4;i++)m->damp[c][i]=clean(m->damp[c][i]);
 }
 m->hp_k=pole(fmaxf(1,v[1]));m->lp_k=pole(v[2]);
 m->eq_k=pole(character_hz[ch]);
 m->bass_k=pole(160);m->echo_k=pole(v[11]);m->room_k=pole(v[14]);
 m->drive=powf(10,v[3]/20);m->eq_gain=powf(10,v[4]/20)-1;
 for(int i=0;i<4;i++)m->feedback[i]=powf(.001f,comb_size[i]/(SR*v[13]));
 float desired=bound(beat*division_beats[(int)f->target[9]],64,ECHO_FRAMES/1.125f-2);
 if(m->delay_new==0)m->delay_old=m->delay_new=desired;
 /* Finish a crossfade before admitting the latest requested division. */
 if(m->delay_fade>=1&&fabsf(desired-m->delay_new)>1){m->delay_old=m->delay_new;m->delay_new=desired;m->delay_fade=0;}
}
static void fx_process(Fx *f,int ch,float beat,float input[2],float out[2],float legacy_tone){
 FxMemory *m=&f->m;float *v=f->value;
 for(int p=0;p<NP;p++)if(p!=9&&p!=22)v[p]+=(f->target[p]-v[p])*.001133f; /* 20ms */
 if((m->clock&31)==0)fx_control(f,ch,beat);
 float x[2];
 for(int c=0;c<2;c++){
  m->tone[c]+=(input[c]-m->tone[c])*legacy_tone;x[c]=m->tone[c];
  m->hp[c]+=(x[c]-m->hp[c])*m->hp_k;if(v[1]>.01f)x[c]-=m->hp[c];
  m->lp[c]+=(x[c]-m->lp[c])*m->lp_k;
  /* 18k is the original voiced dry bypass. */
  x[c]+=(m->lp[c]-x[c])*bound((18000-v[2])/1000,0,1);
  if(v[3]>.0001f)x[c]=x[c]*m->drive/(1+fabsf(x[c])*(m->drive-1))/sqrtf(m->drive);
  m->eq[c]+=(x[c]-m->eq[c])*m->eq_k;
  if(character_kind[ch]!=0)x[c]+=m->eq_gain*(character_kind[ch]==1?m->eq[c]:x[c]-m->eq[c]);
 }
 float detector=fmaxf(fabsf(x[0]),fabsf(x[1]));
 m->fast+=(detector-m->fast)*(detector>m->fast?.08f:.004f);
 m->slow+=(detector-m->slow)*.0004f;
 if(character_kind[ch]==0){float transient=bound((m->fast-m->slow)*8,-1,1);for(int c=0;c<2;c++)x[c]*=1+v[4]*transient;}
 m->envelope+=(detector-m->envelope)*(detector>m->envelope?.004f:.00015f);
 if(v[5]>.0001f){float threshold=.16f-.12f*v[5],ratio=1+5*v[5];float g=m->envelope>threshold?powf(threshold/m->envelope,1-1/ratio):1;for(int c=0;c<2;c++)x[c]*=g;}
 int mod_active=v[16]+v[19]+v[20]>1e-5f;
 if(mod_active){
  m->mod_dirty=1;
  for(int c=0;c<2;c++){
   m->mod[m->mp][c]=x[c];
   float wobble=60*v[19]*triangle(m->phase[1])+4*v[20]*triangle(m->phase[2]);
   float dry=tap(m->mod,MOD_FRAMES,m->mp,128+wobble,c);
   float phase=m->phase[0]+c*.25f;if(phase>=1)phase-=1;
   float delayed=tap(m->mod,MOD_FRAMES,m->mp,441+v[18]*22.05f*(1+triangle(phase))+wobble,c);
   float tape=bound((v[19]+v[20])*100,0,1);
   x[c]=x[c]*(1-tape)+dry*tape;
   x[c]=x[c]*(1-v[16])+delayed*v[16];
  }
 }else if(m->mod_dirty){memset(m->mod,0,sizeof m->mod);m->mod_dirty=0;}
 if(v[21]>1e-5f){float g=1-v[21]*(.5f+.5f*triangle(m->phase[3]));x[0]*=g;x[1]*=g;}
 if(v[23]>1e-5f){
  if(m->hold--<=0){m->hold=(int)(v[23]*11);float steps=powf(2,15-10*v[23]);for(int c=0;c<2;c++)m->held[c]=roundf(bound(x[c],-1,1)*steps)/steps;}
  for(int c=0;c<2;c++)x[c]=x[c]*(1-v[23])+m->held[c]*v[23];
 }
 for(int c=0;c<2;c++)out[c]=x[c];
 if(v[8]>1e-5f){
  m->echo_dirty=1;
  for(int c=0;c<2;c++){
   float ratio=c?1.125f:1;
   float wet=tap(m->echo,ECHO_FRAMES,m->ep,m->delay_old*ratio,c)*(1-m->delay_fade)+tap(m->echo,ECHO_FRAMES,m->ep,m->delay_new*ratio,c)*m->delay_fade;
   m->echo_lp[c]+=(wet-m->echo_lp[c])*m->echo_k;
   m->echo[m->ep][c]=clean(bound(x[c]+m->echo_lp[c]*v[10],-8,8));
   out[c]+=m->echo_lp[c]*v[8];
  }
 }else if(m->echo_dirty){memset(m->echo,0,sizeof m->echo);memset(m->echo_lp,0,sizeof m->echo_lp);m->echo_dirty=0;}
 if(v[12]>1e-5f){
  m->room_dirty=1;
  for(int c=0;c<2;c++){
   m->predelay[m->rp][c]=x[c];float pred=tap(m->predelay,ROOM_FRAMES,m->rp,1+v[15]*44.1f,c),wet=0;
   for(int i=0;i<4;i++){
    int size=comb_size[i]+c*23,pos=m->clock%size;float y=m->comb[c][i][pos];
    m->damp[c][i]+=(y-m->damp[c][i])*m->room_k;
    m->comb[c][i][pos]=clean(bound(pred*.25f+m->damp[c][i]*m->feedback[i],-8,8));wet+=y;
   }
   for(int i=0;i<2;i++){
    int pos=m->clock%(i?337:211);float delayed=m->allpass[c][i][pos];
    float y=delayed-.5f*wet;m->allpass[c][i][pos]=clean(wet+.5f*y);wet=y;
   }
   out[c]+=wet*v[12];
  }
 }else if(m->room_dirty){memset(m->predelay,0,sizeof m->predelay);memset(m->comb,0,sizeof m->comb);memset(m->allpass,0,sizeof m->allpass);memset(m->damp,0,sizeof m->damp);m->room_dirty=0;}
 if(m->delay_fade<1)m->delay_fade=fminf(1,m->delay_fade+1.0f/1323);
 float rates[4]={v[17],.33f,6.1f,SR/fmaxf(64,beat*division_beats[(int)f->target[22]])};
 for(int i=0;i<4;i++){m->phase[i]+=rates[i]/SR;if(m->phase[i]>=1)m->phase[i]-=1;}
 m->mp=(m->mp+1)%MOD_FRAMES;m->ep=(m->ep+1)%ECHO_FRAMES;m->rp=(m->rp+1)%ROOM_FRAMES;
 /* A64-bit sample counter avoids periodic comb-index discontinuities. */
 m->clock++;
 /* Final width includes stereo wet paths; Bass keeps its low side mono. */
 float mid=(out[0]+out[1])*.5f,side=(out[0]-out[1])*.5f*v[6];
 if(ch==1){m->bass[0]+=(side-m->bass[0])*m->bass_k;side-=m->bass[0];}
 out[0]=mid+side;out[1]=mid-side;
 for(int c=0;c<2;c++)out[c]*=fminf(1,1+(c?v[7]:-v[7]));
}

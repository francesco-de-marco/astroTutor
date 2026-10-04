"""Reproduce relation charts from frozen logs and final AI judgments. No API calls."""
import json, hashlib, os, statistics, collections, textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'grafici_relazione'
OUT.mkdir(exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR',str(OUT/'.mplcache'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
ORDER=['Qwen/Qwen2.5-1.5B-Instruct','Qwen/Qwen2.5-3B-Instruct','HuggingFaceTB/SmolLM3-3B','google/gemma-3-1b-it','meta-llama/Llama-3.2-3B-Instruct','mistralai/Mistral-7B-Instruct-v0.3']
NAMES=['Qwen 1.5B','Qwen 3B','SmolLM3 3B','Gemma 1B','Llama 3B','Mistral 7B']
COLORS=['#4477aa','#66aacc','#aa3377','#ccbb44','#228833','#ee7733']
BASE,DPO='#567795','#159b89'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#26364a','text.color':'#26364a','axes.grid':True,'grid.alpha':.17,'svg.fonttype':'none','savefig.facecolor':'white'})
summary=read(ROOT/'evaluation/final_groq_v1/summary.json')
assert summary['status']=='completed' and summary['responses']==960
M={m['model']:m for m in summary['models']}
ROWS=read(ROOT/'evaluation/final_groq_v1/scored_responses.json')
H={}; R={}; INPUTS={}
for model in ORDER:
    run=ROOT/'runs'/(model.replace('/','__')+'_train_v1')
    H[model]=[r for r in read(run/'training_history.json') if 'loss' in r]
    R[model]=read(run/'result.json')
    assert len(H[model])==300 and [r['step'] for r in H[model]]==list(range(1,301))
    for f in [run/'training_history.json',run/'result.json',run/'run_manifest.json']:
        INPUTS[str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
for name in ['summary.json','scored_responses.json','manifest.json']:
    f=ROOT/'evaluation/final_groq_v1'/name
    INPUTS[str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
FIGS=[]
def finish(fig,slug,title,caption,kind='test'):
    fig.suptitle(title,fontsize=17,x=.07,ha='left',y=.98)
    footer=('Training: 600 coppie sintetiche, 2 epoche, seed 42. Nessuna validation.' if kind=='train' else
            'Test: 20 domande x 4 livelli per modello. Giudice IA GPT-OSS 120B; nessuna revisione umana.')
    fig.text(.07,.025,footer,fontsize=8,color='#53677a')
    fig.tight_layout(rect=(.035,.06,.99,.925))
    for fmt in ['png','svg']:
        fig.savefig(OUT/(slug+'.'+fmt),dpi=220)
    plt.close(fig)
    FIGS.append({'id':slug,'title':title,'caption':caption,'kind':kind})
def rolling(y,w=20):
    return np.array([np.mean(y[max(0,i-w+1):i+1]) for i in range(len(y))])
def history_panel(key,slug,title,ylabel,caption,ylim=None):
    fig,axes=plt.subplots(2,3,figsize=(12.5,7.5),sharex=True,sharey=True)
    for ax,model,name,color in zip(axes.flat,ORDER,NAMES,COLORS):
        x=[r['step'] for r in H[model]]; y=np.array([r[key] for r in H[model]])
        ax.plot(x,y,color=color,alpha=.23,lw=.7,label='Log per step')
        ax.plot(x,rolling(y),color=color,lw=2,label='Media mobile 20 step')
        ax.axvline(150,color='#777777',ls=':',lw=1)
        ax.set_title(name,fontsize=11); ax.set_xlabel('Step ottimizzatore'); ax.set_ylabel(ylabel)
        if ylim: ax.set_ylim(*ylim)
    axes.flat[0].legend(fontsize=8)
    finish(fig,slug,title,caption+' Linea tenue: dati grezzi; linea piena: media mobile retrospettiva di 20 step (finestra ridotta all\'inizio). Linea verticale: fine prima epoca.',kind='train')

history_panel('loss','01_training_loss','Loss DPO durante il training','Loss DPO',
 'La loss misura l\'obiettivo di preferenza sul training. Una loss più bassa non prova correttezza, qualità didattica o generalizzazione; le scale tra modelli non costituiscono una classifica di qualità.')
history_panel('rewards/accuracies','02_training_preference_accuracy','Accuratezza delle preferenze sul training','Frazione chosen > rejected',
 'Quota di esempi per cui il reward implicito della risposta preferita supera quello della rifiutata. Non è accuratezza scientifica sul test.',(-.03,1.03))
history_panel('rewards/margins','03_training_margin','Margine di preferenza durante il training','Reward chosen - rejected',
 'Il margine confronta i reward impliciti rispetto al modello di riferimento. Valori positivi indicano maggiore preferenza per chosen; non sono voti di un docente.')
history_panel('grad_norm','04_training_gradients','Norma dei gradienti registrata','Norma del gradiente',
 'Diagnostica dell\'ottimizzazione: non è una misura di qualità delle risposte. Il valore registrato può precedere il clipping e superarne la soglia.')
fig,axes=plt.subplots(2,3,figsize=(12.5,7.5),sharex=True,sharey=True)
for ax,model,name in zip(axes.flat,ORDER,NAMES):
    for key,label,color in [('rewards/chosen','Chosen',DPO),('rewards/rejected','Rejected','#c65c55')]:
        y=[r[key] for r in H[model]]
        ax.plot(range(1,301),y,color=color,alpha=.15,lw=.6)
        ax.plot(range(1,301),rolling(y),color=color,label=label,lw=2)
    ax.set_title(name); ax.set_xlabel('Step ottimizzatore'); ax.set_ylabel('Reward implicito');ax.axhline(0,color='gray',lw=.7)
axes.flat[0].legend()
finish(fig,'05_training_rewards','Reward impliciti: chosen e rejected','Dati grezzi e media mobile di 20 step. Reward relativi al riferimento, non giudizi esterni di correttezza.', 'train')
fig,ax=plt.subplots(figsize=(12.5,5.8))
for model,name,color in zip(ORDER,NAMES,COLORS):
    ax.plot([r['step'] for r in H[model]],[r['learning_rate'] for r in H[model]],label=name,color=color,alpha=.7)
ax.set_ylim(0,6e-6);ax.set_ylabel('Learning rate');ax.set_xlabel('Step ottimizzatore');ax.legend(ncol=3)
ax.text(.5,.35,'Le sei curve coincidono: learning rate costante = 0,000005',ha='center',transform=ax.transAxes)
finish(fig,'06_learning_rate','Learning rate: controllo della configurazione','Il learning rate è uguale e costante nei sei run. Non è stata effettuata una ricerca degli iperparametri separata per ciascun modello.','train')

def bars(slug,title,values,ylabel,caption,ylim=None):
    fig,ax=plt.subplots(figsize=(12.5,6.2)); x=np.arange(6)
    for s,off,color,label in [('base',-.2,BASE,'Base'),('dpo',.2,DPO,'DPO')]:
        y=values(s); b=ax.bar(x+off,y,.38,color=color,label=label)
        ax.bar_label(b,labels=[f'{v:.1f}' for v in y],padding=3,fontsize=9)
    ax.set_xticks(x,NAMES);ax.set_ylabel(ylabel);ax.legend()
    if ylim: ax.set_ylim(*ylim)
    finish(fig,slug,title,caption)
bars('07_correctness','Correttezza stimata: base e DPO',lambda s:[100*M[m][s]['correctness'].get('C',0)/80 for m in ORDER],
 'Risposte classificate C (%)','80 risposte per condizione e modello. C indica nucleo corretto e assenza di errori sostanziali secondo il giudice IA. Non sono 80 domande indipendenti.',(0,108))
fig,axes=plt.subplots(2,3,figsize=(12.5,7.5),sharey=True)
for ax,model,name in zip(axes.flat,ORDER,NAMES):
    bottoms=np.zeros(2)
    for c,label,color in [('C','Corrette','#159b89'),('P','Parziali','#e6b44c'),('I','Errate','#c65c55')]:
        counts=np.array([M[model][s]['correctness'].get(c,0) for s in ['base','dpo']]);vals=counts/80*100
        ax.bar(['Base','DPO'],vals,bottom=bottoms,color=color,label=label,width=.55)
        for i,n in enumerate(counts):
            if n>=3:ax.text(i,bottoms[i]+vals[i]/2,str(n),ha='center',va='center',fontsize=10)
        bottoms+=vals
    ax.set_title(name);ax.set_ylim(0,100);ax.set_ylabel('% risposte')
handles,labels=axes.flat[0].get_legend_handles_labels()
fig.legend(handles,labels,ncol=3,loc='upper center',bbox_to_anchor=(.55,.93),fontsize=9,frameon=False)
finish(fig,'08_correct_partial_incorrect','Distribuzione dei giudizi C / P / I','Altezza delle barre in percentuale; numeri interni = conteggi su 80. Le piccole categorie senza etichetta restano incluse.')
fig,axes=plt.subplots(1,3,figsize=(13,5.7),sharey=True)
for ax,key,label in zip(axes,['completeness','adequacy','clarity'],['Completezza','Adeguatezza al livello','Chiarezza']):
    for s,off,c in [('base',-.2,BASE),('dpo',.2,DPO)]:
        ax.bar(np.arange(6)+off,[M[m][s][key] for m in ORDER],.38,color=c,label=s.upper())
    ax.set_xticks(range(6),NAMES,rotation=65,ha='right');ax.set_ylim(0,2.15);ax.set_title(label);ax.set_ylabel('Media dei voti (0-2)')
axes[0].legend()
finish(fig,'09_quality_dimensions','Qualità delle risposte oltre la correttezza','Medie descrittive di voti ordinali da 0 a 2. Correttezza e adattamento didattico sono dimensioni diverse: un miglioramento della prima non implica quello della seconda.')
def heat(slug,title,key,scale,caption):
    fig,axes=plt.subplots(1,3,figsize=(13,6.3))
    arrays=[]
    for s in ['base','dpo']:
        arrays.append(np.array([[M[m]['by_level'][l][s][key] if key!='correctness' else M[m]['by_level'][l][s][key].get('C',0)*5 for l in 'ABCD'] for m in ORDER]))
    for ax,arr,label in zip(axes,[*arrays,arrays[1]-arrays[0]],['Base','DPO','Differenza DPO - base']):
        diff=label.startswith('Differenza')
        lim=max(abs(arr.min()),abs(arr.max()),.01)
        im=ax.imshow(arr,cmap='RdBu' if diff else 'YlGnBu',vmin=-lim if diff else 0,vmax=lim if diff else scale,aspect='auto')
        for (i,j),v in np.ndenumerate(arr):
            ax.text(j,i,f'{v:+.2f}' if diff and key!='correctness' else f'{v:.2f}' if key!='correctness' else f'{v:+.0f}' if diff else f'{v:.0f}',ha='center',va='center',fontsize=9,color='white' if (not diff and v>scale*.65) or (diff and abs(v)>lim*.65) else '#152d40')
        ax.set_xticks(range(4),list('ABCD'));ax.set_yticks(range(6),NAMES);ax.set_title(label);ax.grid(False);fig.colorbar(im,ax=ax,shrink=.65)
    finish(fig,slug,title,caption)
heat('10_adequacy_by_level','Adeguatezza per livello scolastico','adequacy',2,'A: primaria; B: medie; C: superiori; D: università. 20 risposte per cella. A destra differenza dei voti medi (scala 0-2); non è una misura di apprendimento.')
heat('11_correctness_by_level','Correttezza per livello scolastico','correctness',100,'Percentuale di risposte C su 20 per cella. A destra differenza in punti percentuali. Le quattro versioni della stessa domanda sono dipendenti.')
fig,ax=plt.subplots(figsize=(12.5,6.2));left=np.zeros(6)
for k,label,c in [('dpo','DPO preferito',DPO),('tie','Parità','#c4ced7'),('base','Base preferito',BASE)]:
    y=np.array([M[m]['preferences_from_scores'].get(k,0) for m in ORDER]);ax.barh(NAMES,y,left=left,label=label,color=c)
    for i,n in enumerate(y):ax.text(left[i]+n/2,i,str(n),ha='center',va='center')
    left+=y
ax.set_xlim(0,80);ax.set_xlabel('Confronti appaiati (80 per modello)');ax.invert_yaxis();ax.legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,1.12))
finish(fig,'12_preferences','Preferenze derivate dai voti','Regola lessicografica: correttezza, completezza, adeguatezza, chiarezza. Non è una seconda valutazione indipendente; sono mantenute le parità.')
fig,ax=plt.subplots(figsize=(12.5,6.3))
for s,off,c in [('base',-.18,BASE),('dpo',.18,DPO)]:
    data=[[len(r['answer'].split()) for r in ROWS if r['model']==m and r['setting']==s] for m in ORDER]
    bp=ax.boxplot(data,positions=np.arange(6)+off,widths=.3,patch_artist=True,manage_ticks=False,
        medianprops={'color':'#192e40'},flierprops={'marker':'.','markersize':3})
    for box in bp['boxes']:box.set_facecolor(c);box.set_alpha(.75)
    ax.plot([],[],lw=8,color=c,label=s.upper())
ax.set_xticks(range(6),NAMES);ax.set_ylabel('Parole per risposta (split su spazi)');ax.legend()
finish(fig,'13_response_length','Distribuzione della lunghezza delle risposte','Box: quartili 25-75%; linea: mediana; baffi: 1,5 IQR; punti: valori esterni. Sono incluse le risposte al limite di token. La brevità non è di per sé un miglioramento.')
bars('14_token_limits','Risposte che raggiungono il limite di token',lambda s:[M[m][s]['token_limit'] for m in ORDER],
 'Numero di risposte su 80','Flag limite_token_senza_EOS: possibile troncamento, non certezza di errore. Limite comune: 384 nuovi token. Tutti questi casi sono inclusi nella valutazione.',(0,18))
fig,ax=plt.subplots(figsize=(12.5,6.3))
for i,model in enumerate(ORDER):
    c=M[model]['correctness_uncertainty'];v=c['delta_percentage_points'];lo,hi=c['percentile95_cluster_bootstrap']
    ax.errorbar(v,i,xerr=[[v-lo],[hi-v]],fmt='o',color=COLORS[i],capsize=5,ms=8)
    ax.text(31,i,f'{v:+.2f} [{lo:.2f}; {hi:.2f}]',va='center',fontsize=9)
ax.axvline(0,color='#596979',ls='--');ax.set_yticks(range(6),NAMES);ax.invert_yaxis();ax.set_xlim(-20,58);ax.set_xlabel('Differenza di correttezza DPO - base (punti percentuali)')
finish(fig,'15_correctness_uncertainty','Differenze di correttezza e incertezza esplorativa','Intervalli bootstrap percentili al 95%, 5.000 ricampionamenti di 10 brani. Non includono errore del giudice, variabilità tra seed o dipendenze tra brani dello stesso PDF. Nessuna correzione per confronti multipli: non etichettare come prova definitiva di significatività.')
fig,axes=plt.subplots(1,2,figsize=(12.5,6.4))
for ax,vals,label in [(axes[0],[R[m]['train_metrics']['train_runtime']/60 for m in ORDER],'Tempo di training (minuti)'),(axes[1],[R[m]['peak_vram_allocated_gib'] for m in ORDER],'Picco VRAM allocata (GiB)')]:
    b=ax.barh(NAMES,vals,color=COLORS);ax.bar_label(b,fmt='%.1f',padding=3);ax.invert_yaxis();ax.set_xlabel(label);ax.set_xlim(0,max(vals)*1.17)
finish(fig,'16_training_resources','Risorse registrate durante il training','Tempi del trainer: escludono download e possono escludere preparazione/precalcolo. VRAM allocata da PyTorch, non memoria totale della GPU. Stessa RTX 4070 Laptop, ma condizioni operative non controllate: confronto descrittivo, non benchmark di velocità.','train')
fig,axes=plt.subplots(2,3,figsize=(12.5,7.7))
for ax,model,name in zip(axes.flat,ORDER,NAMES):
    by={(r['prompt_id'],r['setting']):r['judgment']['correctness'] for r in ROWS if r['model']==model};cats=['C','P','I'];a=np.zeros((3,3),int)
    for pid in sorted({k[0] for k in by}):a[cats.index(by[pid,'base']),cats.index(by[pid,'dpo'])]+=1
    ax.imshow(a,vmin=0,vmax=80,cmap='Blues');ax.grid(False)
    for (i,j),v in np.ndenumerate(a):ax.text(j,i,str(v),ha='center',va='center',color='white' if v>40 else '#152d40')
    ax.set_xticks(range(3),cats);ax.set_yticks(range(3),cats);ax.set_xlabel('DPO');ax.set_ylabel('Base');ax.set_title(name)
finish(fig,'17_correctness_transitions','Come cambiano i giudizi sulle stesse domande','Conteggi appaiati su 80 prompt per modello. Righe: base; colonne: DPO. La diagonale indica classe invariata; C/P/I indicano corretto/parziale/errato secondo il giudice.')
topics=list(dict.fromkeys(r['topic'] for r in read(ROOT/'test_common_v1.json')['prompts']))
a=np.zeros((6,len(topics)))
for i,m in enumerate(ORDER):
    for j,t in enumerate(topics):
        subset=[r for r in ROWS if r['model']==m and r['topic']==t]
        assert len(subset)==16
        a[i,j]=100*(sum(r['setting']=='dpo' and r['judgment']['correctness']=='C' for r in subset)-sum(r['setting']=='base' and r['judgment']['correctness']=='C' for r in subset))/8
fig,ax=plt.subplots(figsize=(13,7.5));lim=max(abs(a.min()),abs(a.max()));im=ax.imshow(a,cmap='RdBu',vmin=-lim,vmax=lim,aspect='auto');ax.grid(False)
ax.set_xticks(range(len(topics)),['\n'.join(textwrap.wrap(t,18)) for t in topics],rotation=50,ha='right',fontsize=8);ax.set_yticks(range(6),NAMES)
for (i,j),v in np.ndenumerate(a):ax.text(j,i,f'{v:+.1f}',ha='center',va='center',fontsize=8,color='white' if abs(v)>lim*.65 else '#152d40')
fig.colorbar(im,ax=ax,label='Differenza in punti percentuali')
finish(fig,'18_topic_differences','Variazioni di correttezza per argomento','Solo 8 risposte per condizione e argomento: due domande a quattro livelli. Un singolo caso vale 12,5 punti percentuali. Usare per descrivere eterogeneità, non per classificare la competenza su interi argomenti.')

(OUT/'figure_catalog.json').write_text(json.dumps(FIGS,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'provenance.json').write_text(json.dumps({'inputs_sha256':INPUTS,'smoothing':'trailing 20 steps; raw data retained','judge':summary['judge'],'human_validated':False,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2),encoding='utf-8')
intro=['# Grafici per la relazione AstroTutor','',
 '18 figure in PNG (220 dpi) e SVG vettoriale. Fascicolo PDF con didascalie. Nessuna nuova chiamata API.',
 '', '## Figure consigliate nel corpo della relazione',
 '01 loss; 07 correttezza; 09 dimensioni qualitative; 10 adeguatezza per livello; 13 lunghezza; 15 incertezza. Le altre figure sono adatte ad approfondimenti o appendici.',
 '', '## Conclusione prudente',
 'La correttezza stimata migliora in cinque modelli su sei, mentre l\'adeguatezza al livello non migliora uniformemente. Le risposte diventano più brevi e talvolta meno complete. I dati non sostengono una conclusione generale di inutilità del DPO, né provano efficacia nell\'apprendimento.',
 '', '## Limiti da mantenere nelle didascalie',
 'Un giudice IA, nessuna revisione umana indipendente, un seed per training. 600 coppie derivano da 75 domande; il test ha 20 domande su 10 brani. Le varianti non sono indipendenti. Non ci sono curve di validation né un confronto SFT in questa fase.', '']
for f in FIGS:intro += ['## '+f['id']+' - '+f['title'],f['caption'],'']
(OUT/'LEGGIMI.md').write_text('\n'.join(intro),encoding='utf-8')
print(f'Created {len(FIGS)} figures in PNG and SVG: {OUT}')

#!/usr/bin/env python3
"""ID-2Q1 bounded shared-latent model comparison."""
from __future__ import annotations
import argparse, hashlib, json, math, random, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
import numpy as np
import torch
from torch import nn

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
CONFIG=ROOT/"configs/rgeo_zgeo_1ms_id2q1_shared_latent_model_comparison.json"
CONFIG_SHA256="29b783aa311994a31d9dbfc741fa997b87f62ad468ffc5a84cd008e0f4040c05"
SCHEMA="rgeo-zgeo-1ms-id2q1-shared-latent-model-comparison-result-v1"
MODEL_SCHEMA="rgeo-zgeo-1ms-id2q1-shared-latent-model-v1"

class IntegrityError(RuntimeError): pass
def sha256(path:Path)->str:
    d=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): d.update(b)
    return d.hexdigest()
def canonical_sha(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def inside(path:Path,label:str)->Path:
    v=path.resolve()
    try:v.relative_to(ROOT)
    except ValueError as e:raise IntegrityError(f"{label} escapes repository") from e
    return v
def read_json(path:Path)->dict[str,Any]:
    v=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(v,dict):raise IntegrityError('object required')
    return v
def compact_digest(files:Sequence[Path])->tuple[int,str]:
    d=hashlib.sha256();total=0
    for p in files:
        raw=p.read_bytes();total+=len(raw);d.update(p.name.encode());d.update(b'\0');d.update(hashlib.sha256(raw).hexdigest().encode());d.update(b'\n')
    return total,d.hexdigest()

def load_stage(path:Path=CONFIG)->dict[str,Any]:
    path=inside(path,'config')
    if sha256(path)!=CONFIG_SHA256:raise IntegrityError('config hash mismatch')
    s=read_json(path)
    if s.get('schema_version')!='rgeo-zgeo-1ms-id2q1-shared-latent-model-comparison-v1' or s.get('identity')!=s.get('schema_version'):raise IntegrityError('identity changed')
    if s.get('execution_contract')!='server_only_zero_new_tsc_two_candidate_model_comparison':raise IntegrityError('execution contract changed')
    if any(int(s[k]) for k in ('new_tsc_calls','reset_calls','plant_advances')):raise IntegrityError('zero plant changed')
    if list(s['candidates'])!=['stable_shared_latent_ridge','stable_shared_latent_gru_residual']:raise IntegrityError('candidate set changed')
    if not all(s['forbidden_sources'].values()):raise IntegrityError('forbidden gate weakened')
    if float(s['shared_latent']['actual_current_innovation_decay_per_step'])!=0.8:raise IntegrityError('innovation decay changed')
    for name,src in s['fit_sources'].items():
        rp,ap=inside(ROOT/src['result'],name+' result'),inside(ROOT/src['independent'],name+' audit')
        if sha256(rp)!=src['result_sha256'] or sha256(ap)!=src['independent_sha256']:raise IntegrityError(name+' evidence hash')
        r,a=read_json(rp),read_json(ap)
        if not r.get('passed') or not r.get('development_fit_data_eligible') or r.get('route')!=src['required_route']:raise IntegrityError(name+' not fit eligible')
        if not a.get('audit_passed') or not a.get('development_fit_data_eligible'):raise IntegrityError(name+' audit failed')
    return s

@dataclass
class Cell:
    cell_id:str;group_id:str;cell_kind:str;states:np.ndarray;currents:np.ndarray;issued:np.ndarray;probe_issue:int|None;direction:str|None;sign:str|None
@dataclass
class Dataset:
    cells:list[Cell];nominal_issued:np.ndarray;action_basis:np.ndarray;state_scale:np.ndarray;response_scale:np.ndarray;current_scale:float

def _target(x:dict[str,Any])->np.ndarray:
    v=np.asarray(x['target_current_a_tsc'],float)
    if v.shape!=(14,) or not np.all(np.isfinite(v)):raise IntegrityError('target')
    return v
def _state(x:dict[str,Any])->tuple[np.ndarray,np.ndarray]:
    a=np.asarray([x['r_geo_m'],x['z_geo_m'],x['ip_a']],float);b=np.asarray(x['actual_current_a_tsc'],float)
    if a.shape!=(3,) or b.shape!=(14,) or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):raise IntegrityError('state')
    return a,b
def stable_basis(v:np.ndarray)->np.ndarray:
    _,_,vt=np.linalg.svd(v,full_matrices=False);rank=int(np.linalg.matrix_rank(v,tol=1e-12))
    if rank!=2:raise IntegrityError(f'action rank {rank}')
    b=vt[:2].copy()
    for i in range(2):
        if b[i,int(np.argmax(np.abs(b[i])))]<0:b[i]*=-1
    return b

def load_dataset(stage:dict[str,Any])->Dataset:
    rows=[]
    for name,src in stage['fit_sources'].items():
        folder=inside(ROOT/src['directory'],name+' compact');prefix='h' if name=='k1' else 'f'
        files=sorted(p for p in folder.glob(prefix+'*.json') if '__r' in p.stem);size,digest=compact_digest(files)
        if (len(files),size,digest)!=(src['compact_files'],src['compact_bytes'],src['compact_digest']):raise IntegrityError(name+' compact inventory')
        rows.extend(read_json(p) for p in files)
    grouped={}
    for r in rows:grouped.setdefault(r['cell_id'],[]).append(r)
    if len(grouped)!=80:raise IntegrityError('cell count')
    cells=[]
    for cid,members in sorted(grouped.items()):
        row=next((r for r in members if int(r['replay_index'])==0),None)
        if row is None or not row.get('passed'):raise IntegrityError('primary '+cid)
        states,currents=zip(*(_state(x) for x in row['states']));issued=np.asarray([_target(x) for x in row['actions']])
        c=Cell(cid,row['group_id'],row['cell_kind'],np.asarray(states),np.asarray(currents),issued,row.get('probe_issue_step'),row.get('direction_id'),row.get('sign'))
        if c.states.shape!=(35,3) or c.currents.shape!=(35,14) or c.issued.shape!=(34,14):raise IntegrityError('shape '+cid)
        for replay in members:
            if int(replay['replay_index'])==0:continue
            rs,rc=zip(*(_state(x) for x in replay['states']));ru=np.asarray([_target(x) for x in replay['actions']])
            if not(np.array_equal(c.states,rs) and np.array_equal(c.currents,rc) and np.array_equal(c.issued,ru)):raise IntegrityError('replay '+cid)
        cells.append(c)
    families=sorted({c.group_id for c in cells});expected=sorted(stage['fit_sources']['k1']['families']+stage['fit_sources']['p1']['families'])
    if families!=expected or any(sum(c.group_id==g for c in cells)!=5 for g in families):raise IntegrityError('families')
    ref=next(c for c in cells if c.group_id=='h00' and c.cell_kind=='baseline');nominal=ref.issued.copy();nominal[18:]=ref.issued[17]
    vectors=[c.issued[int(c.probe_issue)]-nominal[int(c.probe_issue)] for c in cells if c.cell_kind=='probe'];basis=stable_basis(np.asarray(vectors))
    residual=max(float(np.max(np.abs((c.issued-nominal)-((c.issued-nominal)@basis.T)@basis))) for c in cells)
    if residual>1e-9:raise IntegrityError(f'basis residual {residual}')
    n=stage['normalization'];return Dataset(cells,nominal,basis,np.asarray(n['state_scale']),np.asarray(n['response_scale']),float(n['actual_current_innovation_scale_a']))

def action_coordinates(c:Cell,d:Dataset)->np.ndarray:return(c.issued-d.nominal_issued)@d.action_basis.T
def memories(c:Cell,d:Dataset,poles:Sequence[float])->dict[str,np.ndarray]:
    u=action_coordinates(c,d);du=np.vstack([u[0],u[1:]-u[:-1]]);pole=np.asarray(poles)[:,None]
    level=np.zeros((len(poles),2));edge=level.copy();el=level.copy();ee=level.copy();out={k:[] for k in ('level','edge','even_level','even_edge')}
    for i in range(34):
        level=pole*level+u[i];edge=pole*edge+du[i];el=pole*el+np.abs(u[i]);ee=pole*ee+np.abs(du[i])
        for k,v in (('level',level),('edge',edge),('even_level',el),('even_edge',ee)):out[k].append(v.copy())
    return{k:np.asarray(v) for k,v in out.items()}
def nominal_training(cells:Sequence[Cell])->tuple[np.ndarray,np.ndarray]:
    s=np.mean([c.states for c in cells if c.cell_kind=='baseline'],axis=0);return s,s[1:]-s[:-1]
def context(c:Cell,o:int,nominal:np.ndarray,d:Dataset)->np.ndarray:
    now=(c.states[o]-nominal[o])/d.state_scale;v1=(c.states[o]-c.states[max(0,o-1)])/d.state_scale;v4=(c.states[o]-c.states[max(0,o-4)])/max(1,min(4,o))/d.state_scale
    active=d.nominal_issued[0] if o==0 else c.issued[o-1];innovation=((c.currents[o]-active)@d.action_basis.T)/d.current_scale
    return np.clip(np.concatenate([now,v1,v4,innovation]),-20,20)
def step_features(c:Cell,o:int,d:Dataset,nominal:np.ndarray,stage:dict[str,Any])->np.ndarray:
    mem=memories(c,d,stage['shared_latent']['fixed_poles']);u=action_coordinates(c,d);du=np.vstack([u[0],u[1:]-u[:-1]]);ctx=context(c,o,nominal,d);rows=[]
    for i in range(o,o+8):
        step_ctx=ctx.copy();step_ctx[-2:]*=float(stage['shared_latent']['actual_current_innovation_decay_per_step'])**(i-o)
        m=np.concatenate([mem[k][i].reshape(-1) for k in ('level','edge','even_level','even_edge')]);rows.append(np.concatenate([step_ctx,m,u[i],du[i],np.outer(step_ctx,u[i]).reshape(-1),[i/34,(i-o+1)/8]]))
    x=np.asarray(rows)
    if x.shape!=(8,71):raise IntegrityError(f'feature {x.shape}')
    return x
def sequence_input(c:Cell,d:Dataset,nominal:np.ndarray)->np.ndarray:
    u=action_coordinates(c,d);du=np.vstack([u[0],u[1:]-u[:-1]]);rows=[]
    for i in range(34):
        active=d.nominal_issued[0] if i==0 else c.issued[i-1];innovation=((c.currents[i]-active)@d.action_basis.T)/d.current_scale
        rows.append(np.concatenate([(c.states[i]-nominal[i])/d.state_scale,(c.states[i]-c.states[max(0,i-1)])/d.state_scale,innovation,u[i],du[i]]))
    return np.asarray(rows)
def arrays(cells:Sequence[Cell],d:Dataset,stage:dict[str,Any]):
    ns,nd=nominal_training(cells);x=[];y=[];meta=[]
    for ci,c in enumerate(cells):
        for o in range(16,27):
            f=step_features(c,o,d,ns,stage);t=(c.states[o+1:o+9]-c.states[o:o+8]-nd[o:o+8])/d.response_scale
            for s in range(8):x.append(f[s]);y.append(t[s]);meta.append((ci,o,s))
    return ns,nd,np.asarray(x),np.asarray(y),meta

@dataclass
class RidgeModel:
    scale:np.ndarray;coef:np.ndarray;nominal_state:np.ndarray;nominal_delta:np.ndarray;condition:float
    def increments(self,c:Cell,o:int,d:Dataset,s:dict[str,Any])->np.ndarray:return self.nominal_delta[o:o+8]+((step_features(c,o,d,self.nominal_state,s)/self.scale)@self.coef)*d.response_scale
def fit_ridge(cells:Sequence[Cell],d:Dataset,s:dict[str,Any])->RidgeModel:
    ns,nd,x,y,meta=arrays(cells,d,s);rows=[x];outs=[y];index={m:i for i,m in enumerate(meta)};cell_index={id(c):i for i,c in enumerate(cells)};baselines={g:next(c for c in cells if c.group_id==g and c.cell_kind=='baseline') for g in{c.group_id for c in cells}};w=math.sqrt(float(s['shared_latent']['paired_loss_weight']))
    for ci,c in enumerate(cells):
        if c.cell_kind=='baseline':continue
        bi=cell_index[id(baselines[c.group_id])];ids=[index[(ci,o,k)] for o in range(16,27) for k in range(8)];bids=[index[(bi,o,k)] for o in range(16,27) for k in range(8)]
        rows.append(w*(x[ids]-x[bids]));outs.append(w*(y[ids]-y[bids]))
    xx=np.concatenate(rows);yy=np.concatenate(outs);scale=np.sqrt(np.mean(xx*xx,axis=0));scale=np.where(scale>1e-10,scale,1.0);xn=xx/scale
    sv=np.linalg.svd(xn,compute_uv=False);rank=np.linalg.matrix_rank(xn);condition=float(sv[0]/sv[rank-1]);ridge=float(s['shared_latent']['ridge']);coef=np.linalg.solve(xn.T@xn+ridge*np.eye(xn.shape[1]),xn.T@yy)
    return RidgeModel(scale,coef,ns,nd,condition)

class GRUResidual(nn.Module):
    def __init__(self,iw:int,fw:int,h:int,cap:np.ndarray):
        super().__init__();self.gru=nn.GRU(iw,h,batch_first=True);self.head=nn.Sequential(nn.Linear(h+fw,h),nn.Tanh(),nn.Linear(h,3));self.register_buffer('cap',torch.tensor(cap,dtype=torch.float32))
    def forward(self,seq,feat,ci,origin):return torch.tanh(self.head(torch.cat([self.gru(seq)[0][ci,origin],feat],1)))*self.cap
@dataclass
class GRUModel:
    base:RidgeModel;modules:list[GRUResidual];seq_mean:np.ndarray;seq_scale:np.ndarray;feature_scale:np.ndarray
    def increments(self,c:Cell,o:int,d:Dataset,s:dict[str,Any])->np.ndarray:
        base=self.base.increments(c,o,d,s);seq=(sequence_input(c,d,self.base.nominal_state)-self.seq_mean)/self.seq_scale;feat=step_features(c,o,d,self.base.nominal_state,s)/self.feature_scale
        st=torch.tensor(seq[None],dtype=torch.float32);ft=torch.tensor(feat,dtype=torch.float32);ci=torch.zeros(8,dtype=torch.long);origin=torch.full((8,),o,dtype=torch.long)
        with torch.no_grad():r=np.mean([m(st,ft,ci,origin).numpy() for m in self.modules],axis=0)
        return base+r*d.response_scale
def seed_all(v:int):random.seed(v);np.random.seed(v);torch.manual_seed(v);torch.use_deterministic_algorithms(True);torch.set_num_threads(1)
def fit_gru(cells:Sequence[Cell],d:Dataset,s:dict[str,Any])->GRUModel:
    base=fit_ridge(cells,d,s);ns,_,x,y,meta=arrays(cells,d,s);fs=np.sqrt(np.mean(x*x,axis=0));fs=np.where(fs>1e-10,fs,1.0);seq=np.asarray([sequence_input(c,d,ns) for c in cells]);sm=seq.mean((0,1));ss=seq.std((0,1));ss=np.where(ss>1e-8,ss,1.0)
    base_pred=np.asarray([((step_features(cells[ci],o,d,ns,s)/base.scale)@base.coef)[k] for ci,o,k in meta]);residual=y-base_pred;cfg=s['candidates']['stable_shared_latent_gru_residual']
    st=torch.tensor((seq-sm)/ss,dtype=torch.float32);ft=torch.tensor(x/fs,dtype=torch.float32);yt=torch.tensor(residual,dtype=torch.float32);ci=torch.tensor([m[0] for m in meta]);origin=torch.tensor([m[1] for m in meta]);modules=[]
    index={m:i for i,m in enumerate(meta)};cell_index={id(c):i for i,c in enumerate(cells)};baselines={g:next(c for c in cells if c.group_id==g and c.cell_kind=='baseline') for g in{c.group_id for c in cells}};pair_probe=[];pair_base=[]
    for probe_index,c in enumerate(cells):
        if c.cell_kind=='baseline':continue
        base_index=cell_index[id(baselines[c.group_id])]
        for o in range(16,27):
            for k in range(8):pair_probe.append(index[(probe_index,o,k)]);pair_base.append(index[(base_index,o,k)])
    pair_probe_t=torch.tensor(pair_probe,dtype=torch.long);pair_base_t=torch.tensor(pair_base,dtype=torch.long);paired_weight=float(s['shared_latent']['paired_loss_weight'])
    for seed in cfg['seeds']:
        seed_all(int(seed));m=GRUResidual(seq.shape[2],x.shape[1],int(cfg['hidden_width']),np.asarray(cfg['maximum_residual_increment_scaled']));opt=torch.optim.Adam(m.parameters(),lr=float(cfg['learning_rate']),weight_decay=float(cfg['weight_decay']))
        for _ in range(int(cfg['epochs'])):
            opt.zero_grad(set_to_none=True);pred=m(st,ft,ci,origin);point_loss=torch.mean((pred-yt)**2);paired_target=yt[pair_probe_t]-yt[pair_base_t];paired_pred=pred[pair_probe_t]-pred[pair_base_t];loss=point_loss+paired_weight*torch.mean((paired_pred-paired_target)**2);loss.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),float(cfg['gradient_clip']));opt.step()
        modules.append(m.eval())
    return GRUModel(base,modules,sm,ss,fs)

def predict(model,c,o,d,s):return c.states[o]+np.cumsum(model.increments(c,o,d,s),axis=0)
def cosine(a,b):
    z=float(np.linalg.norm(a)*np.linalg.norm(b));return float(a@b/z) if z>0 else -1.0
def evaluate(model,held,d,s):
    errors=[[]for _ in range(8)];pred={}
    for c in held:
        for o in range(16,27):
            p=predict(model,c,o,d,s);t=c.states[o+1:o+9]
            for h in range(8):errors[h].append(p[h]-t[h])
        if c.cell_kind=='probe':pred[c.cell_id]=predict(model,c,int(c.probe_issue),d,s)
    p95=[np.quantile(np.abs(np.asarray(v)),.95,axis=0).tolist() for v in errors];mx=[np.max(np.abs(np.asarray(v)),axis=0).tolist() for v in errors];ta=[];pa=[];cs=[];ranking=[]
    for g in sorted({c.group_id for c in held}):
        b=next(c for c in held if c.group_id==g and c.cell_kind=='baseline');gt=[];gp=[]
        for c in[c for c in held if c.group_id==g and c.cell_kind=='probe']:
            o=int(c.probe_issue);bp=predict(model,b,o,d,s);pp=pred[c.cell_id]-bp;tt=c.states[o+1:o+9]-b.states[o+1:o+9];ta.append(tt/d.response_scale);pa.append(pp/d.response_scale);peak=int(np.argmax(np.linalg.norm(tt[:,:2],axis=1)));cs.append(cosine(tt[peak,:2],pp[peak,:2]));gt.append(tt[peak,:2]);gp.append(pp[peak,:2])
        gt=np.asarray(gt);gp=np.asarray(gp);scale=max(float(np.max(np.linalg.norm(gt,axis=1))),1e-12);reg=[]
        for a in np.linspace(0,2*np.pi,16,endpoint=False):
            v=np.asarray([np.cos(a),np.sin(a)]);scores=gt@v;selected=int(np.argmax(gp@v));reg.append(max(0,float(np.max(scores)-scores[selected]))/scale)
        ranking.append(max(reg))
    ta=np.concatenate(ta);pa=np.concatenate(pa);n=float(np.linalg.norm(pa-ta)/np.linalg.norm(ta))
    return{'endpoint_p95_abs_by_horizon':p95,'endpoint_max_abs_by_horizon':mx,'response_nrmse':n,'positive_peak_directions':sum(v>0 for v in cs),'probe_count':len(cs),'peak_cosines':cs,'maximum_action_ranking_regret_fraction':max(ranking),'family_ranking_regret':ranking,'response_sse_improvement_over_zero_fraction':1-n*n}
def eligible(folds,s):
    g=s['eligibility'];caps=g['endpoint_p95_abs_caps_by_horizon'];fail=[]
    for row in folds:
        fid=row['fold_id'];m=row['metrics']
        for h,v in enumerate(m['endpoint_p95_abs_by_horizon']):
            if v[0]>caps['r_geo_m'][h] or v[1]>caps['z_geo_m'][h] or v[2]>caps['ip_a'][h]:fail.append(f'P95:{fid}:{h+1}')
        if any(v>c for v,c in zip(m['endpoint_max_abs_by_horizon'][0],g['maximum_h1_abs_error'])):fail.append('H1MAX:'+fid)
        if m['response_nrmse']>g['maximum_each_fold_response_nrmse']:fail.append('RESPONSE:'+fid)
        if m['positive_peak_directions']!=g['required_positive_peak_directions_per_fold']:fail.append('DIRECTION:'+fid)
        if m['maximum_action_ranking_regret_fraction']>g['maximum_each_fold_action_ranking_regret_fraction']:fail.append('RANKING:'+fid)
        if m['response_sse_improvement_over_zero_fraction']<g['minimum_response_sse_improvement_over_zero_fraction']:fail.append('BLIND:'+fid)
    if np.mean([r['metrics']['response_nrmse'] for r in folds])>g['maximum_mean_response_nrmse']:fail.append('MEAN_RESPONSE')
    return not fail,list(dict.fromkeys(fail))
def model_payload(model,kind,d):
    b=model if isinstance(model,RidgeModel) else model.base;v={'schema_version':MODEL_SCHEMA,'kind':kind,'config_sha256':CONFIG_SHA256,'action_basis':d.action_basis.tolist(),'nominal_issued':d.nominal_issued.tolist(),'state_scale':d.state_scale.tolist(),'response_scale':d.response_scale.tolist(),'nominal_state':b.nominal_state.tolist(),'nominal_delta':b.nominal_delta.tolist(),'feature_scale':b.scale.tolist(),'coefficients':b.coef.tolist()}
    if isinstance(model,GRUModel):v.update({'sequence_mean':model.seq_mean.tolist(),'sequence_scale':model.seq_scale.tolist(),'gru_feature_scale':model.feature_scale.tolist(),'gru_members':[{k:t.detach().numpy().tolist() for k,t in m.state_dict().items()}for m in model.modules]})
    return v
def compute(path:Path=CONFIG,source_revision:str='development'):
    s=load_stage(path);d=load_dataset(s);results=[]
    for kind in s['candidates']:
        folds=[]
        for f in s['whole_family_folds']:
            train=[c for c in d.cells if c.group_id not in f['held']];held=[c for c in d.cells if c.group_id in f['held']];model=fit_ridge(train,d,s) if kind.endswith('ridge') else fit_gru(train,d,s);condition=model.condition if isinstance(model,RidgeModel) else model.base.condition
            folds.append({'fold_id':f['fold_id'],'held_families':f['held'],'metrics':evaluate(model,held,d,s),'scaled_feature_condition':condition})
        ok,fail=eligible(folds,s)
        if any(r['scaled_feature_condition']>s['shared_latent']['maximum_scaled_feature_condition'] for r in folds):ok=False;fail.append('FEATURE_CONDITION')
        summary={'mean_response_nrmse':float(np.mean([r['metrics']['response_nrmse'] for r in folds])),'worst_response_nrmse':max(r['metrics']['response_nrmse'] for r in folds),'maximum_endpoint_p95':np.max(np.asarray([r['metrics']['endpoint_p95_abs_by_horizon'] for r in folds]),axis=(0,1)).tolist()}
        results.append({'kind':kind,'eligible':ok,'failures':list(dict.fromkeys(fail)),'folds':folds,'summary':summary})
    eligible_rows=[r for r in results if r['eligible']];selected=None
    if eligible_rows:
        ridge=next((r for r in eligible_rows if r['kind'].endswith('ridge')),None);gru=next((r for r in eligible_rows if r['kind'].endswith('gru_residual')),None);selected=ridge or gru
        if ridge and gru:
            imp=1-gru['summary']['worst_response_nrmse']/ridge['summary']['worst_response_nrmse'];reg=max(g/r if r>0 else 0 for g,r in zip(gru['summary']['maximum_endpoint_p95'],ridge['summary']['maximum_endpoint_p95']))-1
            if imp>=s['eligibility']['minimum_gru_worst_fold_response_improvement_fraction_for_selection'] and reg<=s['eligibility']['maximum_gru_endpoint_p95_regression_fraction_for_selection']:selected=gru
        final=fit_ridge(d.cells,d,s) if selected['kind'].endswith('ridge') else fit_gru(d.cells,d,s);payload=model_payload(final,selected['kind'],d)
    else:payload=None
    route=s['routes']['pass' if selected else 'no_eligible_candidate'];result={'schema_version':SCHEMA,'source_revision':source_revision,'stage_config_sha256':CONFIG_SHA256,'passed':selected is not None,'route':route,'candidate_count':2,'whole_history_families':16,'primary_fit_cells':80,'candidate_fold_fits':8,'final_full_fit':1 if selected else 0,'ridge_solves':8+(1 if selected else 0),'gru_members_trained':12+(3 if selected and selected['kind'].endswith('gru_residual') else 0),'new_tsc_calls':0,'reset_calls':0,'plant_advances':0,'n1_records_used_for_fit':0,'candidate_results':results,'selected_kind':None if selected is None else selected['kind'],'model_payload_sha256':None if payload is None else canonical_sha(payload),'claim_boundary':s['claim_boundary']}
    return result,payload
def write_new(path:Path,v:Any):
    path=inside(path,'output');path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise IntegrityError('output exists')
    path.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=CONFIG);p.add_argument('--source-revision',required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args(argv);r,m=compute(a.config,a.source_revision);out=inside(a.output_dir,'output')
    if out.exists():raise IntegrityError('output exists')
    out.mkdir(parents=True);write_new(out/'result.json',r)
    if m is not None:write_new(out/'model.json',m)
    print(json.dumps(r,indent=2,sort_keys=True,allow_nan=False));return 0 if r['passed'] else 2
if __name__=='__main__':raise SystemExit(main())

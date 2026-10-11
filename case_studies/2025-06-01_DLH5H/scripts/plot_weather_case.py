from pathlib import Path
from datetime import datetime, timezone
import argparse
import h5py
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import Normalize

UTC=timezone.utc
parser = argparse.ArgumentParser(description="Reproduce ERA5 six-panel June 1 case figure")
parser.add_argument("--repo-root", type=Path, required=True, help="Path to cloned parent flight-trajectory-analysis GitHub repository")
args = parser.parse_args()
case_root = Path(__file__).resolve().parents[1]
repo = args.repo_root.resolve()
weather_dir = case_root / "data" / "era5"
wind_path = weather_dir / "wind_2025-06-01.nc"
if not wind_path.is_file():
    raise FileNotFoundError(f"Missing ERA5 wind NetCDF: {wind_path}")
inst_files=list(weather_dir.rglob('data_stream-oper_stepType-instant.nc'))
acc_files=list(weather_dir.rglob('data_stream-oper_stepType-accum.nc'))
if len(inst_files)!=1 or len(acc_files)!=1:
    raise FileNotFoundError('ZIP must contain one instant.nc and one accum.nc')

def field(handle,name,hour):
    if name not in handle:
        raise KeyError(f'Missing CDS variable: {name}')
    tt=handle['valid_time'][:].astype('int64')
    expected=int(datetime(2025,6,1,hour,tzinfo=UTC).timestamp())
    ids=np.where(tt==expected)[0]
    if len(ids)!=1:
        raise ValueError(f'{name}: expected 2025-06-01 {hour:02d}:00 UTC, actual {tt}')
    return np.asarray(handle[name][int(ids[0])],dtype=float)

with h5py.File(inst_files[0]) as f:
    lat=np.asarray(f['latitude'][:]);lon=np.asarray(f['longitude'][:])
    cloud=field(f,'tcc',9)*100.0
    cape=field(f,'cape',9)
with h5py.File(acc_files[0]) as f:
    np.testing.assert_allclose(f['latitude'][:],lat)
    np.testing.assert_allclose(f['longitude'][:],lon)
    tp9=field(f,'tp',9)*1000.0
    tp10=field(f,'tp',10)*1000.0
    cp9=field(f,'cp',9)*1000.0
    cp10=field(f,'cp',10)*1000.0
with h5py.File(wind_path) as f:
    pressure=np.asarray(f['pressure_level'][:]); ix=np.argmin(np.abs(pressure-350.))
    if abs(pressure[ix]-350)>0.01: raise ValueError('350 hPa missing from wind file')
    wlat=np.asarray(f['latitude'][:]);wlon=np.asarray(f['longitude'][:])
    u=field(f,'u',9)[ix];v=field(f,'v',9)[ix]

results=repo/'data'/'lhr_fra_hdbscan_mcs10_ms5'
labels=pd.read_csv(results/'flight_clusters.csv')
medoids=pd.read_csv(results/'cluster_representatives.csv')
rows=labels.loc[(labels['date'].astype(str)=='2025-06-01') & (labels['cluster']==-1)]
if len(rows)!=1: raise ValueError('Expected exactly one June 1 noise flight')
chosen={'Outlier (Jun 1)':str(rows.iloc[0]['flight_id'])}
for row in medoids.itertuples(index=False):
    chosen[f'Cluster {int(row.cluster)}']=row.medoid_flight_id
parts=[]
for chunk in pd.read_csv(repo/'data/lhr_fra_prepared/flight_points_clean.csv.gz',usecols=['flight_id','latitude','longitude','point_time_unix'],chunksize=100000):
    sub=chunk.loc[chunk.flight_id.isin(chosen.values())]
    if not sub.empty: parts.append(sub)
if not parts: raise ValueError('No requested flight points found')
pts=pd.concat(parts,ignore_index=True).sort_values(['flight_id','point_time_unix'])
paths={key:pts.loc[pts.flight_id==fid] for key,fid in chosen.items()}
for label,g in paths.items():
    if len(g)<2: raise ValueError(f'No track for {label}')
obs=paths['Outlier (Jun 1)']
start=datetime.fromtimestamp(float(obs.point_time_unix.iloc[0]),UTC)
end=datetime.fromtimestamp(float(obs.point_time_unix.iloc[-1]),UTC)
colors={'Outlier (Jun 1)':'#e12632','Cluster 0':'#ef8a00','Cluster 1':'#913eb6','Cluster 2':'#009a81','Cluster 3':'#246bb3'}

fig,axs=plt.subplots(2,3,figsize=(20,12),constrained_layout=False)
fig.subplots_adjust(left=.045,right=.965,top=.865,bottom=.185,wspace=.20,hspace=.29)
fig.suptitle('2025-06-01  |  LHR -> FRA  |  Weather and HDBSCAN Outlier',fontsize=21,fontweight='bold',y=.975)
fig.text(.5,.927,f'Outlier ADS-B: {start:%H:%M}-{end:%H:%M} UTC  |  ERA5 0.25 deg grid  |  Wind: 350 hPa at 09:00 UTC',ha='center',fontsize=13)

panels=[
 (axs[0,0],tp9,'Total precipitation | 08:00-09:00 UTC','Blues','rain'),
 (axs[0,1],tp10,'Total precipitation | 09:00-10:00 UTC','Blues','rain'),
 (axs[0,2],cloud,'Total cloud cover | 09:00 UTC','Greys','cloud'),
 (axs[1,0],cp9,'Convective precipitation | 08:00-09:00 UTC','PuBu','rain'),
 (axs[1,1],cp10,'Convective precipitation | 09:00-10:00 UTC','PuBu','rain'),
 (axs[1,2],cape,'CAPE | 09:00 UTC','YlOrRd','cape'),
]
maxrain=max(2.0,float(np.ceil(max(np.nanmax(tp9),np.nanmax(tp10),np.nanmax(cp9),np.nanmax(cp10)))))
for ax,arr,title,cmap,kind in panels:
    if kind=='rain':
        # Values below 0.1 mm in a one-hour window are left unshaded.
        showing=np.ma.masked_less(arr,0.1)
        mesh=ax.pcolormesh(lon,lat,showing,shading='auto',cmap=cmap,vmin=0.1,vmax=maxrain,zorder=1)
        label='mm per hour (hourly accumulation)'
    elif kind=='cloud':
        mesh=ax.pcolormesh(lon,lat,arr,shading='auto',cmap=cmap,vmin=0,vmax=100,zorder=1)
        label='Total cloud cover (%)'
    else:
        mesh=ax.pcolormesh(lon,lat,arr,shading='auto',cmap=cmap,vmin=0,vmax=max(500, float(np.ceil(np.nanmax(cape)/200)*200)),zorder=1)
        label='CAPE (J/kg)'
    if kind in ('cape','cloud'):
        step=5
        q=ax.quiver(wlon[::step],wlat[::step],u[::step,::step],v[::step,::step],color='#1c354f' if kind=='cloud' else '#26415b',width=.0024,scale=340,alpha=.85,zorder=3)
        ax.quiverkey(q,.11,.1,20,'20 m/s wind',coordinates='axes',labelpos='E',fontproperties={'size':8})
    for name,g in paths.items():
        ax.plot(g.longitude,g.latitude,color=colors[name],lw=3.2 if name.startswith('Outlier') else 1.8,alpha=.97,zorder=8 if name.startswith('Outlier') else 6)
    for place,xy in {'LHR':(-.4619,51.4706),'FRA':(8.5622,50.038)}.items():
        ax.scatter(*xy,s=22,color='#151515',edgecolors='white',linewidth=.7,zorder=11)
        ax.annotate(place,xy,fontsize=9,fontweight='bold',xytext=(5,4),textcoords='offset points',bbox={'facecolor':'white','alpha':.8,'edgecolor':'none','pad':1},zorder=12)
    ax.set_xlim(-2,11);ax.set_ylim(48,55)
    ax.set_aspect(1/np.cos(np.deg2rad(51)),adjustable='box')
    ax.set_xlabel('Longitude (degrees east)',fontsize=9)
    ax.set_ylabel('Latitude (degrees north)',fontsize=9)
    ax.set_title(title,fontsize=12,fontweight='bold',pad=7)
    ax.grid(alpha=.16,linewidth=.5)
    fig.colorbar(mesh,ax=ax,fraction=.038,pad=.024,shrink=.85,label=label)

handles=[Line2D([0],[0],color=c,lw=4 if n.startswith('Outlier') else 2.3,label=n) for n,c in colors.items()]
fig.legend(handles=handles,ncol=5,loc='lower center',bbox_to_anchor=(.5,.113),frameon=False,fontsize=12)
fig.text(.5,.077,'Rain panels: values < 0.1 mm are transparent. Cloud cover and CAPE do not prove thunderstorms. Medoids flew on different dates.',ha='center',fontsize=10)
fig.text(.5,.047,'Sources: ERA5 CDS weather + GitHub OpenSky-based trajectories. Spatial coincidence alone does not establish pilot/ATC intent.',ha='center',fontsize=10,color='#7d2635')
out_dir=case_root / "figures"
out_dir.mkdir(parents=True,exist_ok=True)
out=out_dir / 'weather_outlier_2025-06-01_6panels.png' 
fig.savefig(out,dpi=175,facecolor='white')
plt.close(fig)
print('Saved:',out)
print('Selected flight IDs:')
for name,fid in chosen.items(): print(f'  {name}: {fid}')
print('Weather maxima across downloaded region:')
for name,a in [('TP 08-09',tp9),('TP 09-10',tp10),('CP 08-09',cp9),('CP 09-10',cp10),('CAPE 09',cape)]:print(f'  {name}: {np.nanmax(a):.2f}')

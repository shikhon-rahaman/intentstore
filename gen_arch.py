import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os

fig, ax = plt.subplots(figsize=(16, 10))
fig.patch.set_facecolor('#0D1117')
ax.set_facecolor('#0D1117')
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis('off')

def box(x, y, w, h, fc, ec, text, sub=''):
    ax.add_patch(FancyBboxPatch((x,y), w, h,
        boxstyle='round,pad=0.1', facecolor=fc,
        edgecolor=ec, linewidth=2, zorder=3))
    ax.text(x+w/2, y+h/2+(0.12 if sub else 0), text,
        ha='center', va='center', fontsize=8,
        fontweight='bold', color='white',
        fontfamily='monospace', zorder=4)
    if sub:
        ax.text(x+w/2, y+h/2-0.2, sub,
            ha='center', va='center', fontsize=6.5,
            color='#8B949E', fontfamily='monospace', zorder=4)

def arr(x1,y1,x2,y2,c):
    ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
        arrowprops=dict(arrowstyle='-|>',
        color=c, lw=2), zorder=5)

# Title
ax.text(8, 9.5, 'IntentStore — Semantic Storage Intelligence Engine',
    ha='center', fontsize=15, fontweight='bold',
    color='#00D4FF', fontfamily='monospace')
ax.text(8, 9.1, 'CDAC SSM Next-Gen Kernel Hackathon 2026',
    ha='center', fontsize=9, color='#8B949E',
    fontfamily='monospace')
ax.plot([0.5,15.5],[8.85,8.85], color='#00D4FF', lw=0.8, alpha=0.4)

# Layer backgrounds
ax.add_patch(FancyBboxPatch((0.2,0.5),4.2,8,
    boxstyle='round,pad=0.1', facecolor='#1A2744',
    edgecolor='#2088FF', linewidth=2, alpha=0.4, zorder=1))
ax.text(0.5,8.6,'LAYER 1 — KERNEL',fontsize=7,
    color='#2088FF', fontweight='bold', fontfamily='monospace')

ax.add_patch(FancyBboxPatch((4.8,0.5),6.2,8,
    boxstyle='round,pad=0.1', facecolor='#1B3A2A',
    edgecolor='#3FB950', linewidth=2, alpha=0.4, zorder=1))
ax.text(5.1,8.6,'LAYER 2 — INTENT ENGINE (LLM + ML)',fontsize=7,
    color='#3FB950', fontweight='bold', fontfamily='monospace')

ax.add_patch(FancyBboxPatch((11.4,0.5),4.2,8,
    boxstyle='round,pad=0.1', facecolor='#2D1B3D',
    edgecolor='#8B5CF6', linewidth=2, alpha=0.4, zorder=1))
ax.text(11.6,8.6,'LAYER 3 — OUTPUT',fontsize=7,
    color='#8B5CF6', fontweight='bold', fontfamily='monospace')

# Layer 1 boxes
box(0.4,7.2,3.8,0.7,'#1C2D50','#2088FF','inotify / eBPF Probes','syscall tracing')
box(0.4,6.2,3.8,0.7,'#1C2D50','#2088FF','File Event Collector','CREATE/MODIFY/DELETE')
box(0.4,5.2,3.8,0.7,'#1C2D50','#2088FF','FUSE VFS Overlay','zero-patch kernel')
box(0.4,4.2,3.8,0.7,'#1C2D50','#2088FF','Access Event Logger','timestamped I/O')
box(0.4,3.0,3.8,0.9,'#1C2D50','#2088FF','Watchdog Observer','Python inotify')
box(0.4,1.5,3.8,1.2,'#243050','#2088FF','SQLite Event Store','access history DB')

# Layer 1 arrows
for y in [7.2,6.2,5.2,4.2,3.0]:
    arr(2.3,y,2.3,y-0.3,'#2088FF')

# Layer 2 boxes
box(5.0,7.2,2.8,0.7,'#1A3520','#3FB950','Groq API / Ollama','LLaMA 3.1 8B')
box(8.1,7.2,2.7,0.7,'#1A3520','#3FB950','Prompt Composer','context builder')
box(5.0,6.0,5.8,0.85,'#0F2D1A','#00FF88','Semantic Access Entropy Engine','SAE(f) = (1-S)x0.4 + (1-A)x0.3 + (1-F)x0.3')
box(5.0,4.9,1.8,0.8,'#1A3520','#3FB950','Content Embedder','n-gram vectors')
box(7.0,4.9,1.8,0.8,'#1A3520','#3FB950','Access Entropy','Shannon decay')
box(9.0,4.9,1.8,0.8,'#1A3520','#3FB950','Relevance Model','future predictor')
box(5.0,3.7,5.8,0.85,'#1A3520','#3FB950','Proactive Archival Planner','KEEP | ARCHIVE_SOON | ARCHIVE_NOW | DELETE')
box(5.0,2.5,5.8,0.9,'#1A3520','#3FB950','Batch Analyzer','parallel pipeline')
box(5.0,1.2,5.8,1.0,'#243520','#3FB950','SQLite Semantic Store','scores + embeddings')

# Layer 2 arrows
arr(6.4,7.2,6.4,6.85,'#3FB950')
arr(9.45,7.2,8.0,6.85,'#3FB950')
arr(7.9,6.0,7.9,5.7,'#3FB950')
arr(7.9,4.9,7.9,4.55,'#3FB950')
arr(7.9,3.7,7.9,3.4,'#3FB950')
arr(7.9,2.5,7.9,2.2,'#3FB950')

# Layer 3 boxes
box(11.6,7.2,3.6,0.7,'#2D1B3D','#8B5CF6','Web Dashboard','live HTML frontend')
box(11.6,6.2,3.6,0.7,'#2D1B3D','#8B5CF6','FastAPI REST API','/status /files /report')
box(11.6,5.2,3.6,0.7,'#2D1B3D','#8B5CF6','Rich CLI Dashboard','terminal UI')
box(11.6,4.2,3.6,0.7,'#2D1B3D','#8B5CF6','Alert Engine','urgent notifications')
box(11.6,3.0,3.6,0.9,'#2D1B3D','#8B5CF6','GitHub Actions CI','auto-scan on push')
box(11.6,1.5,3.6,1.2,'#3D1B2D','#8B5CF6','DevOps / User','decision maker')

# Layer 3 arrows
for y in [7.2,6.2,5.2,4.2,3.0]:
    arr(13.4,y,13.4,y-0.3,'#8B5CF6')

# Cross layer arrows
arr(4.2,6.5,5.0,6.5,'#00D4FF')
arr(4.2,4.55,5.0,4.55,'#00D4FF')
arr(10.8,7.55,11.6,7.55,'#00FF88')
arr(10.8,4.05,11.6,4.05,'#00FF88')

# Legend
items = [('#2088FF','Kernel Layer'),('#3FB950','LLM Engine'),
         ('#8B5CF6','Output Layer'),('#00D4FF','Event Flow'),('#00FF88','Results Flow')]
lx = 0.5
for c,l in items:
    ax.plot([lx,lx+0.4],[0.2,0.2],color=c,lw=3)
    ax.text(lx+0.5,0.2,l,fontsize=6.5,color='#8B949E',
        va='center',fontfamily='monospace')
    lx += 3.0

os.makedirs('assets', exist_ok=True)
plt.tight_layout(pad=0)
plt.savefig('assets/intentstore_architecture.png',
    dpi=180, bbox_inches='tight', facecolor='#0D1117')
print('DONE - saved to assets/intentstore_architecture.png')
plt.close()
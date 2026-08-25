import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

fig, ax = plt.subplots(figsize=(14, 8))
fig.patch.set_facecolor('#0D1117')
ax.set_facecolor('#0D1117')
ax.set_xlim(0, 14)
ax.set_ylim(0, 8)
ax.axis('off')

ax.text(7, 7.5, 'IntentStore - Semantic Storage Intelligence Engine',
        ha='center', fontsize=13, fontweight='bold',
        color='#00D4FF', fontfamily='monospace')

ax.text(7, 7.1, 'CDAC SSM Next-Gen Kernel Hackathon 2026',
        ha='center', fontsize=9, color='#8B949E',
        fontfamily='monospace')

os.makedirs('assets', exist_ok=True)
plt.savefig('assets/intentstore_architecture.png',
            dpi=150, bbox_inches='tight',
            facecolor='#0D1117')
print('DONE - saved to assets/')
plt.close()
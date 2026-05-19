"""
generate_graphs.py
====================
Generates exactly 3 graphs for the ADM project:

  Graph A — SQLite vs MongoDB   (Q1 Q2 Q3 Q4 bar chart)
  Graph B — Spark vs MongoDB    (Q2 comparison)
  Graph C — Scalability         (Q1 Q2 Q3 Q4 line chart)

Command:
    python generate_graphs.py

Output saved in:  graphs/  folder

Install first:
    pip install matplotlib numpy
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

os.makedirs("graphs", exist_ok=True)

C_SQLITE = "#1F3864"
C_MONGO  = "#2E75B6"
C_SPARK  = "#E07B39"

X_LABELS = [
    "1k/10k\ne=0","1k/10k\ne=2","1k/10k\ne=5","1k/10k\ne=10",
    "10k/50k\ne=0","10k/50k\ne=2","10k/50k\ne=5","10k/50k\ne=10",
    "50k/100k\ne=0","50k/100k\ne=2","50k/100k\ne=5","50k/100k\ne=10",
]
X = np.arange(len(X_LABELS))
W = 0.38

# ── YOUR REAL BENCHMARK NUMBERS ───────────────────────────────────────────────
SQL_Q1=[0.0357,0.0257,0.0257,0.0257,0.1256,0.1256,0.1256,0.1256,0.3381,0.3381,0.3381,0.3381]
SQL_Q2=[0.0104,0.0088,0.0088,0.0088,0.0663,0.0663,0.0663,0.0663,0.2643,0.2643,0.2643,0.2643]
SQL_Q3=[0.4197,0.4118,0.4118,0.4118,9.1815,9.1815,9.1815,9.1815,47.9492,47.9492,47.9492,47.9492]
SQL_Q4=[0.0003,0.0116,0.0116,0.0116,0.0003,0.0116,0.0932,0.0932,0.0003,0.0116,0.0932,0.2699]
MNG_Q1=[0.0742,0.0435,0.0435,0.0435,0.2304,0.2304,0.2304,0.2304,0.5783,0.5783,0.5783,0.5783]
MNG_Q2=[0.1411,0.0700,0.0700,0.0700,0.4221,0.4221,0.4221,0.4221,1.1429,1.1429,1.1429,1.1429]
MNG_Q3=[0.0621,0.0187,0.0187,0.0187,0.0794,0.0794,0.0794,0.0794,0.1752,0.1752,0.1752,0.1752]
MNG_Q4=[0.0382,0.0391,0.0391,0.0391,0.0382,0.0391,0.1754,0.1754,0.0382,0.0391,0.1754,0.5809]
SPK_Q2=[12.5,13.0,13.5,14.0,18.0,19.0,20.0,21.0,28.0,30.0,32.0,34.0]
TRIP_LBLS=["10,000 trips","50,000 trips","100,000 trips"]

# ── GRAPH A — SQLite vs MongoDB ───────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(18, 11))
fig.patch.set_facecolor("#F8FAFF")
fig.suptitle("SQLite vs MongoDB — All 4 Queries Performance Comparison\nCity Mobility Platform  |  ADM Project  |  A.Y. 2025/2026",
    fontsize=15, fontweight="bold", color="#1F3864", y=1.02)
bar_data=[
    ("Q1 — All Trips with User and Station Names",     SQL_Q1,MNG_Q1,"#EBF2FB"),
    ("Q2 — Users: Trip Count and Average Duration",    SQL_Q2,MNG_Q2,"#EBF5EB"),
    ("Q3 — Stations: Trips Starting and Ending  ⚠",   SQL_Q3,MNG_Q3,"#FFF5E6"),
    ("Q4 — Trips Containing at Least One ERROR Event", SQL_Q4,MNG_Q4,"#F5EBF5"),
]
for ax,(title,sql,mng,bg) in zip(axes.flatten(),bar_data):
    ax.set_facecolor(bg)
    ax.bar(X-W/2,sql,W,color=C_SQLITE,alpha=0.9,zorder=3)
    ax.bar(X+W/2,mng,W,color=C_MONGO, alpha=0.9,zorder=3)
    ax.set_title(title,fontsize=11,fontweight="bold",color="#1F3864",pad=8)
    ax.set_ylabel("Time (seconds)",fontsize=10)
    ax.set_xlabel("Dataset (users/trips / events per trip)",fontsize=9)
    ax.set_xticks(X); ax.set_xticklabels(X_LABELS,fontsize=7.5)
    ax.grid(True,alpha=0.25,linestyle="--",zorder=0)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.legend(handles=[mpatches.Patch(color=C_SQLITE,alpha=0.9,label="SQLite"),
                       mpatches.Patch(color=C_MONGO, alpha=0.9,label="MongoDB")],fontsize=10,loc="upper left")
    winner="SQLite faster" if sum(sql)<sum(mng) else "MongoDB faster"
    wcolor=C_SQLITE if sum(sql)<sum(mng) else C_MONGO
    ax.text(0.99,0.97,winner,transform=ax.transAxes,fontsize=9,fontweight="bold",color=wcolor,
            ha="right",va="top",bbox=dict(boxstyle="round,pad=0.3",facecolor="white",edgecolor=wcolor,alpha=0.95))
plt.tight_layout(h_pad=3.0,w_pad=2.5)
fig.savefig("graphs/graph_A_sqlite_vs_mongodb.png",dpi=180,bbox_inches="tight",facecolor=fig.get_facecolor())
plt.close(fig)
print("Saved → graphs/graph_A_sqlite_vs_mongodb.png")

# ── GRAPH B — Spark vs MongoDB ────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(16, 11))
fig.patch.set_facecolor("#F8FAFF")
fig.suptitle("Spark vs MongoDB — Query 2 Performance Comparison\nUsers with Trip Count and Average Duration  |  ADM Project 2025/2026",
    fontsize=15, fontweight="bold", color="#1F3864", y=1.02)
groups=[
    ("1,000 Users  /  10,000 Trips",  [0,1,2,3]),
    ("10,000 Users  /  50,000 Trips", [4,5,6,7]),
    ("50,000 Users  /  100,000 Trips",[8,9,10,11]),
    ("All Configs Combined",           list(range(12))),
]
for ax,(grp_title,idxs) in zip(axes.flatten(),groups):
    ax.set_facecolor("#FFF8F0")
    mng_vals=[MNG_Q2[i] for i in idxs]
    spk_vals=[SPK_Q2[i] for i in idxs]
    ev_lbls=[X_LABELS[i] for i in idxs]
    xi=np.arange(len(idxs))
    ax.bar(xi-W/2,mng_vals,W,color=C_MONGO,alpha=0.9,zorder=3)
    ax.bar(xi+W/2,spk_vals,W,color=C_SPARK,alpha=0.9,zorder=3)
    for i,(mv,sv) in enumerate(zip(mng_vals,spk_vals)):
        ax.text(i-W/2,mv+0.2,f"{mv:.2f}s",ha="center",fontsize=7.5,color=C_MONGO,fontweight="bold")
        ax.text(i+W/2,sv+0.2,f"{sv:.1f}s", ha="center",fontsize=7.5,color=C_SPARK,fontweight="bold")
    ax.set_title(grp_title,fontsize=11,fontweight="bold",color="#1F3864",pad=8)
    ax.set_ylabel("Time (seconds)",fontsize=10)
    ax.set_xlabel("Events per trip",fontsize=9)
    ax.set_xticks(xi); ax.set_xticklabels(ev_lbls,fontsize=8.5)
    ax.grid(True,alpha=0.25,linestyle="--",zorder=0)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.legend(handles=[mpatches.Patch(color=C_MONGO,alpha=0.9,label="MongoDB"),
                       mpatches.Patch(color=C_SPARK,alpha=0.9,label="Spark")],fontsize=10,loc="upper left")
    ax.text(0.99,0.97,"MongoDB faster\n(no JVM overhead)",transform=ax.transAxes,
            fontsize=8,fontweight="bold",color=C_MONGO,ha="right",va="top",
            bbox=dict(boxstyle="round,pad=0.3",facecolor="white",edgecolor=C_MONGO,alpha=0.95))
plt.tight_layout(h_pad=3.0,w_pad=2.5)
fig.savefig("graphs/graph_B_spark_vs_mongodb.png",dpi=180,bbox_inches="tight",facecolor=fig.get_facecolor())
plt.close(fig)
print("Saved → graphs/graph_B_spark_vs_mongodb.png")

# ── GRAPH C — Scalability ─────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(16, 11))
fig.patch.set_facecolor("#F8FAFF")
fig.suptitle("Scalability Analysis — Q1 Q2 Q3 Q4  (SQLite and MongoDB)\nHow Query Time Grows as Dataset Size Increases  |  ADM Project 2025/2026",
    fontsize=15, fontweight="bold", color="#1F3864", y=1.02)
scale_data=[
    ("Q1 — All Trips with User and Station Names",
     [SQL_Q1[0],SQL_Q1[4],SQL_Q1[8]],[MNG_Q1[0],MNG_Q1[4],MNG_Q1[8]],"#EBF2FB","Linear growth — healthy"),
    ("Q2 — Users: Trip Count and Average Duration",
     [SQL_Q2[0],SQL_Q2[4],SQL_Q2[8]],[MNG_Q2[0],MNG_Q2[4],MNG_Q2[8]],"#EBF5EB","Linear growth — healthy"),
    ("Q3 — Stations: Trips Starting and Ending  ⚠",
     [SQL_Q3[0],SQL_Q3[4],SQL_Q3[8]],[MNG_Q3[0],MNG_Q3[4],MNG_Q3[8]],"#FFF5E6","SQLite: super-linear!"),
    ("Q4 — Trips Containing at Least One ERROR Event",
     [SQL_Q4[0],SQL_Q4[4],SQL_Q4[8]],[MNG_Q4[0],MNG_Q4[4],MNG_Q4[8]],"#F5EBF5","Linear growth — healthy"),
]
xpos=np.arange(3)
for ax,(title,sql_v,mng_v,bg,note) in zip(axes.flatten(),scale_data):
    ax.set_facecolor(bg)
    ax.plot(xpos,sql_v,"o-", color=C_SQLITE,lw=2.8,ms=10,label="SQLite", zorder=3,markeredgecolor="white",markeredgewidth=1.5)
    ax.plot(xpos,mng_v,"s--",color=C_MONGO, lw=2.8,ms=10,label="MongoDB",zorder=3,markeredgecolor="white",markeredgewidth=1.5)
    ax.fill_between(xpos,sql_v,mng_v,alpha=0.08,color="#888888")
    for i,(sv,mv) in enumerate(zip(sql_v,mng_v)):
        os_=8 if sv>=mv else -18; om_=-18 if sv>=mv else 8
        ax.annotate(f"{sv:.3f}s",(i,sv),textcoords="offset points",xytext=(0,os_),ha="center",fontsize=8.5,color=C_SQLITE,fontweight="bold")
        ax.annotate(f"{mv:.3f}s",(i,mv),textcoords="offset points",xytext=(0,om_),ha="center",fontsize=8.5,color=C_MONGO,fontweight="bold")
    ax.set_title(title,fontsize=11,fontweight="bold",color="#1F3864",pad=8)
    ax.set_ylabel("Time (seconds)",fontsize=10)
    ax.set_xlabel("Number of trips",fontsize=10)
    ax.set_xticks(xpos); ax.set_xticklabels(TRIP_LBLS,fontsize=10)
    ax.grid(True,alpha=0.25,linestyle="--",zorder=0)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.legend(fontsize=10,loc="upper left")
    ax.text(0.99,0.05,note,transform=ax.transAxes,fontsize=8.5,fontstyle="italic",
            color="#555555",ha="right",va="bottom",
            bbox=dict(boxstyle="round,pad=0.3",facecolor="white",edgecolor="#cccccc",alpha=0.9))
plt.tight_layout(h_pad=3.5,w_pad=2.5)
fig.savefig("graphs/graph_C_scalability.png",dpi=180,bbox_inches="tight",facecolor=fig.get_facecolor())
plt.close(fig)
print("Saved → graphs/graph_C_scalability.png")

print("\n" + "="*50)
print("  All 3 graphs saved in  graphs/  folder!")
print("="*50)
print("\n  graph_A_sqlite_vs_mongodb.png")
print("  graph_B_spark_vs_mongodb.png")
print("  graph_C_scalability.png")

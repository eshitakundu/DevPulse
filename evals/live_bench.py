import json, time, statistics, urllib.request, urllib.parse, sys
tools = ["Bun","Deno","Zig","htmx","Svelte","Tailwind","SQLite","DuckDB","Polars","FastAPI","Rust","Go","Kubernetes","Terraform","Redis","Postgres","Supabase","Vite","Ruff","uv"]
rows=[]
def get(t):
    u="https://devpulse.eshita.dev/api/report?tool="+urllib.parse.quote(t)
    req=urllib.request.Request(u,headers={"User-Agent":"devpulse-bench/1.0"})
    t0=time.time()
    with urllib.request.urlopen(req,timeout=180) as r: d=json.load(r)
    return time.time()-t0,d
for t in tools:
    try:
        s1,d1=get(t); s2,d2=get(t)
        r=d1["report"]
        rows.append(dict(tool=t,first_s=round(s1,2),cached_first=d1["cached"],second_s=round(s2,2),cached_second=d2["cached"],written_by=r["written_by"],pros=len(r["pros"]),cons=len(r["cons"]),rejected=len(r["rejected"]),comments=len(r["comments"])))
    except Exception as e:
        rows.append(dict(tool=t,error=str(e)[:120]))
    print(rows[-1],flush=True)
json.dump(rows,open(sys.argv[1],"w"),indent=1)

"""FastAPI read-only inventory and topology endpoints."""
from __future__ import annotations
from contextlib import asynccontextmanager
from dataclasses import asdict
import asyncio
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from .collector import make_subscriber
from .config import Settings, from_env
from .database import collect
from .model import Topology
from .monitoring import update as update_metrics

LOG = logging.getLogger(__name__)


def create_app(topology: Topology | None = None, start_mqtt: bool = False,
               settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    graph = topology or Topology(settings.stale_after, settings.offline_after)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        subscriber = None
        if start_mqtt:
            subscriber = make_subscriber(graph, settings)
            subscriber.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=12)
            subscriber.loop_start()
        db_task = None
        if start_mqtt and settings.db_dsn:
            async def watch_db():
                while True:
                    result = await asyncio.to_thread(collect, settings.db_dsn)
                    graph.observe_database(asdict(result))
                    await asyncio.sleep(5)
            db_task = asyncio.create_task(watch_db())
        try:
            yield
        finally:
            if db_task:
                db_task.cancel()
                try:
                    await db_task
                except asyncio.CancelledError:
                    pass
            if subscriber:
                subscriber.disconnect()
                subscriber.loop_stop()

    app = FastAPI(title="SignalAtlas", version="0.1.0", lifespan=lifespan)
    app.state.topology = graph
    app.state.settings = settings

    @app.get("/health")
    def health():
        # API process liveness, NOT end-to-end industrial connectivity.
        return {"api": "alive", "broker_connected": graph.broker_connected}

    @app.get("/ready")
    def readiness():
        if not graph.broker_connected or not graph.subscription_ready:
            raise HTTPException(status_code=503, detail="MQTT subscription not ready")
        return {"mqtt_subscription": "ready"}

    @app.get("/api/topology")
    def topology_data():
        return graph.snapshot()

    @app.get("/api/nodes")
    def nodes():
        return graph.snapshot()["nodes"]

    @app.get("/api/nodes/{node_id}")
    def node(node_id: str):
        for entry in graph.snapshot()["nodes"]:
            if entry["id"] == node_id:
                return entry
        raise HTTPException(404, detail="Unknown topology node")

    @app.get("/api/links")
    def links():
        return graph.snapshot()["links"]

    @app.get("/api/incidents")
    def incidents():
        return graph.snapshot()["incidents"]

    @app.get("/api/database")
    def database():
        measured = asdict(collect(settings.db_dsn))
        if settings.db_dsn:
            graph.observe_database(measured)
        return measured

    @app.get("/metrics")
    def metrics():
        # Prometheus scrapeable observations, not synthetic gauges.
        update_metrics(graph)
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/", response_class=HTMLResponse)
    def operator_preview():
        # Diagnostic fallback, NOT Ignition Perspective. No actuator controls.
        return HTMLResponse("""<!doctype html><html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'><title>SignalAtlas | Live topology</title>
<style>
:root{font:14px system-ui;color:#e5eaf5;background:#08111e}*{box-sizing:border-box}
body{max-width:1200px;margin:auto;padding:25px}header{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}
h1{font-size:31px;letter-spacing:-1px;margin:0}.sub{color:#92a9c7}
.tag{border:1px solid #33465f;border-radius:30px;padding:8px 12px;color:#9bc9f4}
main{display:grid;grid-template-columns:1.45fr 1fr;gap:18px;margin-top:24px}
.panel{background:#111f31;border:1px solid #263950;border-radius:12px;padding:20px}
h2{font-size:15px;color:#bcd2ef;margin-top:0}button{cursor:pointer;border:1px solid #395573;color:#e5eaf5;background:#172c43;padding:12px;border-radius:8px;text-align:left}
button:hover,button:focus-visible{outline:2px solid #8daeff}.edges{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.node{display:block;width:100%;margin:9px 0}.spine{text-align:center;color:#b8c7df;padding:10px;border-left:2px dashed #4e6c8b;margin:9px auto;width:max-content}
.state{float:right;font-weight:700;font-size:12px}.HEALTHY{color:#6de1ac}.DEGRADED,.STALE{color:#f7ca79}.OFFLINE{color:#ff7d8f}.UNKNOWN{color:#95a3ba}
pre{overflow:auto;white-space:pre-wrap;font:12px/1.5 ui-monospace,monospace;color:#c4d3ea}
small{color:#9aaecb}.summary{font-size:12px;color:#9db6d2;margin-top:15px}
@media(max-width:760px){main{grid-template-columns:1fr}.edges{grid-template-columns:1fr}body{padding:15px}}
</style></head><body><header><div><h1>SignalAtlas<span style='color:#65c8ff'>.</span></h1>
<p class='sub'>Industrial connectivity observability / Synthetic lab</p></div>
<div class='tag'>READ-ONLY · Observed signals only</div></header><main>
<section class='panel'><h2>Live connectivity</h2><div id='edges' class='edges'></div>
<div class='spine'>↓ MQTT links ↓</div><button class='node' data-id='broker' id='broker'>Broker</button>
<div class='spine'>↓ uninstrumented ↓</div>
<button class='node' data-id='ignition' id='ignition'>Ignition</button>
<div class='spine'>↓ uninstrumented ↓</div>
<button class='node' data-id='postgres' id='postgres'>Historian</button>
<p class='summary'>States are based on received evidence. Uninstrumented systems stay UNKNOWN.</p></section>
<section class='panel'><h2>Evidence inspector</h2><pre id='detail' aria-live='polite'>Select a node to inspect its observations.</pre>
<h2>Latest incidents</h2><pre id='incidents'>No state changes observed</pre></section></main>
<script>
let selected='edge-a';const esc=s=>String(s).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
function show(n){return `<span>${esc(n.id)}</span><span class='state ${esc(n.status)}'>${esc(n.status)}</span>`}
async function refresh(){try{const r=await fetch('/api/topology',{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const g=await r.json();
let e=document.getElementById('edges');e.innerHTML=g.nodes.filter(n=>n.id.startsWith('edge-')).map(n=>`<button data-id='${esc(n.id)}'>${show(n)}</button>`).join('');
for(const id of ['broker','ignition','postgres'])document.getElementById(id).innerHTML=show(g.nodes.find(n=>n.id===id));
e.querySelectorAll('button').forEach(b=>b.onclick=()=>{selected=b.dataset.id;refresh()});
for(const id of ['broker','ignition','postgres'])document.getElementById(id).onclick=()=>{selected=id;refresh()};
const n=g.nodes.find(n=>n.id===selected);document.getElementById('detail').textContent=JSON.stringify(n,null,2);
document.getElementById('incidents').textContent=JSON.stringify(g.incidents.slice(0,8),null,2);
}catch(e){document.getElementById('detail').textContent='Observability API unavailable: '+e.message}}
refresh();setInterval(refresh,3000);</script></body></html>""")
    return app


app = create_app(settings=from_env(), start_mqtt=True) if os.getenv("SIGNALATLAS_RUNTIME") == "1" else create_app()

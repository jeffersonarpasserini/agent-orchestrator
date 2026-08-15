from html import escape

from orchestrator.reserve_ledger import ReserveMetricsSnapshot


def render_reserve_dashboard(snapshot: ReserveMetricsSnapshot) -> str:
    statuses = "".join(
        f"<tr><td>{escape(status)}</td><td>{count}</td></tr>"
        for status, count in sorted(snapshot.status_counts.items())
    )
    models = "".join(
        f"<tr><td>{escape(model)}</td><td>{count}</td></tr>"
        for model, count in sorted(snapshot.model_counts.items())
    )
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Reserva DeepSeek</title></head>
<body><main><h1>Reserva DeepSeek</h1>
<p>Ativações: {snapshot.total_activations}</p>
<p>Custo direto: US$ {snapshot.direct_cost_usd:.12f}</p>
<h2>Estados</h2><table><tr><th>Estado</th><th>Total</th></tr>{statuses}</table>
<h2>Modelos</h2><table><tr><th>Modelo</th><th>Total</th></tr>{models}</table>
</main></body></html>"""

from app.domain.entities import Node, Edge

def _source(label="Sun", uev=1.0, amount=100, node_id=None):
    kwargs = {"label": label, "type": "source", "uev": uev, "category": "renewable", "amount": amount}
    if node_id:
        kwargs["id"] = node_id
    return Node(**kwargs)

def _process(label, node_id=None, is_multi_output=False, multi=False):
    """Gera um nó do tipo process. 
    Aceita 'is_multi_output' ou 'multi' para manter compatibilidade com todos os testes.
    """
    multi_output = is_multi_output or multi
    kwargs = {"label": label, "type": "process", "is_multi_output": multi_output}
    if node_id:
        kwargs["id"] = node_id
    return Node(**kwargs)

def _edge(source, target, amount=100.0):
    return Edge(source=source, target=target, amount=amount)
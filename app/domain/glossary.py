"""
Glossário de conceitos emergéticos e da metodologia de cálculo.
Atende ao Requisito Funcional Opcional 2 (RFO 2) do planejamento.
"""

from typing import TypedDict


class Termo(TypedDict):
    termo: str
    categoria: str
    definicao: str
    referencia: str


_GLOSSARIO: list[Termo] = [
    # ── Conceitos fundamentais ─────────────────────────────────────────────
    {
        "termo": "Emergia",
        "categoria": "Conceito fundamental",
        "definicao": (
            "Quantidade total de energia de um único tipo (geralmente energia solar equivalente) "
            "necessária, direta ou indiretamente, para produzir um produto ou serviço. "
            "Difere da energia convencional por contabilizar o trabalho ambiental incorporado "
            "ao longo de toda a cadeia de produção."
        ),
        "referencia": "Odum, H.T. (1996). Environmental Accounting: Emergy and Environmental Decision Making.",
    },
    {
        "termo": "Transformidade (UEV)",
        "categoria": "Conceito fundamental",
        "definicao": (
            "Unit Emergy Value (UEV) ou Transformidade: razão entre a emergia total necessária "
            "para produzir um fluxo e a energia ou massa desse fluxo. "
            "Unidade: sej/J (solar emjoule por joule) ou sej/g. "
            "Quanto maior a transformidade, mais elaborado e raro é o produto no contexto ecossistêmico."
        ),
        "referencia": "Odum, H.T. (1988). Self-organization, transformity, and information. Science, 242(4882).",
    },
    {
        "termo": "Solar emjoule (sej)",
        "categoria": "Unidade de medida",
        "definicao": (
            "Unidade de medida da emergia. Representa a quantidade equivalente de energia solar "
            "que foi necessária para gerar determinado produto ou serviço. "
            "É a unidade padronizada usada globalmente em avaliações emergéticas."
        ),
        "referencia": "Brown, M.T.; Ulgiati, S. (2004). Emergy Analysis and Environmental Accounting.",
    },
    {
        "termo": "Avaliação Emergética (Emergy Analysis)",
        "categoria": "Metodologia",
        "definicao": (
            "Método desenvolvido por Howard T. Odum para quantificar o trabalho da natureza e "
            "da economia humana incorporado em produtos e serviços. "
            "Utiliza as quatro regras da álgebra emergética aplicadas a grafos de fluxo de energia, "
            "matéria e informação."
        ),
        "referencia": "Odum, H.T. (1996). Environmental Accounting: Emergy and Environmental Decision Making.",
    },
    # ── Álgebra emergética ─────────────────────────────────────────────────
    {
        "termo": "Regra 1 — Atribuição à saída",
        "categoria": "Álgebra emergética",
        "definicao": (
            "Toda a emergia proveniente de uma fonte é atribuída integralmente à sua saída. "
            "Não há perda ou divisão nesse estágio: o fluxo de emergia da fonte é transferido "
            "por completo ao processo que ela alimenta."
        ),
        "referencia": "Odum, H.T. (1996). Capítulo 3 — Emergy Algebra.",
    },
    {
        "termo": "Regra 2 — Co-produtos",
        "categoria": "Álgebra emergética",
        "definicao": (
            "Quando um processo gera múltiplos produtos simultaneamente (co-produtos), cada produto "
            "recebe a emergia TOTAL do processo, sem divisão entre eles. "
            "Isso reflete o fato de que todos os insumos foram necessários para produzir cada co-produto. "
            "Exemplo: etanol e bagaço gerados pela cana-de-açúcar recebem, cada um, "
            "toda a emergia do processo de destilação."
        ),
        "referencia": "Odum, H.T. (1996). Capítulo 3 — Emergy Algebra.",
    },
    {
        "termo": "Regra 3 — Divisão de caminhos",
        "categoria": "Álgebra emergética",
        "definicao": (
            "Quando um fluxo se divide em dois ou mais caminhos (sem ser co-produto), "
            "a emergia é distribuída proporcionalmente à quantidade de energia/massa em cada caminho. "
            "A soma das emergia parciais dos caminhos resultantes é igual à emergia original."
        ),
        "referencia": "Odum, H.T. (1996). Capítulo 3 — Emergy Algebra.",
    },
    {
        "termo": "Regra 4 — Não duplicação",
        "categoria": "Álgebra emergética",
        "definicao": (
            "A emergia não pode ser contada duas vezes. Quando fluxos oriundos da mesma fonte "
            "primária convergem em um ponto (retroalimentações ou co-produtos que se reúnem), "
            "utiliza-se apenas o MAIOR valor de emergia entre os caminhos convergentes, "
            "e não a soma deles. Isso evita a inflação artificial do resultado."
        ),
        "referencia": "Odum, H.T. (1996). Capítulo 3 — Emergy Algebra.",
    },
    # ── Estrutura do grafo ─────────────────────────────────────────────────
    {
        "termo": "Nó (No)",
        "categoria": "Estrutura do grafo",
        "definicao": (
            "Elemento do grafo que representa uma etapa do processo ou uma fonte primária de energia. "
            "Tipos: 'source' (fonte primária, com UEV e quantidade definidos) e "
            "'process' (transformação intermediária ou produto final)."
        ),
        "referencia": "Implementação interna — entities.py.",
    },
    {
        "termo": "Aresta",
        "categoria": "Estrutura do grafo",
        "definicao": (
            "Elemento do grafo que representa o fluxo de energia, massa ou informação entre dois nós. "
            "Possui origem, destino, quantidade e unidade. "
            "A quantidade é usada para calcular a proporção na divisão de caminhos (Regra 3)."
        ),
        "referencia": "Implementação interna — entities.py.",
    },
    {
        "termo": "Processo multi-saída (is_multi_output)",
        "categoria": "Estrutura do grafo",
        "definicao": (
            "Nó do tipo 'process' marcado como multi-saída. "
            "Indica que suas saídas são co-produtos (Regra 2): cada saída recebe a emergia total "
            "do processo, em vez de receber uma fração proporcional."
        ),
        "referencia": "Implementação interna — entities.py; Odum (1996) Regra 2.",
    },
    {
        "termo": "Busca em Profundidade (DFS)",
        "categoria": "Algoritmo",
        "definicao": (
            "Algoritmo de percurso de grafos usado pelo motor de cálculo. "
            "Percorre recursivamente os predecessores de cada nó para acumular a emergia, "
            "com memoização (cache) para evitar recálculos e detecção de ciclos para "
            "prevenir recursão infinita em grafos com retroalimentação."
        ),
        "referencia": "Cormen et al. (2009). Introduction to Algorithms — Capítulo 22.",
    },
    # ── Indicadores e resultados ───────────────────────────────────────────
    {
        "termo": "Emergia total do sistema",
        "categoria": "Resultado",
        "definicao": (
            "Soma das emergia de todos os nós folha (nós sem saída) do grafo. "
            "Representa a emergia incorporada no(s) produto(s) final(is) do processo analisado."
        ),
        "referencia": "Odum, H.T. (1996). Environmental Accounting.",
    },
    {
        "termo": "Renovabilidade (%R)",
        "categoria": "Indicador",
        "definicao": (
            "Percentual da emergia total proveniente de fontes renováveis (sol, vento, chuva). "
            "Quanto maior o %R, mais sustentável é o processo em termos emergéticos. "
            "Calculado como: R / (R + N + F) × 100, onde R = renováveis, N = não-renováveis "
            "locais e F = materiais e serviços importados."
        ),
        "referencia": "Brown, M.T.; Ulgiati, S. (1997). Emergy-based indices and ratios.",
    },
    {
        "termo": "Razão de Rendimento Emergético (EYR)",
        "categoria": "Indicador",
        "definicao": (
            "Emergy Yield Ratio: razão entre a emergia total do produto e a emergia dos "
            "insumos econômicos investidos (F). EYR = Y / F. "
            "Avalia a capacidade do processo de amplificar recursos locais com insumos externos. "
            "Valores > 1 indicam que o processo contribui líquido para a economia."
        ),
        "referencia": "Odum, H.T. (1996). Environmental Accounting.",
    },
    {
        "termo": "SCALE",
        "categoria": "Referência de software",
        "definicao": (
            "Software de referência para cálculos emergéticos desenvolvido pela Universidade da Flórida. "
            "Este sistema foi desenvolvido como alternativa simplificada ao SCALE, "
            "voltada ao público brasileiro e com curva de aprendizado reduzida."
        ),
        "referencia": "University of Florida — Center for Environmental Policy.",
    },
]


def get_glossary() -> dict:
    """
    Retorna o glossário completo organizado por categoria.
    """
    categorias: dict[str, list] = {}
    for termo in _GLOSSARIO:
        cat = termo["categoria"]
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append({
            "termo": termo["termo"],
            "definicao": termo["definicao"],
            "referencia": termo["referencia"],
        })

    return {
        "total_termos": len(_GLOSSARIO),
        "categorias": [
            {"nome": cat, "termos": termos}
            for cat, termos in categorias.items()
        ],
    }
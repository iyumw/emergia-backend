"""
Suite completa de testes do motor de cálculo emergético.

Cobertura alvo: ≥ 80% (RNF 3.1.8)
Cenários obrigatórios (RNF 3.1.10):
  - Grafo sem co-produtos
  - Grafo com co-produtos
  - Grafo com loop/retroalimentação

Execute com:
    pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=80
"""

import io
import pytest
from app.application.emergy_calculator import EmergyCalculator
from app.domain.entities import GraphData, No, Aresta
from app.infrastructure.adapters.importador import (
    parse_nodes,
    parse_sources,
    parse_edges,
    build_graph_data_from_csvs,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def calculator():
    return EmergyCalculator()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de construção de grafo
# ─────────────────────────────────────────────────────────────────────────────

def _fonte(label="Sol", uev=1.0, quantidade=1000.0, node_id=None) -> No:
    kwargs = dict(label=label, tipo="source", uev=uev, categoria="renovável", quantidade=quantidade)
    if node_id:
        kwargs["id"] = node_id
    return No(**kwargs)


def _processo(label, multi=False, node_id=None) -> No:
    kwargs = dict(label=label, tipo="process", is_multi_output=multi)
    if node_id:
        kwargs["id"] = node_id
    return No(**kwargs)


def _aresta(origem, destino, quantidade=1000.0) -> Aresta:
    return Aresta(origem=origem, destino=destino, quantidade=quantidade)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Regras de Odum
# ─────────────────────────────────────────────────────────────────────────────

class TestRegrasOdum:

    def test_regra1_emergia_da_fonte_vai_para_saida(self, calculator):
        """Regra 1: toda a emergia da fonte é atribuída ao processo de saída."""
        src = _fonte(uev=2.0, quantidade=500.0, node_id="SRC")  # 2 * 500 = 1000 sej
        p1 = _processo("Processo A", node_id="P1")
        data = GraphData(Nos=[src, p1], Arestas=[_aresta("SRC", "P1")])
        result = calculator.calculate(data)
        p1_contrib = next(c for c in result["contributions"] if c["id"] == "P1")
        assert p1_contrib["value"] == pytest.approx(1000.0)

    def test_regra2_co_produtos_recebem_valor_total(self, calculator):
        """Regra 2: co-produtos recebem o valor TOTAL da entrada (não divide)."""
        src = _fonte(node_id="SRC")
        p1 = _processo("Destilaria", multi=True, node_id="P1")
        out1 = _processo("Etanol", node_id="OUT1")
        out2 = _processo("Bagaco", node_id="OUT2")
        data = GraphData(
            Nos=[src, p1, out1, out2],
            Arestas=[
                _aresta("SRC", "P1"),
                _aresta("P1", "OUT1", 800),
                _aresta("P1", "OUT2", 200),
            ],
        )
        result = calculator.calculate(data)
        etanol = next(c for c in result["contributions"] if c["id"] == "OUT1")
        bagaco = next(c for c in result["contributions"] if c["id"] == "OUT2")
        assert etanol["value"] == pytest.approx(1000.0)
        assert bagaco["value"] == pytest.approx(1000.0)

    def test_regra3_divisao_proporcional_ao_fluxo(self, calculator):
        """Regra 3: sem co-produto, a emergia divide proporcionalmente ao fluxo."""
        src = _fonte(node_id="SRC")
        p1 = _processo("Divisor", multi=False, node_id="P1")
        out1 = _processo("Saida 1", node_id="OUT1")
        out2 = _processo("Saida 2", node_id="OUT2")
        data = GraphData(
            Nos=[src, p1, out1, out2],
            Arestas=[
                _aresta("SRC", "P1"),
                _aresta("P1", "OUT1", 700),
                _aresta("P1", "OUT2", 300),
            ],
        )
        result = calculator.calculate(data)
        out1_c = next(c for c in result["contributions"] if c["id"] == "OUT1")
        out2_c = next(c for c in result["contributions"] if c["id"] == "OUT2")
        assert out1_c["value"] == pytest.approx(700.0)
        assert out2_c["value"] == pytest.approx(300.0)

    def test_regra4_evita_dupla_contagem(self, calculator):
        """Regra 4: caminhos da mesma fonte que convergem usam o maior valor, não somam."""
        src = _fonte(node_id="SRC")
        p1 = _processo("Processo A", multi=True, node_id="P1")
        p2 = _processo("Processo B", node_id="P2")
        final = _processo("Juncao", node_id="FINAL")
        data = GraphData(
            Nos=[src, p1, p2, final],
            Arestas=[
                _aresta("SRC", "P1"),
                _aresta("P1", "P2"),
                _aresta("P1", "FINAL"),   # caminho 1
                _aresta("P2", "FINAL"),   # caminho 2 — mesma origem
            ],
        )
        result = calculator.calculate(data)
        final_c = next(c for c in result["contributions"] if c["id"] == "FINAL")
        # Não deve somar 2000; deve ser 1000
        assert final_c["value"] == pytest.approx(1000.0)

    def test_regra4_fontes_independentes_somam(self, calculator):
        """Regra 4 negativa: fontes distintas devem SER somadas (não são duplicatas)."""
        src1 = _fonte(label="Sol", uev=1.0, quantidade=600.0, node_id="SRC1")
        src2 = _fonte(label="Chuva", uev=1.0, quantidade=400.0, node_id="SRC2")
        p1 = _processo("Planta", node_id="P1")
        data = GraphData(
            Nos=[src1, src2, p1],
            Arestas=[
                _aresta("SRC1", "P1", 600),
                _aresta("SRC2", "P1", 400),
            ],
        )
        result = calculator.calculate(data)
        p1_c = next(c for c in result["contributions"] if c["id"] == "P1")
        assert p1_c["value"] == pytest.approx(1000.0)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Grafo com loop / retroalimentação (RNF 3.1.10 — cenário obrigatório)
# ─────────────────────────────────────────────────────────────────────────────

class TestGrafoComLoop:

    def test_loop_direto_nao_causa_recursao_infinita(self, calculator):
        """
        Grafo com loop/feedback direto: A → B → A.
        O cálculo deve encerrar (sem RecursionError) e produzir um resultado
        consistente — a detecção de ciclo retorna 0 para a aresta de volta,
        quebrando o loop de forma controlada.
        """
        src = _fonte(node_id="SRC")
        pa = _processo("Processo A", node_id="PA")
        pb = _processo("Processo B", node_id="PB")
        data = GraphData(
            Nos=[src, pa, pb],
            Arestas=[
                _aresta("SRC", "PA"),
                _aresta("PA", "PB"),
                _aresta("PB", "PA"),  # retroalimentação — cria o loop
            ],
        )
        # Não deve lançar exceção
        result = calculator.calculate(data)
        assert "total_emergy" in result
        assert result["total_emergy"] >= 0

    def test_loop_indireto_tres_nos(self, calculator):
        """Loop indireto: A → B → C → A. Deve encerrar sem erro."""
        src = _fonte(node_id="SRC")
        pa = _processo("A", node_id="PA")
        pb = _processo("B", node_id="PB")
        pc = _processo("C", node_id="PC")
        data = GraphData(
            Nos=[src, pa, pb, pc],
            Arestas=[
                _aresta("SRC", "PA"),
                _aresta("PA", "PB"),
                _aresta("PB", "PC"),
                _aresta("PC", "PA"),  # fecha o loop
            ],
        )
        result = calculator.calculate(data)
        assert "total_emergy" in result
        assert result["total_emergy"] >= 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Testes de integração — CSV → Grafo → Cálculo (RNF 3.1.10)
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegracaoCSV:
    """
    IDs são declarados explicitamente nos CSVs para que a segunda parseagem
    dentro de build_graph_data_from_csvs produza os mesmos IDs usados nas arestas.
    Isso evita o problema de double-parse com UUIDs gerados aleatoriamente.
    """

    # IDs fixos declarados uma única vez como constantes da classe
    SRC_ID = "src-solar-01"
    P1_ID  = "proc-plant-01"
    P2_ID  = "proc-colh-01"

    NODES_CSV = (
        "id,label,is_multi_output\n"
        f"{P1_ID},Plantação,false\n"
        f"{P2_ID},Colheita,false\n"
    )
    SOURCES_CSV = (
        "id,label,uev,categoria,quantidade\n"
        f"{SRC_ID},Energia Solar,1.0,renovável,3500000.0\n"
    )
    EDGES_CSV = (
        "origem,destino,quantidade\n"
        f"{SRC_ID},{P1_ID},3500000.0\n"
        f"{P1_ID},{P2_ID},1000.0\n"
    )

    def test_grafo_sem_coprodutos_csv(self, calculator):
        """Integração: CSV sem co-produtos → cálculo emergético correto."""
        data = build_graph_data_from_csvs(self.NODES_CSV, self.SOURCES_CSV, self.EDGES_CSV)

        assert len(data.Nos) == 3
        assert len(data.Arestas) == 2

        result = calculator.calculate(data)
        assert result["total_emergy"] == pytest.approx(3500000.0)

    def test_grafo_com_coprodutos_csv(self, calculator):
        """Integração: CSV com co-produtos → ambas saídas recebem emergia total."""
        nodes_csv = (
            "id,label,is_multi_output\n"
            "dest-01,Destilaria,true\n"
            "etanol-01,Etanol,false\n"
            "bagaco-01,Bagaco,false\n"
        )
        sources_csv = (
            "id,label,uev,categoria,quantidade\n"
            "sol-01,Sol,1.0,renovável,1000.0\n"
        )
        edges_csv = (
            "origem,destino,quantidade\n"
            "sol-01,dest-01,1000.0\n"
            "dest-01,etanol-01,800.0\n"
            "dest-01,bagaco-01,200.0\n"
        )
        data = build_graph_data_from_csvs(nodes_csv, sources_csv, edges_csv)
        result = calculator.calculate(data)

        etanol_c = next(c for c in result["contributions"] if c["id"] == "etanol-01")
        bagaco_c  = next(c for c in result["contributions"] if c["id"] == "bagaco-01")
        assert etanol_c["value"] == pytest.approx(1000.0)
        assert bagaco_c["value"]  == pytest.approx(1000.0)

    def test_resultado_possui_campos_obrigatorios(self, calculator):
        """Integração: resultado deve conter todos os campos esperados."""
        data = build_graph_data_from_csvs(self.NODES_CSV, self.SOURCES_CSV, self.EDGES_CSV)
        result = calculator.calculate(data)

        assert "total_emergy" in result
        assert "unit" in result
        assert result["unit"] == "sej"
        assert "stats" in result
        assert "contributions" in result
        assert "graph" in result
        assert result["stats"]["processing_time_ms"] >= 0

    def test_tempo_de_resposta_dentro_do_limite(self, calculator):
        """RNF 3.1.3: cálculo deve concluir em menos de 10 000 ms."""
        data = build_graph_data_from_csvs(self.NODES_CSV, self.SOURCES_CSV, self.EDGES_CSV)
        result = calculator.calculate(data)
        assert result["stats"]["processing_time_ms"] < 10_000


# ─────────────────────────────────────────────────────────────────────────────
# 4. Testes do importador CSV
# ─────────────────────────────────────────────────────────────────────────────

class TestImportador:

    def test_parse_nodes_gera_id_automatico(self):
        """IDs devem ser gerados automaticamente quando ausentes no CSV."""
        csv = "label,is_multi_output\nProcesso X,false\n"
        nodes = parse_nodes(csv)
        assert len(nodes) == 1
        assert nodes[0].id  # não vazio
        assert nodes[0].label == "Processo X"

    def test_parse_nodes_preserva_id_explicito(self):
        """ID explícito no CSV deve ser preservado."""
        csv = "id,label\nMEU_ID,Processo Y\n"
        nodes = parse_nodes(csv)
        assert nodes[0].id == "MEU_ID"

    def test_parse_sources_campos_obrigatorios(self):
        """sources.csv sem coluna obrigatória deve lançar ValueError."""
        csv_sem_uev = "label,categoria\nSol,renovável\n"
        with pytest.raises(ValueError, match="uev"):
            parse_sources(csv_sem_uev)

    def test_parse_sources_quantidade_padrao_1(self):
        """quantidade padrão deve ser 1.0 quando ausente."""
        csv = "label,uev,categoria\nSol,1.0,renovável\n"
        sources = parse_sources(csv)
        assert sources[0].quantidade == pytest.approx(1.0)

    def test_parse_edges_quantidade_invalida(self):
        """quantidade não numérica deve lançar ValueError."""
        csv = "origem,destino,quantidade\nA,B,INVALIDO\n"
        with pytest.raises(ValueError, match="Quantidade inválida"):
            parse_edges(csv, {"A", "B"})

    def test_parse_nodes_pula_linhas_vazias(self):
        """Linhas com label vazio devem ser ignoradas."""
        csv = "label\nValido\n\n   \n"
        nodes = parse_nodes(csv)
        assert len(nodes) == 1

    def test_build_graph_data_completo(self):
        """build_graph_data_from_csvs deve retornar GraphData com nós e arestas."""
        nodes_csv = "label\nProcesso A\n"
        sources_csv = "label,uev,categoria,quantidade\nSol,1.0,renovável,500.0\n"

        nodes = parse_nodes(nodes_csv)
        sources = parse_sources(sources_csv)
        edges_csv = f"origem,destino,quantidade\n{sources[0].id},{nodes[0].id},500.0\n"

        data = build_graph_data_from_csvs(nodes_csv, sources_csv, edges_csv)
        assert len(data.Nos) == 2
        assert len(data.Arestas) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 5. Testes de validação
# ─────────────────────────────────────────────────────────────────────────────

class TestValidacao:

    def test_grafo_vazio_lanca_erro(self, calculator):
        """Deve falhar com mensagem clara se o grafo estiver vazio."""
        data = GraphData(Nos=[], Arestas=[])
        with pytest.raises(ValueError, match="Grafo inválido"):
            calculator.calculate(data)

    def test_aresta_com_destino_inexistente(self, calculator):
        """Aresta apontando para nó inexistente deve lançar ValueError."""
        p1 = _processo("P1", node_id="P1")
        data = GraphData(
            Nos=[p1],
            Arestas=[Aresta(origem="P1", destino="FANTASMA", quantidade=10)],
        )
        with pytest.raises(ValueError, match="FANTASMA"):
            calculator.calculate(data)

    def test_no_source_sem_uev_lanca_erro(self):
        """Nó do tipo 'source' sem UEV deve falhar na validação Pydantic."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            No(label="Fonte Invalida", tipo="source", categoria="renovável", quantidade=100)

    def test_ids_dos_nos_sao_unicos(self):
        """IDs gerados automaticamente devem ser únicos entre si."""
        nos = [No(label=f"N{i}", tipo="process") for i in range(20)]
        ids = [n.id for n in nos]
        assert len(ids) == len(set(ids))

    def test_aresta_quantidade_zero_lanca_erro(self):
        """Aresta com quantidade zero deve falhar na validação Pydantic."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Aresta(origem="A", destino="B", quantidade=0)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Testes de desempenho — RNF 3.1.2 e 3.1.3
# ─────────────────────────────────────────────────────────────────────────────

class TestDesempenho:

    def _gerar_grafo_linear(self, n_processos: int) -> GraphData:
        """Cria um grafo linear: fonte → P0 → P1 → ... → P(n-1)."""
        src = _fonte(node_id="SRC_PERF")
        processos = [_processo(f"P{i}", node_id=f"PERF_{i}") for i in range(n_processos)]
        nos = [src] + processos

        arestas = [_aresta("SRC_PERF", "PERF_0")]
        for i in range(n_processos - 1):
            arestas.append(_aresta(f"PERF_{i}", f"PERF_{i+1}"))

        return GraphData(Nos=nos, Arestas=arestas)

    def test_grafo_medio_dentro_do_tempo_limite(self, calculator):
        """500 processos em cadeia linear: deve concluir em < 10 000 ms (RNF 3.1.3)."""
        data = self._gerar_grafo_linear(500)
        result = calculator.calculate(data)
        assert result["stats"]["processing_time_ms"] < 10_000

    def test_grafo_grande_sem_erro(self, calculator):
        """1 000 processos em cadeia: deve calcular sem exceção."""
        data = self._gerar_grafo_linear(1_000)
        result = calculator.calculate(data)
        assert result["total_emergy"] > 0

    def test_grafo_larga_escala_arestas(self, calculator):
        """
        Grafo em estrela com ~3 000 arestas (RNF 3.1.2):
        uma fonte → hub → 3 000 folhas.
        Verifica que o sistema suporta a escala sem falhas.
        """
        n_folhas = 3_000
        src = _fonte(node_id="SRC_STAR")
        hub = _processo("Hub", node_id="HUB")

        folhas = [_processo(f"F{i}", node_id=f"LEAF_{i}") for i in range(n_folhas)]
        nos = [src, hub] + folhas

        arestas = [_aresta("SRC_STAR", "HUB")]
        for i in range(n_folhas):
            arestas.append(_aresta("HUB", f"LEAF_{i}", 1.0))

        data = GraphData(Nos=nos, Arestas=arestas)
        result = calculator.calculate(data)

        assert result["stats"]["edges_count"] == n_folhas + 1
        assert result["stats"]["processing_time_ms"] < 10_000


# ─────────────────────────────────────────────────────────────────────────────
# 7. Testes do glossário
# ─────────────────────────────────────────────────────────────────────────────

class TestGlossario:

    def test_glossario_retorna_estrutura_correta(self):
        """Glossário deve retornar dict com total_termos e categorias."""
        from app.domain.glossario import get_glossario
        g = get_glossario()
        assert "total_termos" in g
        assert "categorias" in g
        assert g["total_termos"] > 0
        assert len(g["categorias"]) > 0

    def test_glossario_cada_categoria_tem_termos(self):
        """Cada categoria do glossário deve ter ao menos um termo."""
        from app.domain.glossario import get_glossario
        g = get_glossario()
        for cat in g["categorias"]:
            assert len(cat["termos"]) > 0

    def test_glossario_termos_possuem_campos_obrigatorios(self):
        """Cada termo deve ter 'termo', 'definicao' e 'referencia'."""
        from app.domain.glossario import get_glossario
        g = get_glossario()
        for cat in g["categorias"]:
            for termo in cat["termos"]:
                assert "termo" in termo
                assert "definicao" in termo
                assert "referencia" in termo
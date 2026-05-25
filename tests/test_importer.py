import pytest
import pandas as pd
import json
from io import BytesIO
from app.infrastructure.adapters.importer import _combine_into_result, _parse_edges_section, _parse_nodes_section, _parse_sources_section, build_from_xlsx, build_graph_data_from_csvs, build_graph_data_from_uploads

class TestImporter:

    def test_nodes_section_auto_generates_id(self):
        nodes = _parse_nodes_section("label,is_multi_output\nProcess X,false\n")
        assert len(nodes) == 1
        assert nodes[0].id
        assert nodes[0].label == "Process X"

    def test_nodes_section_preserves_explicit_id(self):
        nodes = _parse_nodes_section("id,label\nMY_ID,Process Y\n")
        assert nodes[0].id == "MY_ID"

    def test_parse_sources_invalid_numeric(self):
        invalid_sources_csv = "label,uev,category,amount\nFonte Invalida,abc,R,100"
        with pytest.raises(ValueError, match="Valor numérico inválido na seção 'sources'"):
            _parse_sources_section(invalid_sources_csv)

    def test_parse_sources_with_and_without_id(self):
        # Cenário A: ID Explícito fornecido no CSV
        csv_with_id = "id,label,uev,category,amount\nsrc-custom,Sol,1.0,R,500"
        nodes_with_id = _parse_sources_section(csv_with_id)
        assert nodes_with_id[0].id == "src-custom"

        # Cenário B: ID Ausente (força a execução de _generate_id())
        csv_no_id = "label,uev,category,amount\nSol,1.0,R,500"
        nodes_no_id = _parse_sources_section(csv_no_id)
        assert len(nodes_no_id[0].id) == 8

    def test_parse_nodes_with_and_without_id(self):
        csv_no_id = "label,is_multi_output\nProcesso Sem ID,false"
        nodes = _parse_nodes_section(csv_no_id)
        assert len(nodes[0].id) == 8

    def test_upload_single_json_success(self):
        """Linhas 200-225: Cobre o fluxo de upload bem-sucedido de um arquivo único .json."""
        json_payload = {
            "nodes": [
                {"id": "P1", "label": "Processo Teste", "type": "process", "is_multi_output": False},
                {"id": "S1", "label": "Fonte Solar", "type": "source", "uev": 2.5, "category": "R", "amount": 1000.0}
            ],
            "edges": [
                {"id": "E1", "source": "S1", "target": "P1", "amount": 1000.0}
            ]
        }
        raw_bytes = json.dumps(json_payload).encode("utf-8")
        result = build_graph_data_from_uploads({"diagrama.json": raw_bytes})
        
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.nodes[0].label == "Processo Teste"


    def test_upload_single_xlsx_success(self):
        """Linhas 200-225: Cobre o fluxo de upload bem-sucedido de um arquivo único .xlsx."""
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame([
                {"id": "P1", "label": "Refinaria", "is_multi_output": False}
            ]).to_excel(writer, sheet_name='nodes', index=False)
            
            pd.DataFrame([
                {"id": "S1", "label": "Petroleo", "uev": 50000.0, "category": "N", "amount": 10}
            ]).to_excel(writer, sheet_name='sources', index=False)
            
            pd.DataFrame([
                {"source": "S1", "target": "P1", "amount": 10}
            ]).to_excel(writer, sheet_name='edges', index=False)
        
        excel_bytes = output.getvalue()
        result = build_graph_data_from_uploads({"modelo.xlsx": excel_bytes})
        
        assert len(result.nodes) == 2
        assert result.edges[0].source == "S1"

    def test_upload_single_csv_error(self):
        """Linhas 200-225: Garante barramento amigável caso o usuário faça upload de um arquivo .csv solitário."""
        with pytest.raises(ValueError, match="O sistema não aceita um único arquivo .csv"):
            build_graph_data_from_uploads({"dados_solitarios.csv": b"id,label\nP1,Processo"})

    def test_upload_unsupported_format_error(self):
        """Linhas 200-225: Trata extensões não aceitas (ex: .txt, .png)."""
        with pytest.raises(ValueError, match="Formato não suportado"):
            build_graph_data_from_uploads({"diagrama.txt": b"conteudo de texto corrido"})

    def test_upload_empty_dict_error(self):
        """Linhas 200-225: Captura o fallback final caso o dicionário de uploads venha vazio."""
        with pytest.raises(ValueError, match="Formato não suportado"):
            build_graph_data_from_uploads({})
        
    def test_sources_section_missing_required_column(self):
        with pytest.raises(ValueError, match="uev"):
            _parse_sources_section("label,category\nSun,renewable\n")

    def test_sources_section_default_amount_is_one(self):
        sources = _parse_sources_section("label,uev,category\nSun,1.0,renewable\n")
        assert sources[0].amount == pytest.approx(1.0)

    def test_edges_section_invalid_amount(self):
        with pytest.raises(ValueError, match="Valor numérico inválido"):
            _parse_edges_section("source,target,amount\nA,B,NOT_A_NUMBER\n")

    def test_nodes_section_skips_blank_labels(self):
        nodes = _parse_nodes_section("label\nValid\n\n   \n")
        assert len(nodes) == 1

    def test_backwards_compat_multi_csv(self):
        data = build_graph_data_from_csvs(
            "id,label\nproc-a,Process A\n",
            "id,label,uev,category,amount\nsol-x,Sun,1.0,renewable,500.0\n",
            "source,target,amount\nsol-x,proc-a,500.0\n",
        )
        assert len(data.nodes) == 2
        assert len(data.edges) == 1

    def test_build_from_xlsx_corrupted(self):
        corrupted_bytes = b"dados de texto puramente aleatorios nao binarios"
        with pytest.raises(ValueError, match="Erro ao ler o arquivo Excel"):
            build_from_xlsx(corrupted_bytes)

    def test_build_graph_data_from_uploads_multiple_missing_required(self):
        files_data = {
            "apenas_sources.csv": b"label,uev,category,amount\nSol,1.0,R,500",
            "outro_arquivo_aleatorio.csv": b"conteudo qualquer"
        }
        with pytest.raises(ValueError, match="Para múltiplos arquivos, envie ao menos 'nodes' e 'edges'"):
            build_graph_data_from_uploads(files_data)

    def test_combine_into_result_empty(self):
        with pytest.raises(ValueError, match="O grafo precisa de pelo menos um nó"):
            _combine_into_result(nodes_csv="", sources_csv="", edges_csv="")

    # ─── Testes de validação de tamanho máximo de arquivo ───────────────────

    def test_file_exceeds_max_size_rejected(self):
        """Testa se MAX_FILE_SIZE_BYTES rejeita qualquer arquivo acima do limite."""
        from app.infrastructure.adapters.importer import MAX_FILE_SIZE_BYTES
        
        large_label = "X" * (MAX_FILE_SIZE_BYTES + 1000000)
        oversized_json = json.dumps({
            "nodes": [{"id": "P1", "label": large_label, "type": "process"}],
            "edges": []
        }).encode("utf-8")
        
        with pytest.raises(ValueError, match="muito grande"):
            build_graph_data_from_uploads({"diagrama.json": oversized_json})

    def test_json_within_max_size_accepted(self):
        """Testa que arquivo JSON dentro do limite é aceito."""
        json_payload = {
            "nodes": [{"id": "P1", "label": "Processo", "type": "process", "is_multi_output": False}],
            "edges": []
        }
        result = build_graph_data_from_uploads({"diagrama.json": json.dumps(json_payload).encode("utf-8")})
        assert len(result.nodes) == 1

    def test_xlsx_within_max_size_accepted(self):
        """Testa que arquivo XLSX dentro do limite é aceito."""
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame([{"id": "P1", "label": "Processo", "is_multi_output": False}]).to_excel(
                writer, sheet_name='nodes', index=False)
            pd.DataFrame([{"source": "P1", "target": "P1", "amount": 100}]).to_excel(
                writer, sheet_name='edges', index=False)
        result = build_graph_data_from_uploads({"modelo.xlsx": output.getvalue()})
        assert len(result.nodes) == 1

class TestExcelImporter:
    def test_import_valid_xlsx(self, calculator):
        # Criando um Excel em memória para testar
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame([
                {"id": "P1", "label": "Processo", "is_multi_output": False}
            ]).to_excel(writer, sheet_name='nodes', index=False)
            
            pd.DataFrame([
                {"id": "S1", "label": "Sol", "uev": 1.0, "category": "R", "amount": 500}
            ]).to_excel(writer, sheet_name='sources', index=False)
            
            pd.DataFrame([
                {"source": "S1", "target": "P1", "amount": 500}
            ]).to_excel(writer, sheet_name='edges', index=False)
        
        excel_bytes = output.getvalue()
        
        ir = build_from_xlsx(excel_bytes)
        result = calculator.calculate(ir.graph_data)
        
        assert result["total_emergy"] == 500.0
        assert len(ir.nodes) == 2

    
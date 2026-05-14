"""
Exceções customizadas para o motor de cálculo de emergia.
Mensagens padronizadas em PT-BR para exibição direta no Front-end.
"""

class EmergyError(Exception):
    """Exceção base para erros de emergia."""
    def __init__(self, message="Ocorreu um erro no cálculo de emergia."):
        self.message = message
        super().__init__(self.message)

class InvalidGraphError(EmergyError):
    """Erro lançado quando a estrutura do grafo é inválida."""
    def __init__(self, message="A estrutura do diagrama é inválida ou contém ciclos sem saída."):
        super().__init__(message)

class NodeNotFoundError(EmergyError):
    """Erro lançado quando um nó referenciado não existe."""
    def __init__(self, node_id=""):
        msg = f"O item '{node_id}' não foi encontrado no diagrama." if node_id else "Um item referenciado não existe."
        super().__init__(msg)

class InvalidNodeError(EmergyError):
    """Erro lançado quando um nó tem propriedades inválidas."""
    def __init__(self, label=""):
        msg = f"Os dados do item '{label}' estão incompletos ou incorretos." if label else "Dados de item inválidos."
        super().__init__(msg)

class InvalidEdgeError(EmergyError):
    """Erro lançado quando uma conexão entre itens é inválida."""
    def __init__(self, message="Há um problema em uma das conexões (setas) do diagrama."):
        super().__init__(message)
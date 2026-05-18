"""
Exceptions related to emergy calculations and graph validation.
"""

class EmergyError(Exception):
    """Base exception for emergy errors."""
    def __init__(self, message="Ocorreu um erro no cálculo de emergia."):
        self.message = message
        super().__init__(self.message)

class InvalidGraphError(EmergyError):
    """Error raised when the graph structure is invalid."""
    def __init__(self, message="A estrutura do diagrama é inválida ou contém ciclos sem saída."):
        super().__init__(message)

class NodeNotFoundError(EmergyError):
    """Error raised when a referenced node is not found."""
    def __init__(self, node_id=""):
        msg = f"O item '{node_id}' não foi encontrado no diagrama." if node_id else "Um item referenciado não existe."
        super().__init__(msg)

class InvalidNodeError(EmergyError):
    """Error raised when a node has invalid properties."""
    def __init__(self, label=""):
        msg = f"Os dados do item '{label}' estão incompletos ou incorretos." if label else "Dados de item inválidos."
        super().__init__(msg)

class InvalidEdgeError(EmergyError):
    """Error raised when an edge has invalid properties."""
    def __init__(self, message="Há um problema em uma das conexões (setas) do diagrama."):
        super().__init__(message)
from db.db import get_db


# Disponibiliza a conexão com o banco de dados
class Database:

    @staticmethod
    def get_db():
        yield from get_db()


# Instância utilizada nas rotas e dependências
database = Database()

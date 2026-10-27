-- Script do banco (dados fictícios) - ordem corrigida para rodar de uma vez
CREATE DATABASE IF NOT EXISTS banco_avaliacao;
USE banco_avaliacao;

-- Níveis de acesso
CREATE TABLE nivel_acesso (
    id_acesso INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50) NOT NULL
);

INSERT INTO nivel_acesso (id_acesso, nome) VALUES
    (1, 'Usuário comum'),
    (2, 'Gestor'),
    (3, 'Administrador');

-- Categorias dos equipamentos
CREATE TABLE categoria_equipamento (
    id_categoria INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO categoria_equipamento (nome) VALUES
    ('Informática'),
    ('Periféricos'),
    ('Equipamentos Audiovisuais');

-- Usuários
CREATE TABLE usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    cpf VARCHAR(20) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    nivel_acesso INT NOT NULL,
    status_usuario ENUM('ativo','inativo') DEFAULT 'ativo',
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (nivel_acesso) REFERENCES nivel_acesso(id_acesso)
);

-- Equipamentos
CREATE TABLE equipamentos (
    id_equipamento INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    modelo VARCHAR(100),
    descricao VARCHAR(100),
    numero_patrimonio VARCHAR(100) NOT NULL UNIQUE,
    id_categoria INT NOT NULL,
    status_equipamento ENUM('disponivel','emprestado','manutencao','inativo') DEFAULT 'disponivel',
    data_aquisicao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_categoria) REFERENCES categoria_equipamento(id_categoria)
);

-- Solicitações (data_solicitacao guarda data E hora do pedido)
CREATE TABLE solicitacoes (
    id_solicitacao INT AUTO_INCREMENT PRIMARY KEY,
    id_equipamento INT NOT NULL,
    id_solicitante INT NOT NULL,
    id_usuario_autorizador INT,
    data_solicitacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_retirada_solicitada DATETIME NOT NULL,
    data_prevista_devolucao DATETIME NOT NULL,
    data_autorizacao DATETIME,
    situacao ENUM('pendente','aprovado','recusado'),
    observacoes_solicitante VARCHAR(200),
    observacoes_autorizador VARCHAR(200),
    FOREIGN KEY (id_solicitante) REFERENCES usuarios(id_usuario),
    FOREIGN KEY (id_usuario_autorizador) REFERENCES usuarios(id_usuario),
    FOREIGN KEY (id_equipamento) REFERENCES equipamentos(id_equipamento)
);

-- Empréstimos
CREATE TABLE emprestimos (
    id_emprestimo INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    id_solicitacao INT NOT NULL,
    id_equipamento INT NOT NULL,
    data_retirada DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_prevista_devolucao DATETIME NOT NULL,
    data_devolucao DATETIME,
    observacoes VARCHAR(150),
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario),
    FOREIGN KEY (id_equipamento) REFERENCES equipamentos(id_equipamento),
    FOREIGN KEY (id_solicitacao) REFERENCES solicitacoes(id_solicitacao)
);

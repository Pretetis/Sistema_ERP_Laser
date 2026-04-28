# Sistema ERP - Gestão de Corte a Laser

Um sistema de Enterprise Resource Planning (ERP) customizado, focado na otimização e monitoramento de operações de corte a laser industrial. O sistema substitui fluxos de trabalho manuais por um painel automatizado e orientado a dados.

Este projeto adota uma arquitetura moderna e interativa construída inteiramente em Python, utilizando o framework Streamlit para o front-end web e módulos isolados para processamento de regras de negócio complexas.

## Telas do Sistema

Abaixo estão os módulos principais do sistema, estruturados para atender desde o planejamento da produção até o chão de fábrica.

### 1. Gestão de Corte

Módulo de Produção: Acompanhamento de ordens de corte, agrupamento inteligente de trabalhos (nesting lógico) para minimizar desperdício de material e organização da fila de produção.

### 2. Tela de Máquinas

Monitoramento em Tempo Real: Visualização do status das máquinas de corte a laser, disponibilidade de equipamentos e alocação de carga de trabalho para os operadores no chão de fábrica.

### 3. Envio de Programas e Extração PDF

Automação e Integração: Interface dedicada para o envio de programas CNC/Laser e um sistema integrado que extrai automaticamente dados técnicos de documentos e desenhos em PDF.

### 4. Dashboard de Métricas

Business Intelligence: Painel central com indicadores de desempenho (KPIs), métricas visuais e rastreamento de dados históricos para análise de produção e tomada de decisão estratégica.

## Arquitetura e Tecnologias

O projeto é construído em uma arquitetura modular em Python, garantindo fácil manutenção e expansibilidade para novos processos industriais.

Front-end e Web App

Framework Web: Streamlit (Python).

Interface (UI/UX): Estrutura multi-páginas (pages/) com navegação centralizada (utils/navigation.py).

Autenticação: Sistema de login seguro e gerenciamento de sessão baseado em perfis de usuário (utils/auth.py).

Back-end e Processamento

Linguagem Base: Python 3.9+.

Processamento de Dados: Lógicas de agrupamento de trabalho (utils/work_grouping.py) utilizando bibliotecas de dados (como Pandas).

Automação de Arquivos: Extração e parsing de dados diretamente de arquivos PDF industriais (utils/pdf_extractor.py).

Armazenamento: Conexão com banco de dados (utils/database.py) e rotinas de salvamento de arquivos (utils/storage.py).

## Como Executar o Projeto

Siga os passos abaixo para preparar o ambiente de desenvolvimento local.

### Pré-requisitos

É necessário possuir o Python (versão 3.9 ou superior) instalado na sua máquina.

Instalação

Clone o repositório para o seu ambiente local:

Instale as dependências requeridas do projeto:

Inicie o servidor local do Streamlit:

O sistema abrirá automaticamente no seu navegador padrão, geralmente no endereço http://localhost:8501.

### 📄 ValidaPy — Sistema de Gerenciamento de Contratos

* O ValidaPy é um sistema de gerenciamento de contratos desenvolvido em Python, com interface em linha de comando (CLI), integração  com MySQL e geração automática de contratos em PDF.

* O sistema permite cadastrar, consultar, organizar e auditar contratos de prestação de serviços, oferecendo validações, histórico e estrutura extensível.

# 🚀 Funcionalidades

- ✔️ Cadastro completo de contratos
- ✔️ Geração automática de PDF profissional
- ✔️ Numeração única de contratos
- ✔️ Validação e formatação de CNPJ
- ✔️ Registro de contratante e contratada
- ✔️ Seleção de ramos de atividade e tipos de serviço
- ✔️ Persistência em banco de dados MySQL
- ✔️ Busca de contratos por número ou empresa
- ✔️ Listagem geral de contratos
- ✔️ Verificação da integridade dos PDFs
- ✔️ Logs de ações do sistema
- ✔️ Estatísticas básicas (total, valor médio, contratos por mês)
- ✔️ Menu administrativo para manutenção do banco

# 🧠 Tecnologias Utilizadas

- 🐍 Python 3.8+

- 🗄️ MySQL

- 📄 FPDF2 (geração de PDF)

- 📦 mysql-connector-python

- 🧩 Programação orientada a objetos

- 🖥️ Interface CLI (terminal)


# 📂 Estrutura do Projeto

```bash
System-Contratos/
├── contratos/              # PDFs gerados automaticamente
├── contrato.py             # Lógica de contratos e geração de PDF
├── database.py             # Conexão e operações com MySQL
├── main.py                 # Interface CLI e fluxo principal
├── config.json             # Configurações do banco de dados
├── .gitignore
└── README.md
```

# ⚙️ Pré-requisitos

* Antes de executar o sistema, certifique-se de ter:

- Python 3.9 ou superior

- MySQL Server em execução

- Banco de dados configurado conforme a necessidade do projeto


# 📦 Instalação

- 1️⃣ Clone o repositório

``` bash
git clone https://github.com/Devmoises79/System-Contratos.git
cd System-Contratos
```


- 2️⃣ Crie um ambiente virtual (opcional, recomendado)

``` bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```


- 3️⃣ Instale as dependências

``` bash
pip install mysql-connector-python fpdf2
```

# 🔧 Configuração do Banco de Dados

- Edite o arquivo config.json com as credenciais do seu MySQL:

```bash
{
  "host": "localhost",
  "user": "seu_usuario",
  "password": "sua_senha",
  "database": "validapy"
}
```

- O sistema cria e valida automaticamente as tabelas na inicialização.


# ▶️ Como Executar

* Execute o sistema pelo terminal:

- python main.py


* Ao iniciar, o sistema exibirá o menu principal:

```bash
1. Criar novo contrato
2. Listar todos os contratos
3. Buscar contrato
4. Ver ramos de atividade
5. Ver tipos de serviço
6. Verificar arquivos PDF
7. Configurar sistema
8. Sair
```



# 📝 Cadastro de Contrato

- Durante o cadastro, o sistema coleta:

- Dados do contratante e contratada

- CNPJ (com validação e formatação)

- Ramo de atividade

- Tipo de serviço

- Valor do contrato

- Prazo

- Datas opcionais

- Especificação detalhada dos serviços



* Ao confirmar:

- O contrato é salvo no banco

- Um PDF é gerado automaticamente

- Um log da operação é registrado



# 📄 Geração de PDF

Os contratos são gerados com:

- Cabeçalho profissional

- Número único do contrato

- Dados completos das partes

- Valor formatado em padrão brasileiro

- Campo para assinaturas

- Rodapé automático



# 📂 Os arquivos são salvos em:

```bash
/contratos/
```


# 📊 Estatísticas do Sistema

* O sistema permite visualizar:

- Total de contratos cadastrados

- Valor total contratado

- Valor médio dos contratos

- Quantidade de contratos por mês



# 🛠️ Configurações Administrativas

* Menu de configurações permite:

- Recriar tabelas do banco

- Visualizar estatísticas do banco

- Limpar dados de teste

- Auditoria básica de registros



# 🔒 Boas Práticas Implementadas

- Separação de responsabilidades (CLI, regras de negócio, banco)

- Validações de entrada

- Tratamento de exceções

- Logs de ações

- Organização modular

- Código orientado à extensibilidade


# 🗺️ Roadmap (Próximas Evoluções/features)

- ⬜ Interface gráfica (Web ou Desktop)
- ⬜ Autenticação de usuários
- ⬜ Controle de permissões
- ⬜ Exportação para Excel
- ⬜ Upload de contratos assinados
- ⬜ API REST (FastAPI ou Flask)
- ⬜ Testes automatizados


# 👨‍💻 Autor

* Moisés Aniceto
* GitHub: https://github.com/Devmoises79


* Projeto desenvolvido para estudo, portfólio e evolução em backend Python, bancos de dados e automação documental.

# 📜 Licença

* Este projeto está sob a licença MIT.
* Sinta-se livre para estudar, modificar e evoluir.
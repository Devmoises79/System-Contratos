# 📄 System-Contratos

Sistema web para gerenciamento corporativo de contratos, empresas e usuários.

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![Flask](https://img.shields.io/badge/flask-2.0+-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## ✨ Características

- ✅ **Multi-empresa** - Suporte completo a múltiplas empresas
- ✅ **RBAC** - Controle de acesso baseado em perfis (Admin Sistema, Admin Empresa, Gestor, Analista, Assistente)
- ✅ **Fluxo de Aprovação** - Workflow completo de contratos
- ✅ **Segurança** - Bloqueio de IP, CSRF, senhas com hash
- ✅ **Logging** - Sistema completo de auditoria
- ✅ **PDF** - Geração de contratos em PDF
- ✅ **Dashboard** - Estatísticas e gráficos
- ✅ **Responsivo** - Interface adaptável a todos dispositivos

## 🚀 Tecnologias

### Backend
- **Python 3.8+**
- **Flask** - Framework web
- **MySQL** - Banco de dados relacional
- **Werkzeug** - Segurança e utilitários
- **ReportLab/WeasyPrint** - Geração de PDF

### Frontend
- **Bootstrap 5** - Framework CSS
- **JavaScript** - Interatividade
- **Font Awesome** - Ícones
- **Jinja2** - Templates

### Desenvolvimento
- **Pytest** - Testes automatizados
- **Logging** - Sistema de logs
- **Git** - Controle de versão

## 📋 Pré-requisitos

- Python 3.8 ou superior
- MySQL 5.7 ou superior
- pip (gerenciador de pacotes Python)

## 🔧 Instalação

1. **Clone o repositório**

```bash
git clone https://github.com/Devmoises79/System-Contratos.git
cd System-Contratos
```

# Crie um ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
```

# ou

```bash
venv\Scripts\activate  # Windows
Instale as dependências
```

```bash
pip install -r requirements.txt
Configure o banco de dados
```

```bash
# Crie o banco de dados MySQL
mysql -u root -p
CREATE DATABASE validapy CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;

# Execute as migrations
python scripts/migrate.py
Configure o arquivo config.py
```


# Execute a aplicação

```bash
python app.py
```

# 🧪 Testes
Execute os testes automatizados:

```bash
# Instalar dependências de teste
pip install pytest pytest-cov


# Executar todos os 

pytest tests/ -v

# Executar com cobertura
pytest tests/ --cov=. --cov-report=html

# Executar testes específicos
pytest tests/test_models.py -v
``` 

# 📁 Estrutura do Projeto

```text
System-Contratos/
├── admin/                 # Módulo de administração
├── auth/                  # Autenticação e autorização
├── core/                  # Utilitários centrais
│   ├── database.py       # Conexão com banco
│   ├── logging_config.py # Sistema de logs
│   └── utils.py          # Funções auxiliares
├── models/                # Modelos de dados
├── static/                # Arquivos estáticos
├── templates/             # Templates HTML
├── tests/                 # Testes automatizados
├── utils/                 # Utilitários
├── app.py                 # Aplicação principal
├── config.py              # Configurações (não versionado)
└── requirements.txt       # Dependências
```


# 🔐 Perfis de Acesso

text
Perfil	Descrição	Permissões
Admin Sistema	Controle total	Gerenciar empresas, usuários, logs, IPs
Admin Empresa	Gestão da empresa	Gerenciar usuários, configurações, estatísticas
Gestor	Aprovação	Aprovar contratos, visualizar relatórios
Analista	Análise	Visualizar dados, exportar relatórios
Assistente	Operacional	Criar e editar contratos
```

# 📊 Fluxo de Contratos

text
Rascunho → Em Análise → Aguardando Aprovação → Ativo
    ↑          ↓              ↓
    └──────────┴──────────────┘ (Revisão)
```

# 🛡️ Segurança

- ✅ Senhas com hash (PBKDF2)

- ✅ Proteção CSRF

- ✅ Bloqueio de IP por tentativas

- ✅ Sessões com timeout

- ✅ Sanitização de inputs

- ✅ Logs de auditoria

# 📝 TODO
- Implementar testes de integração

- Adicionar API REST completa

- Melhorar geração de PDF com WeasyPrint

- Adicionar WebSockets para notificações

- Implementar cache com Redis

- Adicionar dashboard de métricas em tempo real

#🤝 Contribuição
Contribuições são bem-vindas! 

* Fork o projeto

* Crie sua branch. Ex.: (git checkout -b feature/suaFeature)

* Commit suas mudanças. Ex.: e(git commit -m 'Add some ExFeature')

* Push para a branch. Ex.: (git push origin feature/ExFeature)

* Abra um Pull Request

# 📄 Licença
Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

📧 Contato
@Devmoises79 - GitHub
Linkedin: https://www.linkedin.com/in/moisés-aniceto-71042a251/

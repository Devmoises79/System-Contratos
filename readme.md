# 📄 System-Contratos

Sistema web para gerenciamento corporativo de contratos, empresas e usuários, com foco em regras de negócio, controle de acesso e segurança.

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![Flask](https://img.shields.io/badge/flask-2.0+-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## 📊 Visão Geral

Aplicação backend desenvolvida com Flask que implementa o ciclo completo de contratos, incluindo criação, análise, aprovação e acompanhamento.

O sistema foi estruturado com foco em organização de código, separação de responsabilidades e aplicação de regras de negócio reais.

---

## ✨ Funcionalidades

- **Multi-empresa** (isolamento de dados por organização)
- **RBAC (Role-Based Access Control)** com múltiplos perfis
- **Workflow de contratos** com estados, transições e revisões com justificativa
- **Gerenciamento completo de contratos** (criação, edição, análise e aprovação)
- **Sistema de autenticação e autorização**
- **Auditoria e logging**
- **Geração de contratos em PDF**
- **Dashboards e métricas**
- **Sistema de notificações**
- **Gamificação (pontos, ranking, níveis)**

---

## 🔐 Segurança

- Hash de senha (PBKDF2)
- Proteção contra CSRF
- Sanitização de inputs
- Bloqueio de IP por tentativas inválidas
- Controle de sessão com expiração
- Logs de auditoria

---

## 🧠 Regras de Negócio

O sistema implementa um fluxo completo de contratos:


Rascunho → Em Análise → Aguardando Aprovação → Ativo
↑ ↓ ↓
└───────────┴───────────────┘ (Revisão)


Ações disponíveis:

- Criar contrato
- Editar contrato
- Enviar para análise
- Enviar para aprovação
- Aprovar / devolver
- Revisar contrato

---

## 📌 Controle de Alterações (Auditoria de Edição)

O sistema implementa rastreabilidade nas solicitações de alteração de contratos.

Sempre que uma edição é solicitada (por Gestor, Admin ou Analista), o sistema registra:

- Justificativa da solicitação
- Usuário responsável pela ação
- Data e horário da solicitação

Essas informações são exibidas no fluxo do contrato, garantindo transparência e controle sobre mudanças.

---

## ⚙️ Tecnologias

### Backend
- Python 3.8+
- Flask
- MySQL
- Werkzeug

### Frontend
- Bootstrap 5
- JavaScript
- Jinja2

### Documentos
- ReportLab / WeasyPrint

### Testes & Qualidade
- Pytest
- Logging estruturado

---

## 📁 Estrutura do Projeto

```bash
System-Contratos/
├── admin/ # Módulos administrativos
├── auth/ # Autenticação e autorização
├── core/ # Banco, logging, utilitários
├── models/ # Modelos de domínio
├── templates/ # Interface (views)
├── static/ # Arquivos estáticos
├── tests/ # Testes automatizados
├── app.py # Aplicação principal
```

---

## 🚀 Instalação

```bash
git clone https://github.com/Devmoises79/System-Contratos.git
cd System-Contratos

python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

- Dependências:
```bash
pip install -r requirements.txt
```

- Configuração do banco:

```bash
mysql -u root -p

CREATE DATABASE validapy 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;
```

- Script:

```bash
python scripts/migrate.py
```

# ▶️ Execução

```bash
python app.py
```

# 🧪 Testes

```bash
pytest tests/ -v
pytest tests/ --cov=. --cov-report=html
pytest tests/test_models.py -v
```

# 👥 Perfis de Acesso

```text
Perfil	Descrição	Permissões principais
Admin Sistema	Controle total	Gerenciar empresas, usuários, logs e configurações globais
Admin Empresa	Gestão da empresa	Gerenciar usuários, contratos e configurações da empresa
Gestor	Gestão e aprovação	Gerenciar contratos, aprovar e solicitar ajustes
Analista	Análise	Criar, editar e analisar contratos
Assistente	Operacional	Criar e editar contratos
```

# 📈 Observações de Engenharia

Este projeto demonstra:

- Implementação prática de RBAC
- Estruturação de sistema multiempresa
- Organização modular em Flask
- Implementação de fluxo de negócio (além de CRUD)
- Aplicação de boas práticas básicas de segurança
- Uso de métricas e dashboards
- Controle de alterações com rastreabilidade

# 🚧 Próximos Passos (Possíveis decisões)

- API REST completa
- Testes de integração
- Cache com Redis
- WebSockets para notificações em tempo real

# 🤝 Contribuição

Contribuições são bem-vindas:

```bash
git checkout -b feature/minha-feature
git commit -m "feat: minha feature"
git push origin feature/minha-feature
```
Abra um Pull Request 🚀

# 📄 Licença

- MIT License

# 📫 Contato
LinkedIn: https://www.linkedin.com/in/moisés-aniceto-71042a251

# ⚠️ Observação

Projeto em desenvolvimento contínuo, utilizado como base prática para aprofundamento em backend, arquitetura de sistemas e implementação de regras de negócio.

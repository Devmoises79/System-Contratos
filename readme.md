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
- **Efeitos sonoros**
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

### Regras de negócio 🧠

## 👥 Ações por Perfil em Cada Etapa

### 📝 Rascunho
- **Assistente**
  - Criar contrato
  - Editar contrato

- **Analista**
  - Criar contrato
  - Editar contrato

- **Gestor / Admin Empresa**
  - Visualizar
  - Solicitar ajustes (com justificativa)

---

### 🔍 Em Análise
- **Analista**
  - Revisar contrato
  - Editar dados
  - Aprovar para próxima etapa (enviar para gestor)
  - Devolver para revisão (com justificativa)

- **Assistente**
  - Visualizar
  - Ajustar contrato quando devolvido

- **Gestor / Admin Empresa**
  - Acompanhar andamento

---

### ⏳ Aguardando Aprovação
- **Gestor**
  - Aprovar contrato
  - Solicitar alterações (com justificativa)

- **Admin Empresa**
  - Aprovar contrato
  - Solicitar alterações (com justificativa)

- **Analista**
  - Acompanhar status
  - Realizar ajustes quando devolvido

---

### ✅ Ativo
- **Todos os perfis autorizados**
  - Visualizar contrato
  - Baixar PDF

- **Gestor / Admin**
  - Monitorar contratos ativos

---

## 🔁 Regras Gerais do Fluxo

- Transições entre estados seguem regras de permissão (RBAC)
- Qualquer devolução exige **justificativa obrigatória**
- O sistema registra automaticamente:
  - usuário responsável
  - data e horário
  - motivo da ação
- Contratos podem retornar para revisão a partir de qualquer etapa intermediária

---

## 🎯 Objetivo do Fluxo

- Garantir controle do ciclo de vida do contrato
- Separar responsabilidades por perfil
- Permitir rastreabilidade completa das alterações
- Reduzir inconsistências no processo de aprovação

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

## 🏗️ Decisões Técnicas

Esta seção descreve as principais escolhas feitas durante o desenvolvimento do sistema e seus objetivos.

---

### 🔹 Uso do Flask

O Flask foi escolhido por ser um framework leve e flexível, permitindo maior controle sobre a estrutura da aplicação.

**Motivo:**
- Facilidade para entender o ciclo completo da aplicação
- Menor abstração, favorecendo aprendizado de arquitetura
- Adequado para projetos modulares de pequeno a médio porte

---

### 🔹 Arquitetura Modular

O projeto foi organizado em módulos (`auth`, `models`, `core`, `admin`), separando responsabilidades.

**Motivo:**
- Melhor organização do código
- Facilidade de manutenção
- Separação entre regras de negócio, autenticação e acesso a dados

---

### 🔹 Uso de MySQL

Banco relacional utilizado para persistência dos dados.

**Motivo:**
- Estrutura consistente para dados relacionais (contratos, usuários, empresas)
- Suporte a integridade referencial
- Facilidade de consultas para relatórios e métricas

---

### 🔹 Implementação de RBAC

Controle de acesso baseado em perfis (Admin, Gestor, Analista, Assistente).

**Motivo:**
- Separar responsabilidades no fluxo de contratos
- Evitar acesso indevido a funcionalidades
- Simular cenários reais de sistemas corporativos

---

### 🔹 Workflow de Contratos

Implementação de estados (rascunho, análise, aprovação, ativo) com transições controladas.

**Motivo:**
- Representar o ciclo de vida real de contratos
- Garantir controle sobre alterações
- Evitar inconsistências no processo

---

### 🔹 Auditoria de Alterações

Registro de ações com usuário, data, horário e justificativa.

**Motivo:**
- Garantir rastreabilidade
- Aumentar transparência nas mudanças
- Simular requisitos comuns em sistemas corporativos

---

### 🔹 Geração de PDF

Uso de bibliotecas como ReportLab/WeasyPrint para exportação de contratos.

**Motivo:**
- Permitir documentação formal dos contratos
- Simular funcionalidade comum em sistemas empresariais

---

### 🔹 Segurança Básica

Implementação de proteção contra CSRF, hash de senha e bloqueio de IP.

**Motivo:**
- Evitar vulnerabilidades comuns
- Introduzir boas práticas de segurança
- Proteger autenticação e dados sensíveis

---

### 🔹 Sistema de Notificações

Notificações internas para eventos do sistema (criação, análise, aprovação).

**Motivo:**
- Melhorar comunicação entre usuários
- Acompanhar ações no fluxo de contratos

---

### 🔹 Efeitos Sonoros

Implementação de feedback sonoro para ações do sistema (ex: sucesso, erro, notificações).

**Motivo:**
- Melhorar a experiência do usuário (UX)
- Fornecer feedback imediato para ações importantes
- Tornar a interação com o sistema mais intuitiva

--- 

### 🔹 Gamificação

Sistema de pontos e ranking baseado em ações do usuário.

**Motivo:**
- Incentivar uso do sistema
- Explorar funcionalidades adicionais de engajamento

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

## 👥 Perfis de Acesso

| Perfil         | Descrição            | Permissões principais                                              |
|---------------|--------------------|--------------------------------------------------------------------|
| Admin Sistema | Controle total     | Gerenciar empresas, usuários, logs e configurações globais        |
| Admin Empresa | Gestão da empresa  | Gerenciar usuários, contratos e configurações da empresa          |
| Gestor        | Gestão e aprovação | Gerenciar contratos, aprovar e solicitar ajustes                  |
| Analista      | Análise            | Criar, editar e analisar contratos                               |
| Assistente    | Operacional        | Criar e editar contratos                                         |

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
- LinkedIn: https://www.linkedin.com/in/moisés-aniceto-71042a251

# ⚠️ Observação

Projeto em desenvolvimento contínuo, utilizado como base prática para aprofundamento em backend, arquitetura de sistemas e implementação de regras de negócio.

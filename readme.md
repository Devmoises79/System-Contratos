## 📄 System-Contratos

Sistema web para gerenciamento corporativo de contratos, empresas e usuários.

* ⚠️ Status: Projeto em desenvolvimento ativo. Estrutura arquitetural consolidada e novas funcionalidades sendo implementadas.


# 📌 Sobre o Projeto

O System-Contratos é uma aplicação web desenvolvida com foco em organização modular, controle de acesso e boas práticas de backend.

O sistema permite:

- Gestão de contratos

- Administração de empresas

- Controle de usuários

- Permissões baseadas em perfil (RBAC)

- Estrutura organizada por domínio

- Tratamento de erros personalizados

*O projeto está em evolução contínua, com foco em escalabilidade e arquitetura limpa.

# Stack Tecnológica

*Backend:

- Python

- Flask

- Arquitetura modular

- Integração com APIs REST

- ORM para abstração do banco de dados

*Frontend:

- HTML5

- CSS3

- JavaScript

- Bootstrap

*Banco de Dados:

- MySQL

# 🏗️ Estrutura Atual do Projeto

```bash
System-Contratos/
│
├── admin/
├── auth/
├── core/
├── models/
├── static/
│   └── css/
├── templates/
│   ├── admin/
│   ├── auth/
│   ├── contratos/
│   ├── dashboard/
│   ├── empresa/
│   ├── erros/
│   ├── base.html
│   └── login.html
│
├── app.py
├── config.py
├── contrato.py
├── teste_conexao.py
├── .gitignore
└── readme.md
```

* A organização segue separação de responsabilidades, facilitando manutenção, evolução e escalabilidade.

# 🔐 Controle de Acesso e Perfis

O sistema implementa controle de acesso baseado em papéis (RBAC), com quatro níveis administrativos distintos:

# 🔹 Administrador do Sistema

- Gerencia o sistema globalmente

- Controle estrutural da aplicação

- Administração geral de empresas

# 🔹 Administrador da Empresa

- Gerencia usuários da própria empresa

- Administra contratos internos

- Acessa dashboards e estatísticas específicas

# 🔹 Demais Perfis

- Gestor

- Analista

- Assistente

- Cada perfil possui permissões e visualizações específicas.


# 🛡️ Recursos de Segurança

- Autenticação de usuários

- Controle granular de permissões

- Bloqueio de IP

- Páginas de erro personalizadas (403, 404, 500)

- Separação entre camadas administrativas e autenticação

# Direcionamento Futuro

- Ampliação das APIs REST

- Testes automatizados

- Refatoração arquitetural contínua

- Auditoria e logs estruturados

# 📎 Observação

Este projeto está sendo desenvolvido como prática avançada de backend, modelagem de domínio e controle de acesso em aplicações web corporativas.

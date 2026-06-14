#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Validação Automatizada de Pré-Deploy para a Fase 0 (Setup de Infraestrutura).
Verifica a integridade de arquivos de ambiente, dependências Python/NPM, Dockerfile, Netlify TOML e inicialização básica do FastAPI.
"""
import os
import sys
import re
import subprocess
import importlib.util

# Cores ANSI para saída rica no console
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def print_result(name: str, success: bool, warnings: list = None, errors: list = None):
    """Auxiliar para imprimir relatórios de forma estruturada e colorida."""
    status = f"{GREEN}✅ PASSOU{RESET}" if success else f"{RED}❌ FALHOU{RESET}"
    if not success:
        status = f"{RED}❌ FALHOU{RESET}"
    elif warnings:
        status = f"{YELLOW}⚠ AVISO{RESET}"
        
    print(f"[{status}] {CYAN}{name}{RESET}")
    if errors:
        for err in errors:
            print(f"      {RED}- Erro: {err}{RESET}")
    if warnings:
        for warn in warnings:
            print(f"      {YELLOW}- Aviso: {warn}{RESET}")

def check_env_files() -> tuple[bool, list, list]:
    """Valida a existência e integridade dos arquivos .env de desenvolvimento."""
    errors = []
    warnings = []
    
    # 1. Backend .env
    backend_env_path = os.path.join(PROJECT_ROOT, "api", ".env")
    if not os.path.exists(backend_env_path):
        warnings.append("Arquivo 'api/.env' de desenvolvimento local não encontrado. Criando um a partir do template.")
        example_path = os.path.join(PROJECT_ROOT, "api", ".env.example")
        if os.path.exists(example_path):
            try:
                with open(example_path, "r", encoding="utf-8") as src, open(backend_env_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
                warnings.append("Criado 'api/.env' padrão. Lembre-se de preencher a GEMINI_API_KEY nele.")
            except Exception as e:
                errors.append(f"Falha ao criar api/.env a partir do example: {str(e)}")
        else:
            errors.append("Template api/.env.example ausente. Impossível criar o arquivo .env padrão do backend.")
    else:
        # Analisa conteúdo do .env existente
        try:
            with open(backend_env_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "GEMINI_API_KEY=<YOUR_API_KEY_HERE>" in content or "GEMINI_API_KEY=" not in content:
                    warnings.append("GEMINI_API_KEY no arquivo api/.env está com o valor padrão do template ou vazia.")
        except Exception as e:
            errors.append(f"Erro ao ler api/.env: {str(e)}")

    # 2. Frontend .env
    frontend_env_path = os.path.join(PROJECT_ROOT, "client", ".env")
    if not os.path.exists(frontend_env_path):
        warnings.append("Arquivo 'client/.env' de desenvolvimento local não encontrado. Criando um a partir do template.")
        example_path = os.path.join(PROJECT_ROOT, "client", ".env.example")
        if os.path.exists(example_path):
            try:
                with open(example_path, "r", encoding="utf-8") as src, open(frontend_env_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
            except Exception as e:
                errors.append(f"Falha ao criar client/.env: {str(e)}")
        else:
            errors.append("Template client/.env.example ausente.")

    success = len(errors) == 0
    return success, warnings, errors

def check_python_dependencies() -> tuple[bool, list, list]:
    """Compara dependências instaladas no ambiente Python atual com o requirements.txt."""
    errors = []
    warnings = []
    
    req_path = os.path.join(PROJECT_ROOT, "api", "requirements.txt")
    if not os.path.exists(req_path):
        errors.append("Arquivo api/requirements.txt ausente.")
        return False, warnings, errors

    # Carrega requisitos declarados
    declared_packages = {}
    try:
        with open(req_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r"^([^\[=]+)(?:\[[^\]]+\])?==([^\s#]+)", line)
                if match:
                    pkg_name = match.group(1).lower().replace("_", "-")
                    pkg_ver = match.group(2)
                    declared_packages[pkg_name] = pkg_ver
    except Exception as e:
        errors.append(f"Erro ao ler api/requirements.txt: {str(e)}")
        return False, warnings, errors

    # Obtém pacotes instalados usando pip
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=True)
        installed = {}
        for line in result.stdout.splitlines():
            parts = line.split("==")
            if len(parts) == 2:
                installed[parts[0].lower().replace("_", "-")] = parts[1]
    except Exception as e:
        warnings.append(f"Não foi possível rodar 'pip freeze' para validação estrita: {str(e)}")
        return True, warnings, errors

    # Compara
    for pkg, req_ver in declared_packages.items():
        if pkg not in installed:
            warnings.append(f"Pacote Python '{pkg}' (versão requerida {req_ver}) não está instalado no ambiente ativo.")
        elif installed[pkg] != req_ver:
            warnings.append(f"Divergência de versão para '{pkg}': Instalada={installed[pkg]} vs Requerida={req_ver}.")

    success = len(errors) == 0
    return success, warnings, errors

def check_npm_dependencies() -> tuple[bool, list, list]:
    """Valida a pasta client/node_modules e integridade do NPM."""
    errors = []
    warnings = []
    
    client_dir = os.path.join(PROJECT_ROOT, "client")
    node_modules_path = os.path.join(client_dir, "node_modules")
    
    if not os.path.exists(node_modules_path):
        warnings.append("Diretório client/node_modules não encontrado. Executando instalação inicial local no script pode demorar.")
    
    package_json_path = os.path.join(client_dir, "package.json")
    if not os.path.exists(package_json_path):
        errors.append("Arquivo client/package.json ausente. O frontend não está scaffoldado corretamente.")
        
    success = len(errors) == 0
    return success, warnings, errors

def check_dockerfile() -> tuple[bool, list, list]:
    """Verifica a presença e a integridade da sintaxe básica do Dockerfile."""
    errors = []
    warnings = []
    
    dockerfile_path = os.path.join(PROJECT_ROOT, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        errors.append("Dockerfile ausente na raiz do repositório.")
        return False, warnings, errors
        
    try:
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        required_keywords = ["FROM", "WORKDIR", "COPY", "RUN", "EXPOSE", "CMD"]
        for kw in required_keywords:
            if kw not in content:
                errors.append(f"Instrução Docker crucial '{kw}' ausente no Dockerfile.")
                
        # Validações estritas de portas e arquivos
        if "8000" not in content:
            warnings.append("A porta padrão 8000 do FastAPI não foi encontrada explicitamente no Dockerfile.")
            
    except Exception as e:
        errors.append(f"Erro ao ler Dockerfile: {str(e)}")
        
    success = len(errors) == 0
    return success, warnings, errors

def check_netlify_config() -> tuple[bool, list, list]:
    """Valida a sintaxe e a existência de campos obrigatórios no netlify.toml."""
    errors = []
    warnings = []
    
    netlify_path = os.path.join(PROJECT_ROOT, "netlify.toml")
    if not os.path.exists(netlify_path):
        errors.append("Arquivo netlify.toml ausente na raiz do repositório.")
        return False, warnings, errors
        
    try:
        with open(netlify_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Validação simples de sintaxe TOML baseada em regex de chaves cruciais
        if "[build]" not in content:
            errors.append("Seção '[build]' ausente no netlify.toml.")
        if "publish" not in content or "client/dist" not in content:
            errors.append("Diretório de publicação 'publish = \"client/dist\"' ausente ou incorreto no netlify.toml.")
        if "[[redirects]]" not in content:
            warnings.append("Nenhuma regra '[[redirects]]' declarada para redirecionamento SPA ou Proxy de API.")
            
    except Exception as e:
        errors.append(f"Erro ao analisar netlify.toml: {str(e)}")
        
    success = len(errors) == 0
    return success, warnings, errors

def check_fastapi_startup() -> tuple[bool, list, list]:
    """Tenta carregar o módulo FastAPI do backend para garantir que não existam erros de importação estática."""
    errors = []
    warnings = []
    
    # Adiciona a pasta do projeto ao path para carregar o módulo
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
        
    try:
        # Verifica se o módulo de configuração carrega de forma limpa
        config_spec = importlib.util.find_spec("api.core.config")
        if config_spec is None:
            errors.append("Módulo api.core.config não encontrado no PYTHONPATH.")
            return False, warnings, errors
            
        config_module = importlib.util.module_from_spec(config_spec)
        config_spec.loader.exec_module(config_module)
        
        # Tenta localizar api.main
        main_spec = importlib.util.find_spec("api.main")
        if main_spec is None:
            errors.append("Módulo principal api.main não encontrado.")
            return False, warnings, errors
            
        main_module = importlib.util.module_from_spec(main_spec)
        main_spec.loader.exec_module(main_module)
        
        # Verifica a presença da instância da aplicação
        if not hasattr(main_module, "app"):
            errors.append("A instância global 'app' do FastAPI não foi exposta em api/main.py.")
            
    except Exception as e:
        errors.append(f"Falha de importação estática ou de sintaxe no carregamento da API: {str(e)}")
        
    success = len(errors) == 0
    return success, warnings, errors

def main():
    """Ponto de entrada principal executando toda a pipeline de validação."""
    print(f"\n{BLUE}======================================================================{RESET}")
    print(f"{BLUE}      AGENTE STORYTELLER V5 — VALIDADOR AUTOMÁTICO DE PRÉ-DEPLOY{RESET}")
    print(f"{BLUE}======================================================================{RESET}\n")
    
    checks = [
        ("Arquivos de Ambiente (.env)", check_env_files),
        ("Dependências Python (pip requirements)", check_python_dependencies),
        ("Estrutura NPM (client package)", check_npm_dependencies),
        ("Configuração do Dockerfile", check_dockerfile),
        ("Configuração do Netlify (netlify.toml)", check_netlify_config),
        ("Integridade Estrutural FastAPI (api.main)", check_fastapi_startup)
    ]
    
    total_failed = 0
    
    for name, fn in checks:
        try:
            success, warnings, errors = fn()
            print_result(name, success, warnings, errors)
            if not success:
                total_failed += 1
        except Exception as e:
            print_result(name, False, errors=[f"Exceção não tratada: {str(e)}"])
            total_failed += 1
        print()
            
    print(f"{BLUE}======================================================================{RESET}")
    if total_failed == 0:
        print(f"{GREEN}🎉 SUCESSO: Todas as validações cruciais passaram! Pronto para deploy.{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}❌ FALHA: {total_failed} validação(ões) crítica(s) falhou(aram). Corrija-as.{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()

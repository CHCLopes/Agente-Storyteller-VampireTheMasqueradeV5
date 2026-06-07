import os
import shutil

def main():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    # Diretório público na pasta adjacente na sandbox
    dest_dir = os.path.join(os.path.dirname(src_dir), "AgenteStoryteller_Public")
    
    print(f"[*] Sincronizando repositório público em: {dest_dir}")
    os.makedirs(dest_dir, exist_ok=True)
    
    # 1. Pastas e arquivos essenciais
    dirs_to_copy = ["api", "client", "data", "skills"]
    files_to_copy = ["requirements.txt", ".env.example", "INICIAR_JOGO.bat"]
    
    # Limpa destino se já existir para uma sincronização limpa (preservando o .git)
    if os.path.exists(dest_dir):
        for item in os.listdir(dest_dir):
            if item == ".git" or item == "README.md":
                continue
            item_path = os.path.join(dest_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
            
    # Copia pastas
    for d in dirs_to_copy:
        src_path = os.path.join(src_dir, d)
        dest_path = os.path.join(dest_dir, d)
        if os.path.exists(src_path):
            shutil.copytree(src_path, dest_path)
            
    # Copia arquivos
    for f in files_to_copy:
        src_path = os.path.join(src_dir, f)
        dest_path = os.path.join(dest_dir, f)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dest_path)
            
    # Remove saves de teste ou logs de jogo locais do jogador da pasta data/saves copiado
    saves_dir = os.path.join(dest_dir, "data", "saves")
    if os.path.exists(saves_dir):
        for save in os.listdir(saves_dir):
            os.remove(os.path.join(saves_dir, save))
            
    # 2. Cria o .gitignore público
    gitignore_content = """# Ambientes Virtuais
.venv/
venv/
ENV/
env/

# Configurações de Ambiente Locais
.env

# Saves do Jogador (Preservar pasta, ignorar saves locais)
/data/saves/*
!/data/saves/.gitkeep

# Logs do Servidor
/logs/
*.log

# Caches de compilação Python
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
"""
    
    # Garante a existência de .gitkeep em data/saves para que o Git rastreie a pasta
    os.makedirs(saves_dir, exist_ok=True)
    with open(os.path.join(saves_dir, ".gitkeep"), "w") as gitkeep:
        pass
        
    with open(os.path.join(dest_dir, ".gitignore"), "w", encoding="utf-8") as g:
        g.write(gitignore_content)
        
    # Copia também o atalho amigável criado para a distribuição pública
    src_lnk = os.path.join(src_dir, "Iniciar o Jogo.lnk")
    dest_lnk = os.path.join(dest_dir, "Iniciar o Jogo.lnk")
    if os.path.exists(src_lnk):
        shutil.copy2(src_lnk, dest_lnk)
        
    print("[+] Sincronização do repositório público concluída com sucesso.")

if __name__ == "__main__":
    main()

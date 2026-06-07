# 🦇 A Primeira Noite: Guia de Iniciação ao Agente Storyteller

Bem-vindo às sombras. Este é o seu **Agente Storyteller**, um Narrador de Inteligência Artificial totalmente offline e privado, construído para guiar suas crônicas de *Vampiro: A Máscara (5ª Edição)*.

Antes de rolarmos os dados, precisamos preparar o seu "Refúgio" (o ambiente onde o jogo irá rodar). Leia este guia com atenção para garantir que a sua experiência seja segura, rápida e imersiva.

---

## 🛡️ Promessa de Segurança e Privacidade (Zero-Cloud)

Este projeto foi desenhado com foco absoluto na sua privacidade.
* **100% Offline:** O seu jogo, as suas escolhas e a sua ficha nunca saem do seu computador. Nenhuma informação é enviada para a nuvem.
* **Isolamento (Sandbox):** O Agente opera estritamente dentro da pasta que você definir. Ele não tem acesso aos seus arquivos pessoais, fotos ou documentos do sistema operacional.

---

## 📂 Passo 1: Escolha o seu Refúgio (Instalação)

Você tem duas opções para abrigar o seu Narrador. Escolha a que melhor se adapta à sua caçada:

### Opção A: O Refúgio Portátil (Pendrive USB)
Ideal se você quer jogar em diferentes computadores (no trabalho, na casa de amigos) sem instalar os modelos pesados na máquina hospedeira.
1. Formate um Pendrive com pelo menos **32GB** (recomendado devido ao tamanho dos modelos).
2. Crie uma pasta raiz chamada `VTM_Storyteller`.
3. Extraia os arquivos deste projeto diretamente para dentro dessa pasta.

### Opção B: O Santuário Local (Disco Rígido)
Ideal para computadores pessoais, oferecendo tempos de carregamento ligeiramente mais rápidos.
1. Crie uma pasta isolada no seu computador (Ex: `C:\Jogos\VTM_Storyteller`).
2. **Aviso de Segurança:** Não coloque esta pasta dentro de diretórios críticos do sistema (como `System32` ou `Windows`).
3. Extraia os arquivos deste projeto para a pasta criada.

---

## 🔒 Passo 2: O Despertar do Narrador (Configuração do Motor)

O Agente Storyteller utiliza o **LM Studio** como motor principal. Siga os passos abaixo para garantir o isolamento total (Sandbox):

### 2.1 Instalando o LM Studio
1. Acesse o site oficial: [https://lmstudio.ai/download](https://lmstudio.ai/download)
2. Baixe e instale o programa normalmente no seu Windows, Mac ou Linux. 
3. **Dica de UX:** Você não precisa mover o programa para a pasta do jogo. O Windows gerenciará o executável, mas nós configuraremos ele para ler apenas a nossa pasta de jogo.

### 2.2 Configurando o Sandbox (Vital!)
Por questões de segurança e para que o projeto seja portátil e isolado, precisamos dizer ao LM Studio onde os "cérebros" (modelos) estão:
1. Abra o LM Studio.
2. No menu lateral esquerdo, clique no ícone de **Engrenagem (Settings)**.
3. Procure por **"My Models Directory"** (Caminho dos Modelos).
4. Clique em **"Change"** e aponte para a pasta `\models` que está dentro da sua pasta principal `VTM_Storyteller`. 
   * *Isso garante que gigabytes de dados fiquem no seu pendrive/pasta e não "sujem" o seu computador.*

### 2.3 Baixando as Mentes da IA
No LM Studio, vá na opção de pesquisa (botão **"Model Search"**, o ícone de lupa) e busque pelos modelos abaixo. 
**Regra de Ouro:** Escolha sempre as versões que pesam entre **4GB e 5GB** e que possuam o maior número de downloads/corações.

Busque e baixe:
* 🧠 **Agente Operador (`qwen2.5-1.5b-instruct`):** O Árbitro das regras.
* 👁️ **Agente de Memória (`deepseek-r1-distill-qwen-7b`):** O Arquivista da história.
* 🎭 **Agente Storyteller (`llama-3.2-3b-instruct`):** O Mestre da narrativa.

---

## ⚙️ Passo 3: Iniciando a Sessão

Com o LM Studio configurado e os modelos baixados, é hora de começar:

1. **Abra o LM Studio** e vá na clique no segundo botão da barra lateral esquerda chamado **"Developer"**. Dentro dele procure por **"Local Server"**. Clique nele.
2. Dentro de **"Local Server"**, procure o botão **Server Settings** e clique nele. Um novo menu se abrirá e, no primeiro item, **Server Port** , certifique-se de que o servidor está rodando na porta padrão (1234).
3. Agora, vá na sua pasta `VTM_Storyteller` e dê um duplo clique no arquivo **`INICIAR_JOGO.bat`**.
4. Este script fará a conexão automática entre a interface do jogo e o LM Studio.
5. Aguarde a mensagem no terminal: `[Sistema] Coterie de Agentes Online e Aguardando.`

---

## 🩸 Passo 4: Suas Primeiras Palavras

Abra o seu navegador no endereço fornecido pelo terminal e use um dos comandos:

**Para Nova Campanha:** Digite **"Inicie uma nova crônica."**
**Para Carregar Jogo:** Digite **"Continue minha jornada."**

***Lembre-se: A Besta está sempre faminta. Jogue com sabedoria.***
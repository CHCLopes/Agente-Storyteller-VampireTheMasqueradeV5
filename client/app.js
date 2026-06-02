/* ==========================================================================
   VAMPIRE THE MASQUERADE V5 - MOTOR NARRATIVO - FRONTEND REATIVO (Vanilla JS)
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    const estadoPersonagem = {
        nome: "", geracao: "", fome: 0,
        vida: { size: 0, superficial: 0, aggravated: 0 },
        vontade: { size: 0, superficial: 0, aggravated: 0 },
        xp: 0, atributos: {}, habilidades: {}, disciplinas: {},
        relacionamentos: [
            { id: "xerife", titulo: "Favor devedor ao Xerife de Câmera", desc: "Você deve um favor menor a ele por ocultar uma quebra de Máscara no cais." },
            { id: "primogenito", titulo: "Aliança de Sangue com Primogênito Brujah", desc: "Apoiando sua causa em troca de futura lealdade na corte local." },
            { id: "principe", titulo: "Vigilância Constante do Príncipe Villon", desc: "Olhar vigilante constante sobre suas atividades no centro da cidade." }
        ]
    };

    const nomesAtributos = {
        Strength: "Força", Dexterity: "Destreza", Stamina: "Vigor",
        Charisma: "Carisma", Manipulation: "Manipulação", Composure: "Autocontrole",
        Intelligence: "Inteligência", Wits: "Raciocínio", Resolve: "Determinação"
    };

    const nomesHabilidades = {
        Athletics: "Atletismo", Brawl: "Briga", Craft: "Ofício", Drive: "Condução",
        Firearms: "Armas de Fogo", Larceny: "Ladrão", Melee: "Armas Brancas",
        Stealth: "Furtividade", Survival: "Sobrevivência", AnimalKen: "Trato com Animais",
        Etiquette: "Etiqueta", Insight: "Intuição", Intimidation: "Intimidação",
        Leadership: "Liderança", Performance: "Performance", Persuasion: "Persuasão",
        Streetwise: "Manha", Subterfuge: "Subterfúgio", Academics: "Acadêmicos",
        Awareness: "Percepção", Finance: "Finanças", Investigation: "Investigação",
        Medicine: "Medicina", Occult: "Ocultismo", Politics: "Política",
        Science: "Ciência", Technology: "Tecnologia"
    };

    const nomesDisciplinas = {
        animalism: "Animalismo", auspex: "Auspício", celerity: "Rapidez",
        dominate: "Dominar", fortitude: "Fortitude", obfuscate: "Ofuscação",
        potence: "Potência", presence: "Presença", protean: "Metamorfose",
        blood_sorcery: "Feitiçaria de Sangue", feral_weapons: "Armas Ferais",
        scorpion_touch: "Toque do Escorpião", awe: "Fascínio"
    };

    const renderizadores = {
        fome: (valor) => {
            const container = document.getElementById("hud-hunger");
            if (!container) return;
            container.innerHTML = "";
            for (let i = 0; i < 5; i++) {
                const pip = document.createElement("span");
                pip.className = i < valor ? "pip-hunger-active" : "pip-hunger-empty";
                pip.setAttribute("aria-label", i < valor ? "Fome ativa" : "Fome vazia");
                container.appendChild(pip);
            }
        },
        vida: (tracker) => {
            const container = document.getElementById("hud-health");
            if (!container) return;
            container.innerHTML = "";
            const total = tracker.size || 0;
            const superficial = tracker.superficial || 0;
            const agravado = tracker.aggravated || 0;
            for (let i = 0; i < total; i++) {
                const pip = document.createElement("span");
                if (i < agravado) {
                    pip.className = "pip-quadrado-agravado";
                    pip.setAttribute("aria-label", "Dano agravado");
                } else if (i < agravado + superficial) {
                    pip.className = "pip-quadrado-superficial";
                    pip.setAttribute("aria-label", "Dano superficial");
                } else {
                    pip.className = "pip-quadrado-vazio";
                    pip.setAttribute("aria-label", "Vida intacta");
                }
                container.appendChild(pip);
            }
        },
        vontade: (tracker) => {
            const container = document.getElementById("hud-willpower");
            if (!container) return;
            container.innerHTML = "";
            const total = tracker.size || 0;
            const superficial = tracker.superficial || 0;
            const agravado = tracker.aggravated || 0;
            for (let i = 0; i < total; i++) {
                const pip = document.createElement("span");
                if (i < agravado) {
                    pip.className = "pip-quadrado-agravado";
                    pip.setAttribute("aria-label", "Fadiga agravada");
                } else if (i < agravado + superficial) {
                    pip.className = "pip-quadrado-superficial";
                    pip.setAttribute("aria-label", "Fadiga superficial");
                } else {
                    pip.className = "pip-quadrado-vazio";
                    pip.setAttribute("aria-label", "Vontade intacta");
                }
                container.appendChild(pip);
            }
        },
        xp: (valor) => {
            const elem = document.getElementById("hud-xp-avb");
            if (elem) elem.textContent = `${valor} XP`;
        },
        atributos: (dict) => {
            const container = document.getElementById("hud-attributes");
            if (!container) return;
            container.innerHTML = "";
            Object.entries(dict).forEach(([chave, valor]) => {
                const traduzido = nomesAtributos[chave] || chave;
                const wrapper = document.createElement("div");
                wrapper.className = "flex justify-between items-center bg-zinc-900/40 p-1.5 border border-zinc-900 rounded";
                wrapper.innerHTML = `<span class="text-zinc-400">${traduzido}</span><span class="text-v5-parchment font-bold" aria-label="Nível de ${traduzido}: ${valor}">${valor}</span>`;
                container.appendChild(wrapper);
            });
        },
        habilidades: (dict) => {
            const select = document.getElementById("hud-skills-select");
            if (!select) return;
            select.innerHTML = `<option value="" disabled selected hidden>Usar Habilidade...</option>`;
            Object.entries(dict).forEach(([chave, valor]) => {
                const traduzido = nomesHabilidades[chave] || chave;
                const option = document.createElement("option");
                option.value = `Fazer teste de ${traduzido}`;
                option.textContent = `${traduzido} (Nível ${valor})`;
                select.appendChild(option);
            });
        },
        disciplinas: (dict) => {
            const select = document.getElementById("hud-disciplines-select");
            if (!select) return;
            select.innerHTML = `<option value="" disabled selected hidden>Ativar Disciplina de Sangue...</option>`;
            Object.entries(dict).forEach(([chave, valor]) => {
                const traduzido = nomesDisciplinas[chave] || chave.replace(/_/g, " ");
                const estadoAtivacao = typeof valor === "boolean" ? (valor ? "Ativa" : "Inativa") : (valor > 0 ? `Nível ${valor}` : "Inativa");
                const option = document.createElement("option");
                option.value = `Ativar disciplina ${traduzido}`;
                option.textContent = `${traduzido}: ${estadoAtivacao}`;
                select.appendChild(option);
            });
        },
        relacionamentos: (lista) => {
            const select = document.getElementById("hud-relations-select");
            if (!select) return;
            select.innerHTML = `<option value="" disabled selected hidden>Consultar Relacionamento...</option>`;
            lista.forEach((item) => {
                const option = document.createElement("option");
                option.value = item.id;
                option.textContent = item.titulo;
                select.appendChild(option);
            });
            select.onchange = () => {
                const selecionado = lista.find(item => item.id === select.value);
                if (selecionado) {
                    abrirModal(selecionado.titulo, `<p class='leading-relaxed'>${selecionado.desc}</p>`);
                    enviarMensagem(`Consultando relacionamento com ${selecionado.titulo.split(':')[0]}`);
                    select.selectedIndex = 0;
                }
            };
        },
        cabecalho: (nome, clan) => {
            const elemNome = document.getElementById("hud-character-name");
            const elemClan = document.getElementById("hud-clan-name");
            if (elemNome) elemNome.textContent = nome;
            if (elemClan) elemClan.textContent = `${clan}`;
        }
    };

    const stateHandler = {
        set(target, property, value) {
            target[property] = value;
            if (property === "fome") renderizadores.fome(value);
            else if (property === "vida") renderizadores.vida(value);
            else if (property === "vontade") renderizadores.vontade(value);
            else if (property === "xp") renderizadores.xp(value);
            else if (property === "atributos") renderizadores.atributos(value);
            else if (property === "habilidades") renderizadores.habilidades(value);
            else if (property === "disciplinas") renderizadores.disciplinas(value);
            else if (property === "relacionamentos") renderizadores.relacionamentos(value);
            else if (property === "nome" || property === "cla") renderizadores.cabecalho(target.nome, target.cla);
            return true;
        }
    };

    const proxyEstado = new Proxy(estadoPersonagem, stateHandler);

    renderizadores.fome(proxyEstado.fome);
    renderizadores.vida(proxyEstado.vida);
    renderizadores.vontade(proxyEstado.vontade);
    renderizadores.xp(proxyEstado.xp);
    renderizadores.atributos(proxyEstado.atributos);
    renderizadores.habilidades(proxyEstado.habilidades);
    renderizadores.disciplinas(proxyEstado.disciplinas);
    renderizadores.relacionamentos(proxyEstado.relacionamentos);
    renderizadores.cabecalho(proxyEstado.nome, proxyEstado.geracao);

    // ----------------------------------------------------------------------
    // 2. CONEXÃO WEBSOCKET REATIVA
    // ----------------------------------------------------------------------
    let ws = null;
    const logContainer = document.getElementById("narrative-log");
    const connIndicator = document.getElementById("conn-indicator");
    const connText = document.getElementById("conn-text");
    const sessionDisplay = document.getElementById("session-display");
    const sessionContext = document.getElementById("session-context");

    const sessionPath = window.location.pathname.split("/").pop();
    const sessionId = (sessionPath && sessionPath.length > 2) ? sessionPath : "local_player";
    if (sessionDisplay) sessionDisplay.textContent = `SESSÃO: ${sessionId}`;

    let activeStreamContainer = null;

    function conectarWebSocket() {
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsHost = window.location.host || "localhost:8000";
        ws = new WebSocket(`${wsProtocol}//${wsHost}/ws/session/${sessionId}`);

        ws.onopen = () => {
            if (connIndicator) connIndicator.className = "w-2.5 h-2.5 rounded-full bg-emerald-600 animate-pulse shrink-0";
            if (connText) connText.textContent = "CONECTADO";
            if (sessionContext) sessionContext.textContent = "Refúgio ativo. Mestre narrativo aguardando ação.";
        };

        ws.onclose = () => {
            if (connIndicator) connIndicator.className = "w-2.5 h-2.5 rounded-full bg-red-700 shrink-0";
            if (connText) connText.textContent = "DESCONECTADO";
            if (sessionContext) sessionContext.textContent = "Conexão perdida. Tentando reconectar...";
            setTimeout(conectarWebSocket, 3000);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                switch (data.action) {
                    case "chat_response":
                        adicionarMensagemLog(data.message, "narrador");
                        break;
                    case "state_update":
                        if (data.player_sheet) {
                            const sheet = data.player_sheet;
                            if (sheet.clan) proxyEstado.cla = `Clã ${sheet.clan.toUpperCase()}`;
                            if (sheet.status) {
                                if (typeof sheet.status.current_hunger === "number") proxyEstado.fome = sheet.status.current_hunger;
                                if (sheet.status.health_tracker) proxyEstado.vida = sheet.status.health_tracker;
                                if (sheet.status.willpower_tracker) proxyEstado.vontade = sheet.status.willpower_tracker;
                            }
                            if (typeof sheet.available_xp === "number") proxyEstado.xp = sheet.available_xp;
                            if (sheet.attributes) proxyEstado.atributos = sheet.attributes;
                            if (sheet.skills) proxyEstado.habilidades = sheet.skills;
                            if (sheet.disciplines) proxyEstado.disciplinas = sheet.disciplines;
                        }
                        break;
                    case "stream_start":
                        activeStreamContainer = document.createElement("div");
                        activeStreamContainer.className = "font-sans text-lg text-stone-300 leading-relaxed border-l-2 border-red-900 pl-4 py-1 select-text opacity-0 transition-opacity duration-300";
                        logContainer.appendChild(activeStreamContainer);
                        setTimeout(() => activeStreamContainer.classList.remove("opacity-0"), 50);
                        break;
                    case "stream_chunk":
                        if (activeStreamContainer && data.chunk) {
                            activeStreamContainer.textContent += data.chunk;
                            logContainer.scrollTop = logContainer.scrollHeight;
                        }
                        break;
                    case "stream_end":
                        activeStreamContainer = null;
                        logContainer.scrollTop = logContainer.scrollHeight;
                        break;
                    case "error":
                        adicionarMensagemLog(`[Erro do Sistema] ${data.message}`, "sistema-erro");
                        break;
                }
            } catch (err) {
                adicionarMensagemLog(event.data, "narrador");
            }
        };
    }

    conectarWebSocket();

    function adicionarMensagemLog(texto, remetente) {
        const bloco = document.createElement("div");
        if (remetente === "narrador") {
            bloco.className = "font-sans text-lg text-stone-300 leading-relaxed border-l-2 border-red-950 pl-4 py-1 select-text";
        } else if (remetente === "sistema-erro") {
            bloco.className = "font-mono text-xs text-red-500 bg-red-950/20 border border-red-900/40 p-3 rounded";
        } else {
            bloco.className = "font-sans text-sm text-stone-400 bg-zinc-900/30 border border-zinc-900 p-3 rounded select-text text-right ml-auto max-w-xl";
        }
        bloco.textContent = texto;
        logContainer.appendChild(bloco);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    // ----------------------------------------------------------------------
    // 3. INTERAÇÕES DE ELEMENTOS DE PROMPT & FORMULÁRIOS
    // ----------------------------------------------------------------------
    const inputForm = document.getElementById("input-form");
    const userInput = document.getElementById("user-input");
    const inputContainer = document.getElementById("action-panel-container");
    const btnSendTrigger = document.getElementById("btn-send-trigger");
    const macroSelect = document.getElementById("macro-select");

    function enviarMensagem(mensagem) {
        if (!mensagem || !ws || ws.readyState !== WebSocket.OPEN) return;
        if (inputContainer) {
            inputContainer.classList.remove("flash-sending");
            void inputContainer.offsetWidth;
            inputContainer.classList.add("flash-sending");
            setTimeout(() => inputContainer.classList.remove("flash-sending"), 500);
        }
        adicionarMensagemLog(mensagem, "jogador");
        ws.send(mensagem);
        if (userInput) {
            userInput.value = "";
            userInput.focus();
        }
    }

    if (inputForm) {
        inputForm.addEventListener("submit", (e) => {
            e.preventDefault();
            if (userInput) enviarMensagem(userInput.value.trim());
        });
    }

    if (btnSendTrigger) {
        btnSendTrigger.addEventListener("click", () => {
            if (userInput) enviarMensagem(userInput.value.trim());
        });
    }

    if (userInput) {
        userInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                enviarMensagem(userInput.value.trim());
            }
        });
    }

    function configurarAutoSubmissao(select) {
        if (!select) return;
        select.addEventListener("change", () => {
            const valor = select.value;
            if (valor) {
                const textoAcao = select.options[select.selectedIndex].text;
                // Envia a ação para o WebSocket baseada na seleção
                enviarMensagem(valor);
                // Reseta imediatamente o dropdown de volta para o placeholder nativo
                select.selectedIndex = 0;
            }
        });
    }

    configurarAutoSubmissao(macroSelect);
    configurarAutoSubmissao(document.getElementById("hud-skills-select"));
    configurarAutoSubmissao(document.getElementById("hud-disciplines-select"));

    // ----------------------------------------------------------------------
    // 4. CONTROLE DE TOGGLE DA FICHA MOBILE
    // ----------------------------------------------------------------------
    const hudContainer = document.getElementById("hud-container");
    const btnToggleSheet = document.getElementById("btn-toggle-sheet");
    const btnCloseSheet = document.getElementById("btn-close-sheet");
    const sheetOverlay = document.getElementById("sheet-overlay");

    const btnNavAbout = document.getElementById("btn-nav-about");
    const btnNavHelp = document.getElementById("btn-nav-help");
    const btnNavSheet = document.getElementById("btn-nav-sheet");

    function abrirFichaMobile() {
        if (hudContainer) {
            hudContainer.classList.remove("translate-y-full");
            hudContainer.classList.add("translate-y-0");
        }
        if (sheetOverlay) sheetOverlay.classList.remove("hidden");
    }

    function fecharFichaMobile() {
        if (hudContainer) {
            hudContainer.classList.remove("translate-y-0");
            hudContainer.classList.add("translate-y-full");
        }
        if (sheetOverlay) sheetOverlay.classList.add("hidden");
    }

    if (btnToggleSheet) btnToggleSheet.addEventListener("click", abrirFichaMobile);
    if (btnNavSheet) btnNavSheet.addEventListener("click", abrirFichaMobile);
    if (btnCloseSheet) btnCloseSheet.addEventListener("click", fecharFichaMobile);
    if (sheetOverlay) sheetOverlay.addEventListener("click", fecharFichaMobile);

    // ----------------------------------------------------------------------
    // 5. MODAIS
    // ----------------------------------------------------------------------
    const modalContainer = document.getElementById("modal-container");
    const modalTitle = document.getElementById("modal-title");
    const modalBody = document.getElementById("modal-body");
    const btnCloseModal = document.getElementById("btn-close-modal");
    const btnAbout = document.getElementById("btn-about");
    const btnHelp = document.getElementById("btn-help");

    function abrirModal(titulo, conteudoHtml) {
        if (!modalContainer || !modalTitle || !modalBody) return;
        modalTitle.textContent = titulo;
        modalBody.innerHTML = conteudoHtml;
        modalContainer.classList.remove("hidden");
    }

    function fecharModal() {
        if (modalContainer) modalContainer.classList.add("hidden");
    }

    const sobreConteudo = `
        <p>Este sistema é um motor de orquestração local de Inteligência Artificial desenhado sob rigorosas práticas da <strong>Mentoria Vibe Coding</strong>.</p>
        <p>O backend opera em <strong>FastAPI</strong> com suporte reativo a <strong>WebSockets</strong> nativos para streaming síncrono e assíncrono das crônicas.</p>
        <p>A persistência é garantida atonicamente sob <code>asyncio.Lock()</code> com I/O em arquivos do PlayerSheet.</p>
    `;

    const ajudaConteudo = `
        <p><strong>Comandos Principais:</strong></p>
        <ul class="list-disc pl-5 space-y-1">
            <li>Digite <em>"Inicie uma nova crônica."</em> para começar uma jornada das sombras.</li>
            <li>Digite as ações do seu Neófito livremente na caixa de diálogo central ou no <strong>Textarea de entrada</strong> de 4 linhas. Pressione <em>Enter</em> para enviar.</li>
            <li>Utilize os <strong>Dropdowns da Ficha</strong> para ativar disciplinas ou usar habilidades de forma instantânea com auto-submissão reativa.</li>
        </ul>
    `;

    if (btnAbout) btnAbout.addEventListener("click", () => abrirModal("Sobre o Motor Narrativo V5", sobreConteudo));
    if (btnNavAbout) btnNavAbout.addEventListener("click", () => abrirModal("Sobre o Motor Narrativo V5", sobreConteudo));
    if (btnHelp) btnHelp.addEventListener("click", () => abrirModal("Guia de Operação da Crônica", ajudaConteudo));
    if (btnNavHelp) btnNavHelp.addEventListener("click", () => abrirModal("Guia de Operação da Crônica", ajudaConteudo));
    if (btnCloseModal) btnCloseModal.addEventListener("click", fecharModal);
    if (modalContainer) modalContainer.addEventListener("click", (e) => {
        if (e.target === modalContainer) fecharModal();
    });
});

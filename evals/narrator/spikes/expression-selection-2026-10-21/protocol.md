# Estudo prospectivo A2 — seleção de expressão, 21/10/2026

Autorização: continuar o estudo; investigar possível adaptação ao original
agnóstico com foco em modelos gratuitos/leves/locais. Não é autorização para
migrar produto, substituir A1, escolher modelo ou alterar defaults.

Timebox: esta sessão, somente estudo e prova offline. Zero chamadas de inferência,
zero instalação/download/modelos/servidores. Nenhum L86. Rede não usada pela prova.

Hipótese: se cada saída de um modelo contém apenas IDs elegíveis no turno e a
aplicação controla todo o texto, saídas arbitrárias não conseguem inserir prosa
nova. A equivalência semântica dos textos autorados continua obrigação editorial;
hash/schema não a demonstram. A amostra é a matriz L85 congelada (17 planos),
não campanhas gerais nem teste de capacidade de modelos pequenos.

Protótipo isolado: consequência e pergunta retidas; duas falas essenciais
curadas por regra, duas atmosferas (vazia ou posição já conhecida), duas formas
de parágrafo. Até oito combinações por plano. IDs de escolha não controlam
resultados, fatos, RNG, movimento ou memória. Contexto/binding ficam na aplicação;
modelo não ecoa hash longo. Sem reparo, retry ou fallback silencioso.

Critérios: enumerar todas as escolhas; checar consequência/pergunta/referências,
autoria e ausência de texto da resposta no render. Rejeitar conteúdo extra,
JSON inválido, IDs ausentes ou inelegíveis, tipos errados, operação/revisão/
plano/catálogo trocados. Demonstrar deliberadamente que um texto falso introduzido
pelo autor confiável pode passar: contraprova da alegação de verdade geral.
Comparar saída determinística com as mesmas opções; não supor ganho da LLM.

Verificar também transporte simulado no adaptador comum native/emulated,
sem alegar teste de LM Studio/Ollama/llama.cpp ou de qualquer modelo real.
Separar redução de bytes de redução de tokens/latência/VRAM, não medidas aqui.
Registrar resultados, limitações, caminho de portabilidade e decisões ainda abertas.

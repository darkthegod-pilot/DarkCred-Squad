```
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ████████╗  ██╗  ██╗  ███████╗  ██████╗  ██████╗  ███████╗ ██╗  ║
║   ██╔═══██║  ██║  ██║  ██╔════╝  ██╔══██╗ ██╔══██╗ ██╔════╝ ██║  ║
║   ██║   ██║  ███████║  ███████╗  ██║  ██║ ██████╔╝ █████╗   ██║  ║
║   ██║   ██║  ██╔══██║  ╚════██║  ██║  ██║ ██╔══██╗ ██╔══╝   ██║  ║
║   ████████║  ██║  ██║  ███████║  ██████╔╝ ██║  ██║ ███████╗ ██║  ║
║   ╚═══════╝  ╚═╝  ╚═╝  ╚══════╝  ╚═════╝  ╚═╝  ╚═╝ ╚══════╝ ╚═╝  ║
║                                                                   ║
║              A L I N A   P R E T R O V  v2.0                    ║
║        Especialista em Criativos para Instagram · DarkCred       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Claude](https://img.shields.io/badge/Powered%20by-Claude%20AI-orange?logo=anthropic)](https://anthropic.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Segmentos](https://img.shields.io/badge/Segmentos-35%2B-purple)](alina/config.py)
[![Skills](https://img.shields.io/badge/Skills%20Claude-6-red)](.claude/skills/)

**Sistema de geração, análise e otimização de criativos para Instagram.**
**Capital de giro para comerciantes brasileiros — compliance integrado.**

</div>

---

## O que é a Alina?

**Alina Pretrov** é uma agente especialista em marketing de performance para o produto DarkCred — capital de giro para pequenos comerciantes com renda diária no Brasil.

Ela gera copies de alta conversão, analisa resultados de campanha em fotos, aprende com cada ciclo e fica progressivamente melhor. Tudo com compliance automático contra regulações de crédito.

---

## Funcionalidades

| Modo | Comando | O que faz |
|------|---------|-----------|
| ✍️ **Geração** | `python main.py` | Gera copies compliant para qualquer segmento |
| 📸 **Análise de Imagem** | `python main.py --analisar foto.jpg` | Extrai métricas de screenshot via Claude Vision |
| 💬 **Chat Interativo** | `python main.py --chat` | Conversa direta com Alina sobre campanhas |
| 📚 **Aprendizado** | `python main.py --aprendizado` | Exibe o que o sistema aprendeu até agora |
| 📋 **Listar Segmentos** | `python main.py --listar-segmentos` | Lista todos os 35+ segmentos disponíveis |

---

## Setup Rápido

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar API key
cp .env.example .env
# Edite .env e adicione sua ANTHROPIC_API_KEY

# 3. Gerar seus primeiros copies
python main.py
```

---

## Uso Completo

### Geração de Copies

```bash
# 5 copies genéricos (funciona para qualquer comerciante)
python main.py

# 8 copies para padaria
python main.py --segmento padaria --quantidade 8

# 3 copies para todos os 35 segmentos
python main.py --segmento todos --quantidade 3

# Salvar apenas em JSON
python main.py --formato json

# Usar modelo específico
python main.py --modelo claude-opus-4-6
```

### Análise de Resultado de Campanha

```bash
# Manda a foto do resultado e Alina analisa tudo automaticamente
python main.py --analisar screenshot_instagram.jpg

# Funciona com JPG, PNG, WEBP, GIF
python main.py --analisar relatorio_meta_ads.png
```

**O que Alina extrai da imagem:**
- Impressões, Alcance, Frequência
- CTR, CPM, Custo por Mensagem
- Diagnóstico classificado por benchmarks DarkCred
- Projeção de funil: mensagens → fechamentos
- Plano de ação imediato (3 passos)
- Sugestão de próximo copy se necessário

### Chat Interativo

```bash
python main.py --chat
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👋 Oi! Aqui é a Alina Pretrov.
Especialista em criativos DarkCred para Instagram.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Você: meu custo por mensagem tá em R$3,80, o que faço?
Alina: Tá no vermelho — R$3,80 passa dos R$3,50 aceitáveis...

Você: analisa resultado.jpg
[Alina analisa a imagem e exibe diagnóstico completo]

Você: gera 3 copies pra padaria
[Alina gera copies otimizados com contexto do aprendizado]
```

### Agendamento Automático (12h, 15h, 18h30)

```bash
# Configurar cron para envios automáticos
crontab -e

# Adicionar estas linhas:
0 12 * * * cd /home/user/DarkCred-Squad && python scripts/agendador.py --agora --horario 12h >> logs/cron.log 2>&1
0 15 * * * cd /home/user/DarkCred-Squad && python scripts/agendador.py --agora --horario 15h >> logs/cron.log 2>&1
30 18 * * * cd /home/user/DarkCred-Squad && python scripts/agendador.py --agora --horario 18h30 >> logs/cron.log 2>&1
```

Quando você abrir o Claude Code após os horários agendados, os criativos do dia aparecem automaticamente no chat.

---

## Segmentos Disponíveis (35+)

### 🌐 Geral
| Segmento | Público |
|----------|---------|
| `generico` | Qualquer comerciante/empreendedor (maior escala) |

### 🍽️ Alimentação & Bebidas
| Segmento | Público |
|----------|---------|
| `padaria` | Padaria / Confeitaria |
| `pizzaria` | Pizzaria |
| `lanchonete` | Lanchonete / Snack Bar |
| `restaurante` | Restaurante / Marmitaria |
| `acai` | Açaí / Sorveteria |
| `food_truck` | Food Truck / Trailer |
| `pastelaria` | Pastelaria / Esfiha |
| `bar` | Bar / Boteco |

### 💅 Beleza & Cuidado Pessoal
| Segmento | Público |
|----------|---------|
| `salao` | Salão de Beleza |
| `barbearia` | Barbearia |
| `manicure` | Manicure / Studio de Unhas |
| `estetica` | Estética / Spa |
| `academia` | Academia / Studio Fitness |

### 🛍️ Varejo & Comércio
| Segmento | Público |
|----------|---------|
| `vestuario` | Loja de Roupa |
| `calcados` | Loja de Calçados |
| `eletronicos` | Loja de Eletrônicos |
| `variedades` | Bazar / Variedades |
| `mercadinho` | Mercadinho / Mercearia |
| `farmacia` | Farmácia |
| `florista` | Florista |

### 🔧 Serviços
| Segmento | Público |
|----------|---------|
| `encanador` | Encanador |
| `eletricista` | Eletricista |
| `mecanico` | Mecânico / Oficina |
| `chaveiro` | Chaveiro |
| `lavanderia` | Lavanderia |
| `grafica` | Gráfica / Impressão |
| `borracharia` | Borracharia / Pneus |
| `sapateiro` | Sapateiro |

### 🏪 Ambulantes & Mobilidade
| Segmento | Público |
|----------|---------|
| `feirante` | Feirante |
| `ambulante` | Vendedor Ambulante |
| `taxi_uber` | Motorista de App |
| `mototaxi` | Motoboy / Mototaxi |

### 📋 MEI & Outros
| Segmento | Público |
|----------|---------|
| `mei_generico` | MEI / Autônomo |
| `aula_particular` | Professor Autônomo |
| `artesanato` | Artesão / Costureira |

---

## 6 Skills de Marketing

As skills ficam em `.claude/skills/` e estão integradas ao sistema de chat da Alina:

| Skill | Baseada em | Função |
|-------|-----------|--------|
| `analise-criativo` | page-cro + copywriting | Avalia copy em 7 dimensões com nota e versão melhorada |
| `analise-campanha` | campaign-analytics | Diagnóstico de métricas vs benchmarks DarkCred |
| `geracao-copy` | copywriting skill | Gera copies com 3 frameworks (PSA, IE, SNR) |
| `analise-resultado` | social-media-analyzer | Extrai métricas de screenshots de campanha |
| `teste-ab` | ab-test-setup | Plano de teste com hipótese estruturada |
| `otimizacao-segmento` | paid-ads | Distribuição de verba + detecção de saturação |

---

## Sistema de Auto-Alimentação

```
Você gera copies → salvo em dados/historico.json
         │
         ▼
Você envia foto de resultado → Alina extrai métricas via Vision
         │
         ▼
dados/aprendizado.json atualizado com padrões vencedores/perdedores
         │
         ▼
Próxima geração injeta esse contexto no prompt
         │
         ▼
Copies progressivamente melhores 🚀
```

**Arquivos do sistema de aprendizado:**
- `dados/historico.json` — registro de todas as gerações
- `dados/aprendizado.json` — padrões extraídos, scores de hooks/CTAs
- `dados/resultados/` — análises detalhadas de cada campanha analisada

---

## Compliance Automático

Todas as variações geradas passam pelo validador antes de serem entregues.

### Termos PROIBIDOS (bloqueio automático)
```
❌ "Sem consulta SPC/Serasa"      ❌ "Aprovação garantida"
❌ "Liberação imediata"           ❌ "Crédito fácil"
❌ R$ [qualquer valor]            ❌ Taxas de juros (%)
❌ "Aprovado na hora"             ❌ "Dinheiro na hora"
```

### Termos SEGUROS (use ao menos um)
```
✅ "Capital de giro"              ✅ "Fôlego pro seu negócio"
✅ "Sem burocracia"               ✅ "Parcela que cabe no dia a dia"
✅ "Sem enrolação"                ✅ "Força no caixa"
```

---

## Benchmarks DarkCred

### Custo por Mensagem (Direct)
| Resultado | Status | Ação |
|-----------|--------|------|
| < R$ 1,50 | 🟢 Excelente | Escalar verba imediatamente |
| R$ 1,50–2,50 | 🟡 Bom | Manter e monitorar |
| R$ 2,50–3,50 | 🟠 Aceitável | Testar novo hook |
| R$ 3,50–5,00 | 🔴 Ruim | Trocar criativo agora |
| > R$ 5,00 | ⛔ Crítico | Pausar campanha |

### CTR (Taxa de Clique)
| CTR | Status |
|-----|--------|
| > 1,5% | 🟢 Excelente |
| 1,0–1,5% | 🟡 Bom |
| 0,5–1,0% | 🟠 Aceitável |
| < 0,5% | 🔴 Trocar criativo |

### Frequência (Saturação)
| Frequência | Status |
|------------|--------|
| < 1,5 | 🟢 Público fresco |
| 1,5–2,0 | 🟡 Atenção |
| 2,0–2,5 | 🟠 Saturando |
| > 2,5 | ⛔ Saturado — trocar criativo |

### Funil de Conversão DarkCred
```
100 mensagens
  → 75 respondem no WhatsApp  (75%)
  → 45 qualificados           (60%)
  → 35 enviam docs            (78%)
  → 30 fechamentos            (86%)

Taxa geral de fechamento: ~30%
```

---

## Arquitetura

```
DarkCred-Squad/
├── main.py                     # CLI principal (6 modos de operação)
├── alina/
│   ├── config.py               # Termos, segmentos, benchmarks, compliance
│   ├── persona.py              # Personalidade e system prompts da Alina
│   ├── gerador.py              # Wrapper Claude API (geração + chat)
│   ├── construtor_prompt.py    # Constrói prompts com contexto de aprendizado
│   ├── validador.py            # Compliance automático pós-geração
│   ├── saida.py                # Salva outputs + exibição terminal
│   ├── aprendizado.py          # Sistema de memória e padrões
│   ├── analisador.py           # Análise de imagem via Claude Vision
│   └── logger.py               # Logs estruturados
├── .claude/
│   ├── settings.json           # Hooks Claude Code
│   └── skills/                 # 6 skills de marketing
│       ├── analise-criativo/
│       ├── analise-campanha/
│       ├── geracao-copy/
│       ├── analise-resultado/
│       ├── teste-ab/
│       └── otimizacao-segmento/
├── scripts/
│   ├── agendador.py            # Geração agendada 12h/15h/18h30
│   └── verificar_agendados.py  # Exibe pendentes no chat Claude Code
├── dados/
│   ├── historico.json          # Histórico de gerações
│   ├── aprendizado.json        # Padrões aprendidos
│   └── resultados/             # Análises de campanha
├── agendados/                  # Copies agendados pendentes
├── saidas/                     # Copies gerados (JSON + TXT)
└── logs/                       # Logs da aplicação
```

---

## Opções CLI Completas

```
python main.py [opções]

Opções:
  --segmento NOME     Segmento alvo (ou "todos"). Padrão: generico
  --quantidade N      Variações por segmento. Padrão: 5
  --formato TIPO      json | texto | ambos. Padrão: ambos
  --modelo MODELO     Modelo Claude. Padrão: claude-sonnet-4-6
  --analisar IMAGEM   Caminho da imagem de resultado de campanha
  --chat              Modo chat interativo com Alina
  --aprendizado       Exibe resumo do aprendizado acumulado
  --listar-segmentos  Lista todos os segmentos com categorias
```

---

## Configuração do Ambiente

```bash
# .env (criar a partir do .env.example)
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Dependências

```
anthropic>=0.25.0    # SDK Claude API
python-dotenv>=1.0.0 # Variáveis de ambiente
rich>=13.0.0         # Terminal bonito (cores, tabelas, spinners)
schedule>=1.2.0      # Agendamento de tarefas
```

---

## Operação de Mídia DarkCred

| Parâmetro | Valor |
|-----------|-------|
| Formato do anúncio | Feed estático quadrado (1:1) |
| Horário de veiculação | **Apenas 06h–18h** (comerciante na loja) |
| Dias da semana | Domingo a domingo |
| Verba diária | R$ 300–500 |
| Plataforma | Instagram (Meta Ads) |
| Objetivo | Mensagens no Direct |

> **Por que apenas horário comercial?** Na análise pré-liberação, o comerciante precisa enviar um vídeo mostrando o rosto e a data. À noite ele não está na loja.

---

## Licença

MIT — use, modifique, distribua.

---

<div align="center">

**Alina Pretrov v2.0** · Powered by [Claude AI](https://anthropic.com) · DarkCred

</div>

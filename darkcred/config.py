FORBIDDEN_EXACT = [
    "sem consulta spc",
    "sem consulta serasa",
    "aprovação garantida",
    "aprovacao garantida",
    "liberação imediata",
    "liberacao imediata",
    "crédito fácil",
    "credito facil",
]

FORBIDDEN_PATTERNS = [
    r"R\$\s*\d+",
    r"\d+\s*%\s*(ao mês|a\.m\.|mensal|ao mes)",
    r"(aprovad[ao]|liberado|garantid[ao])\s*(na hora|agora|imediatamente|já|ja)",
]

SAFE_TERMS = [
    "Capital de giro",
    "Fôlego pro seu negócio",
    "Sem burocracia",
    "Parcela que cabe no dia a dia",
]

HOOKS = [
    "Precisa de giro pro seu negócio?",
    "Faltou capital pra repor estoque?",
    "Fornecedor quer à vista e você não tem?",
    "Comerciante, me escuta...",
    "Quem tem comércio sabe: às vezes aperta",
    "Tá precisando de uma força no caixa?",
]

CTAS = [
    "Chama no direct 📩",
    "Manda 'GIRO' aqui",
    "Me chama que a gente conversa",
]

SEGMENTS = {
    "generic": {
        "label": "Comerciante geral",
        "context": "pequeno comerciante ou empreendedor autônomo no Brasil",
        "examples": ["lojista", "vendedor", "empreendedor"],
    },
    "padaria": {
        "label": "Padaria / Confeitaria",
        "context": "dono de padaria ou confeitaria",
        "examples": ["farinha, fermento e embalagens", "repor ingredientes", "comprar em quantidade"],
    },
    "salao": {
        "label": "Salão de beleza / Barbearia",
        "context": "dono de salão de beleza, barbearia ou manicure",
        "examples": ["produtos químicos", "equipamentos do salão", "mobiliário e cadeiras"],
    },
    "mercado": {
        "label": "Mercearia / Mercadinho",
        "context": "dono de mercearia ou pequeno mercado",
        "examples": ["repor prateleiras", "comprar à vista no atacado", "estoque de bebidas e secos"],
    },
    "ambulante": {
        "label": "Vendedor ambulante / Barraca de feira",
        "context": "vendedor ambulante, feirante ou dono de barraca",
        "examples": ["montar a banca", "comprar mercadoria para a feira", "capital de giro semanal"],
    },
    "mei": {
        "label": "MEI / Autônomo",
        "context": "MEI ou trabalhador autônomo de qualquer área",
        "examples": ["equipamento de trabalho", "insumos para o serviço", "capital para crescer o negócio"],
    },
}

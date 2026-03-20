# ─────────────────────────────────────────────────────────────
# COMPLIANCE — Termos Proibidos
# ─────────────────────────────────────────────────────────────

TERMOS_PROIBIDOS_EXATOS = [
    "sem consulta spc",
    "sem consulta serasa",
    "aprovação garantida",
    "aprovacao garantida",
    "liberação imediata",
    "liberacao imediata",
    "crédito fácil",
    "credito facil",
    "empréstimo fácil",
    "emprestimo facil",
    "dinheiro na hora",
    "sem juros",
    "juros zero",
    "darkcred",
]

PADROES_PROIBIDOS = [
    r"R\$\s*\d+",                                          # qualquer valor em reais
    r"\d+\s*%\s*(ao mês|a\.m\.|mensal|ao mes)",            # taxas de juros
    r"(aprovad[ao]|liberado|garantid[ao])\s*(na hora|agora|imediatamente|já|ja)",
    r"sem\s*(consulta|análise|analise)\s*(ao)?\s*(spc|serasa|cpf)",
    r"\d+\s*(horas?|minutos?)\s*(para|pra)\s*(liberar|aprovar|cair)",
]

# ─────────────────────────────────────────────────────────────
# TERMOS SEGUROS — Use ao menos um por copy
# ─────────────────────────────────────────────────────────────

TERMOS_SEGUROS = [
    "Capital de giro",
    "Fôlego pro seu negócio",
    "Sem burocracia",
    "Parcela que cabe no dia a dia",
    "Sem enrolação",
    "Força no caixa",
    "Giro pro negócio",
]

# ─────────────────────────────────────────────────────────────
# HOOKS — Aberturas aprovadas (pode adaptar levemente)
# ─────────────────────────────────────────────────────────────

HOOKS = [
    "Precisa de giro pro seu negócio?",
    "Faltou capital pra repor estoque?",
    "Fornecedor quer à vista e você não tem?",
    "Comerciante, me escuta...",
    "Quem tem comércio sabe: às vezes aperta",
    "Tá precisando de uma força no caixa?",
    "Seu negócio merece continuar crescendo",
    "A virada do mês tá pesada pro seu caixa?",
    "Falta capital pra aproveitar uma boa oportunidade?",
    "Comerciante que é comerciante sabe o que é aperto",
    "Teu negócio tá parado por falta de giro?",
    "Precisa comprar à vista mas o caixa não ajuda?",
]

# ─────────────────────────────────────────────────────────────
# CTAs — Use EXATAMENTE como escrito
# REGRA: apenas envio de mensagem ou clique no link. NUNCA comentário.
# ─────────────────────────────────────────────────────────────

CTAS = [
    "Manda uma mensagem agora",
    "Clique no link abaixo e fale comigo",
    "Envia uma mensagem que eu te explico",
    "Clique abaixo e me manda uma mensagem",
    "Fala comigo pelo link abaixo",
]

# ─────────────────────────────────────────────────────────────
# SEGMENTOS — 35+ tipos de negócio brasileiro com renda diária
# ─────────────────────────────────────────────────────────────

SEGMENTOS = {
    # ── GENÉRICO (principal — maior escala) ──────────────────
    "generico": {
        "label": "Comerciante Geral (todos os segmentos)",
        "contexto": "qualquer pequeno comerciante ou empreendedor autônomo no Brasil com renda diária",
        "exemplos": ["lojista", "prestador de serviço", "empreendedor", "autônomo", "comerciante"],
        "categoria": "geral",
    },

    # ── ALIMENTAÇÃO & BEBIDAS ────────────────────────────────
    "padaria": {
        "label": "Padaria / Confeitaria",
        "contexto": "dono de padaria, confeitaria ou panificadora",
        "exemplos": ["farinha e fermento", "repor ingredientes", "comprar em quantidade no atacado"],
        "categoria": "alimentacao",
    },
    "lanchonete": {
        "label": "Lanchonete / Snack Bar",
        "contexto": "dono de lanchonete, snack bar ou casa de salgados",
        "exemplos": ["insumos para lanches", "repor recheios", "comprar embalagens"],
        "categoria": "alimentacao",
    },
    "restaurante": {
        "label": "Restaurante / Marmitaria",
        "contexto": "dono de restaurante pequeno, marmitaria ou self-service",
        "exemplos": ["comprar alimentos no atacado", "pagar fornecedor de hortifrúti", "repor proteínas"],
        "categoria": "alimentacao",
    },
    "pizzaria": {
        "label": "Pizzaria",
        "contexto": "dono de pizzaria ou espaço de pizza",
        "exemplos": ["ingredientes para massa", "mussarela e tomate", "embalagens e caixas"],
        "categoria": "alimentacao",
    },
    "acai": {
        "label": "Açaí / Sorveteria",
        "contexto": "dono de ponto de açaí, sorveteria ou gelateria",
        "exemplos": ["polpa de açaí", "complementos e coberturas", "copos e embalagens"],
        "categoria": "alimentacao",
    },
    "food_truck": {
        "label": "Food Truck / Trailer de Comida",
        "contexto": "operador de food truck ou trailer de comida",
        "exemplos": ["insumos para o evento", "gás e descartáveis", "ingredientes da semana"],
        "categoria": "alimentacao",
    },
    "pastelaria": {
        "label": "Pastelaria / Esfiha",
        "contexto": "dono de pastelaria, barraca de pastel ou esfiha",
        "exemplos": ["massa e recheios", "óleo para fritura", "embalagens e guardanapos"],
        "categoria": "alimentacao",
    },
    "bar": {
        "label": "Bar / Boteco",
        "contexto": "dono de bar, boteco ou ponto de bebidas",
        "exemplos": ["estoque de bebidas", "petiscos e insumos", "gelo e descartáveis"],
        "categoria": "alimentacao",
    },

    # ── BELEZA & CUIDADO PESSOAL ─────────────────────────────
    "salao": {
        "label": "Salão de Beleza",
        "contexto": "dona ou dono de salão de beleza feminino",
        "exemplos": ["produtos químicos", "tinturas e alisamentos", "equipamentos do salão"],
        "categoria": "beleza",
    },
    "barbearia": {
        "label": "Barbearia",
        "contexto": "dono de barbearia ou salão masculino",
        "exemplos": ["produtos para barba", "lâminas e equipamentos", "cadeiras e mobiliário"],
        "categoria": "beleza",
    },
    "manicure": {
        "label": "Manicure / Studio de Unhas",
        "contexto": "manicure autônoma ou dona de studio de unhas",
        "exemplos": ["esmaltes e materiais", "nail art e decoração", "equipamentos de gel"],
        "categoria": "beleza",
    },
    "estetica": {
        "label": "Estética / Spa",
        "contexto": "dona de clínica de estética, spa ou espaço de beleza",
        "exemplos": ["produtos de estética", "equipamentos de tratamento", "insumos para procedimentos"],
        "categoria": "beleza",
    },
    "academia": {
        "label": "Academia / Studio Fitness",
        "contexto": "dono de academia pequena ou studio de fitness",
        "exemplos": ["equipamentos e manutenção", "suplementos para revenda", "aparelhos de musculação"],
        "categoria": "beleza",
    },

    # ── VAREJO & COMÉRCIO ────────────────────────────────────
    "vestuario": {
        "label": "Loja de Roupa / Vestuário",
        "contexto": "dono de loja de roupas, confecções ou moda",
        "exemplos": ["nova coleção", "comprar do fornecedor", "repor estoque de vendas"],
        "categoria": "varejo",
    },
    "calcados": {
        "label": "Loja de Calçados",
        "contexto": "dono de loja de sapatos, tênis ou calçados",
        "exemplos": ["novo lote de calçados", "comprar da fábrica", "repor tamanhos esgotados"],
        "categoria": "varejo",
    },
    "eletronicos": {
        "label": "Loja de Eletrônicos / Celulares",
        "contexto": "dono de loja de eletrônicos, celulares ou informática",
        "exemplos": ["estoque de celulares", "acessórios e capinhas", "peças para manutenção"],
        "categoria": "varejo",
    },
    "variedades": {
        "label": "Loja de Variedades / Bazar",
        "contexto": "dono de loja de variedades, bazar ou utilidades",
        "exemplos": ["produtos variados", "repor o estoque", "novidades para vender"],
        "categoria": "varejo",
    },
    "mercadinho": {
        "label": "Mercadinho / Mercearia",
        "contexto": "dono de mercadinho, mercearia ou mini-mercado",
        "exemplos": ["repor prateleiras", "comprar no atacado", "estoque de bebidas e secos"],
        "categoria": "varejo",
    },
    "farmacia": {
        "label": "Farmácia / Drogaria",
        "contexto": "dono de farmácia independente ou drogaria",
        "exemplos": ["estoque de medicamentos", "produtos de higiene", "comprar do distribuidor"],
        "categoria": "varejo",
    },
    "florista": {
        "label": "Florista / Floricultural",
        "contexto": "florista ou dono de floricultural",
        "exemplos": ["comprar flores frescas", "vasos e substratos", "materiais para arranjos"],
        "categoria": "varejo",
    },

    # ── SERVIÇOS ─────────────────────────────────────────────
    "encanador": {
        "label": "Encanador / Hidráulica",
        "contexto": "encanador autônomo ou dono de empresa de hidráulica",
        "exemplos": ["peças e conexões", "ferramentas", "materiais para obra"],
        "categoria": "servicos",
    },
    "eletricista": {
        "label": "Eletricista",
        "contexto": "eletricista autônomo ou empresa de elétrica",
        "exemplos": ["fios e materiais elétricos", "disjuntores e equipamentos", "ferramentas de trabalho"],
        "categoria": "servicos",
    },
    "mecanico": {
        "label": "Mecânico / Oficina",
        "contexto": "mecânico autônomo ou dono de oficina mecânica",
        "exemplos": ["peças de reposição", "ferramentas especializadas", "óleo e insumos"],
        "categoria": "servicos",
    },
    "chaveiro": {
        "label": "Chaveiro",
        "contexto": "chaveiro autônomo ou loja de chaveiro",
        "exemplos": ["chaves e equipamentos", "fechaduras e cadeados", "kit de abertura"],
        "categoria": "servicos",
    },
    "lavanderia": {
        "label": "Lavanderia",
        "contexto": "dono de lavanderia ou lavanderiaself-service",
        "exemplos": ["produtos de limpeza", "manutenção de máquinas", "embalagens para entrega"],
        "categoria": "servicos",
    },
    "grafica": {
        "label": "Gráfica / Impressão",
        "contexto": "dono de gráfica ou empresa de impressão",
        "exemplos": ["papel e insumos", "tintas para impressão", "materiais de acabamento"],
        "categoria": "servicos",
    },
    "borracharia": {
        "label": "Borracharia / Pneus",
        "contexto": "dono de borracharia ou loja de pneus",
        "exemplos": ["pneus e câmaras", "peças de reposição", "borrachas e materiais"],
        "categoria": "servicos",
    },
    "sapateiro": {
        "label": "Sapateiro / Conserto de Calçados",
        "contexto": "sapateiro ou consertador de calçados",
        "exemplos": ["cola e materiais", "solados e peças", "ferramentas de conserto"],
        "categoria": "servicos",
    },

    # ── AMBULANTES & FEIRA ───────────────────────────────────
    "feirante": {
        "label": "Feirante / Barraca de Feira",
        "contexto": "feirante ou dono de barraca em feira livre",
        "exemplos": ["montar a banca", "comprar mercadoria para a feira", "capital de giro semanal"],
        "categoria": "ambulante",
    },
    "ambulante": {
        "label": "Vendedor Ambulante / Camelô",
        "contexto": "vendedor ambulante, camelô ou vendedor de rua",
        "exemplos": ["repor mercadoria", "comprar o lote novo", "capital para a semana"],
        "categoria": "ambulante",
    },

    # ── MOBILIDADE ───────────────────────────────────────────
    "taxi_uber": {
        "label": "Motorista de Aplicativo / Taxi",
        "contexto": "motorista de Uber, 99, taxi ou mototaxi",
        "exemplos": ["manutenção do veículo", "troca de peças", "abastecimento do mês"],
        "categoria": "mobilidade",
    },
    "mototaxi": {
        "label": "Mototaxi / Motoboy",
        "contexto": "motoboy, entregador ou mototaxista autônomo",
        "exemplos": ["manutenção da moto", "troca de pneu", "peças e revisão"],
        "categoria": "mobilidade",
    },

    # ── EDUCAÇÃO & ARTESANATO ────────────────────────────────
    "aula_particular": {
        "label": "Professor Autônomo / Aulas Particulares",
        "contexto": "professor autônomo que dá aulas particulares",
        "exemplos": ["material didático", "equipamentos para aulas online", "espaço para aulas"],
        "categoria": "educacao",
    },
    "artesanato": {
        "label": "Artesão / Costureira",
        "contexto": "artesão, costureira ou produtor de artesanato",
        "exemplos": ["matéria-prima", "tecidos e aviamentos", "ferramentas de produção"],
        "categoria": "artesanato",
    },

    # ── MEI & AUTÔNOMO ───────────────────────────────────────
    "mei_generico": {
        "label": "MEI / Autônomo (qualquer área)",
        "contexto": "MEI ou trabalhador autônomo de qualquer área com renda diária",
        "exemplos": ["equipamento de trabalho", "insumos para o serviço", "capital para crescer"],
        "categoria": "mei",
    },
}

# ─────────────────────────────────────────────────────────────
# BENCHMARKS DARKCRED
# ─────────────────────────────────────────────────────────────

BENCHMARKS = {
    "custo_mensagem": {
        "excelente": 1.50,
        "bom": 2.50,
        "aceitavel": 3.50,
        "ruim": 5.00,
    },
    "ctr": {
        "excelente": 1.5,
        "bom": 1.0,
        "aceitavel": 0.5,
        "ruim": 0.0,
    },
    "frequencia": {
        "fresco": 1.5,
        "atencao": 2.0,
        "saturando": 2.5,
        "saturado": float("inf"),
    },
    "cpm_referencia_brasil": {
        "bom": 8.0,
        "normal": 15.0,
    },
}

FUNIL_TAXAS = {
    "mensagem_para_whatsapp": 0.75,
    "whatsapp_para_qualificado": 0.60,
    "qualificado_para_docs": 0.78,
    "docs_para_fechamento": 0.86,
    "taxa_total_fechamento": 0.30,
}

OPERACAO = {
    "horario_inicio": 6,
    "horario_fim": 18,
    "verba_minima_diaria": 300,
    "verba_maxima_diaria": 500,
    "dias_semana": "domingo a domingo",
}

LIMITE_CARACTERES_COPY = 500
LIMITE_CARACTERES_HOOK = 80

import json
import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Lista exata com os 9 projetos fornecidos
URLS_PROJETOS = [
    "https://snhbm.lu/projets/vente/bien/rev-ke2-mu/",
    "https://snhbm.lu/projets/vente/bien/rev-ih3559-023/",
    "https://snhbm.lu/projets/vente/bien/ae14-4-5/",
    "https://snhbm.lu/projets/vente/bien/esch-sur-alzette-mu/",
    "https://snhbm.lu/projets/vente/bien/rev-ke2-app/",
    "https://snhbm.lu/projets/vente/bien/rev-ih3298-094/",
    "https://snhbm.lu/projets/vente/bien/rev-ih2861-133/",
    "https://snhbm.lu/projets/vente/bien/rev-ih2867-183/",
    "https://snhbm.lu/projets/vente/bien/rev-ih3294-088/"
]

DATA_FILE = "estado_anterior.json"

def extrair_dados_projeto(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    imoveis = {}
    
    # Nome padrão baseado no link caso a página falhe ao ler o h1
    nome_projeto = url.rstrip("/").split("/")[-1].replace("-", " ").title()

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return nome_projeto, imoveis

        soup = BeautifulSoup(response.content, "html.parser")
        
        # Tenta pegar o nome oficial do projeto
        h1 = soup.find("h1")
        if h1 and h1.text.strip():
            nome_projeto = h1.text.strip()

        texto = soup.get_text("\n")
        linhas = [l.strip() for l in texto.split("\n") if l.strip()]

        # Padrão de referência (ex: IH3055, IH3059 - réservé, IH3061 - vendu)
        ref_pattern = re.compile(r'^([A-Z0-9]{2,12})(?:\s*-\s*(réservé|vendu))?$', re.IGNORECASE)

        i = 0
        while i < len(linhas):
            linha = linhas[i]
            match = ref_pattern.match(linha)

            if match and any(c.isdigit() for c in linha) and len(linha) <= 30:
                ref_base = match.group(1).upper()
                sufixo = (match.group(2) or "").lower()

                # Status conforme sufixo da referência
                if "vendu" in sufixo or "vendu" in linha.lower():
                    status = "Vendido"
                elif "reserv" in sufixo or "réservé" in linha.lower():
                    status = "Reservado"
                else:
                    status = "Disponível"

                chambres = "N/D"
                surface = "N/D"
                preco = "N/D"

                # Varre as linhas seguintes para capturar características
                for j in range(i + 1, min(i + 22, len(linhas))):
                    item = linhas[j]
                    if "m²" in item and surface == "N/D":
                        surface = item
                    elif re.match(r'^[1-9]$', item) and chambres == "N/D":
                        chambres = f"{item} ch."
                    elif "€" in item:
                        preco = item

                imoveis[ref_base] = {
                    "codigo": ref_base,
                    "ref_completa": linha,
                    "status": status,
                    "chambres": chambres,
                    "surface": surface,
                    "preco": preco
                }
            i += 1

    except Exception as e:
        print(f"Erro ao processar {url}: {e}")

    return nome_projeto, imoveis

def executar():
    estado_atual = {}

    for url in URLS_PROJETOS:
        nome_proj, imoveis = extrair_dados_projeto(url)
        if imoveis:
            estado_atual[nome_proj] = {
                "url": url,
                "imoveis": imoveis
            }

    estado_anterior = {}
    historico_mudancas = []

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                conteudo = json.load(f)
                estado_anterior = conteudo.get("dados", {})
                historico_mudancas = conteudo.get("historico", [])
        except Exception:
            pass

    novas_mudancas = []
    data_hora_atual = datetime.now().strftime("%d/%m/%Y %H:%M")

    for nome_proj, dados in estado_atual.items():
        imoveis_atuais = dados["imoveis"]
        imoveis_antigos = estado_anterior.get(nome_proj, {}).get("imoveis", {})

        for codigo, info_nova in imoveis_atuais.items():
            status_novo = info_nova["status"]
            info_antiga = imoveis_antigos.get(codigo, {})
            status_antigo = info_antiga.get("status")

            if status_antigo is not None and status_antigo != status_novo:
                novas_mudancas.append({
                    "data": data_hora_atual,
                    "projeto": nome_proj,
                    "imovel": codigo,
                    "de": status_antigo,
                    "para": status_novo,
                    "preco": info_nova["preco"],
                    "chambres": info_nova["chambres"]
                })

    if novas_mudancas:
        historico_mudancas = novas_mudancas + historico_mudancas
        historico_mudancas = historico_mudancas[:30]

    dados_salvar = {
        "ultima_atualizacao": data_hora_atual,
        "dados": estado_atual,
        "historico": historico_mudancas
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados_salvar, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    executar()

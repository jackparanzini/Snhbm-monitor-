import json
import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://snhbm.lu/projets/vente/"
DATA_FILE = "estado_anterior.json"

def obter_projetos():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(BASE_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, "html.parser")
        
        projetos = []
        for link in soup.find_all("a", href=True):
            url = link["href"]
            if "/projets/vente/bien/" in url or "/bien/" in url:
                if url.startswith("/"):
                    url = "https://snhbm.lu" + url
                if not any(p["url"] == url for p in projetos):
                    nome = link.text.strip() or url.split("/")[-2].replace("-", " ").title()
                    projetos.append({"nome": nome, "url": url})
        return projetos
    except Exception as e:
        print(f"Erro ao buscar lista de projetos: {e}")
        return []

def extrair_imoveis_detalhados(url_projeto):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    imoveis = {}
    try:
        response = requests.get(url_projeto, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, "html.parser")
        texto_pagina = soup.get_text("\n")
        
        # Procura por padrões de referência como IH3055, IH3059 - réservé, IH3061 - vendu
        padrao_ref = re.compile(r'\b([A-Z0-9]{3,8})(?:\s*-\s*(réservé|vendu))?\b', re.IGNORECASE)
        
        # Divide a página por blocos de texto
        linhas = [l.strip() for l in texto_pagina.split('\n') if l.strip()]
        
        i = 0
        while i < len(linhas):
            linha = linhas[i]
            match = padrao_ref.match(linha)
            
            # Identifica se a linha é o início de um imóvel (ex: IH3055, IH3059 - réservé)
            if match and len(linha) <= 25 and any(char.isdigit() for char in linha):
                ref_base = match.group(1).upper()
                sufixo = (match.group(2) or "").lower()
                
                if "vendu" in sufixo or "vendu" in linha.lower():
                    status = "Vendido"
                elif "reserv" in sufixo or "réservé" in linha.lower():
                    status = "Reservado"
                else:
                    status = "Disponível"
                
                # Coleta detalhes dos próximos elementos
                chambres = "N/D"
                surface = "N/D"
                preco = "N/D"
                
                # Varre as próximas 15 linhas buscando características
                for j in range(i + 1, min(i + 20, len(linhas))):
                    l_sub = linhas[j]
                    if "m²" in l_sub and surface == "N/D":
                        surface = l_sub
                    elif re.match(r'^\d+$', l_sub) and chambres == "N/D" and int(l_sub) <= 10:
                        chambres = l_sub
                    elif "€" in l_sub:
                        preco = l_sub  # Atualiza com o valor em Euros encontrado
                
                imoveis[ref_base] = {
                    "codigo": ref_base,
                    "status": status,
                    "chambres": chambres,
                    "surface": surface,
                    "preco": preco
                }
            i += 1
            
    except Exception as e:
        print(f"Erro ao extrair imóveis de {url_projeto}: {e}")
        
    return imoveis

def executar():
    projetos = obter_projetos()
    estado_atual = {}

    for proj in projetos:
        imoveis = extrair_imoveis_detalhados(proj["url"])
        if imoveis:
            estado_atual[proj["nome"]] = {
                "url": proj["url"],
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

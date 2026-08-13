import json
import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://snhbm.lu/projets/vente/"
DATA_FILE = "estado_anterior.json"

def obter_projetos():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(BASE_URL, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    
    projetos = []
    for link in soup.find_all("a", href=True):
        url = link["href"]
        if "/projet/" in url or "/projets/" in url:
            if url.startswith("/"):
                url = "https://snhbm.lu" + url
            if url != BASE_URL and not any(p["url"] == url for p in projetos):
                nome = link.text.strip() or url.split("/")[-2].replace("-", " ").title()
                projetos.append({"nome": nome, "url": url})
    return projetos

def extrair_apartamentos(url_projeto):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url_projeto, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    
    apartamentos = {}
    elementos = soup.find_all(["div", "li", "tr", "span", "p"])
    for el in elementos:
        texto = el.text.strip()
        match = re.search(r"\b([A-Z0-9]{3,8})\b", texto)
        if match:
            codigo = match.group(1)
            texto_lower = texto.lower()
            if "vendu" in texto_lower:
                status = "Vendido"
            elif "reserv" in texto_lower:
                status = "Reservado"
            else:
                status = "Disponível"
            apartamentos[codigo] = status
    return apartamentos

def executar():
    projetos = obter_projetos()
    estado_atual = {}

    for proj in projetos:
        aptos = extrair_apartamentos(proj["url"])
        estado_atual[proj["nome"]] = {
            "url": proj["url"],
            "apartamentos": aptos
        }

    estado_anterior = {}
    historico_mudancas = []

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            conteudo = json.load(f)
            estado_anterior = conteudo.get("dados", {})
            historico_mudancas = conteudo.get("historico", [])

    novas_mudancas = []
    data_hora_atual = datetime.now().strftime("%d/%m/%Y %H:%M")

    for nome_proj, dados in estado_atual.items():
        aptos_atuais = dados["apartamentos"]
        aptos_antigos = estado_anterior.get(nome_proj, {}).get("apartamentos", {})

        for codigo, status_novo in aptos_atuais.items():
            status_antigo = aptos_antigos.get(codigo)
            if status_antigo is not None and status_antigo != status_novo:
                novas_mudancas.append({
                    "data": data_hora_atual,
                    "projeto": nome_proj,
                    "imovel": codigo,
                    "de": status_antigo,
                    "para": status_novo
                })

    if novas_mudancas:
        historico_mudancas = novas_mudancas + historico_mudancas
        historico_mudancas = historico_mudancas[:20]

    dados_salvar = {
        "ultima_atualizacao": data_hora_atual,
        "dados": estado_atual,
        "historico": historico_mudancas
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados_salvar, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    executar()

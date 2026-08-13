import streamlit as st
import json
import os

st.set_page_config(page_title="Painel SNHBM", page_icon="🏢", layout="wide")

st.title("🏢 Painel de Imóveis SNHBM")
st.caption("Atualizado automaticamente duas vezes ao dia (às 08:00 e 15:00).")

DATA_FILE = "estado_anterior.json"

if not os.path.exists(DATA_FILE):
    st.info("O sistema está registrando a primeira varredura do site. Aguarde alguns instantes e recarregue a página.")
else:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        conteudo = json.load(f)

    dados = conteudo.get("dados", {})
    historico = conteudo.get("historico", [])
    ultima_att = conteudo.get("ultima_atualizacao", "Desconhecida")

    st.write(f"🕒 **Última verificação no site da SNHBM:** {ultima_att}")

    # Exibe as alterações recentes se houver
    if historico:
        st.subheader("🚨 Histórico de Alterações Detectadas")
        for mudanca in historico:
            st.warning(f"**[{mudanca['data']}] {mudanca['projeto']}** — Imóvel `{mudanca['imovel']}` mudou de **{mudanca['de']}** ➔ **{mudanca['para']}**")
        st.markdown("---")

    # Resumo Geral
    total_projetos = len(dados)
    disponiveis = sum(sum(1 for st in p["apartamentos"].values() if st == "Disponível") for p in dados.values())
    reservados = sum(sum(1 for st in p["apartamentos"].values() if st == "Reservado") for p in dados.values())
    vendidos = sum(sum(1 for st in p["apartamentos"].values() if st == "Vendido") for p in dados.values())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Projetos", total_projetos)
    col2.metric("Disponíveis", disponiveis)
    col3.metric("Reservados", reservados)
    col4.metric("Vendidos", vendidos)

    st.markdown("---")

    # Lista por Projeto
    st.subheader("📋 Status Atual de Todos os Projetos")
    filtro = st.selectbox("Filtrar por Projeto:", ["Todos"] + list(dados.keys()))

    for nome_proj, info in dados.items():
        if filtro != "Todos" and filtro != nome_proj:
            continue

        with st.expander(f"📌 {nome_proj} ({len(info['apartamentos'])} imóveis)", expanded=True):
            st.markdown(f"[🔗 Acessar página oficial do projeto no site da SNHBM]({info['url']})")
            
            cols = st.columns(3)
            idx = 0
            for codigo, status in info["apartamentos"].items():
                col = cols[idx % 3]
                if status == "Disponível":
                    col.success(f"🟢 **{codigo}**: Disponível")
                elif status == "Reservado":
                    col.warning(f"🟡 **{codigo}**: Reservado")
                else:
                    col.error(f"🔴 **{codigo}**: Vendido")
                idx += 1

import streamlit as st
import json
import os

st.set_page_config(page_title="Painel SNHBM", page_icon="🏢", layout="wide")

st.title("🏢 Painel de Imóveis SNHBM")
st.caption("Verificação automática duas vezes ao dia (08:00 e 15:00).")

DATA_FILE = "estado_anterior.json"

if not os.path.exists(DATA_FILE):
    st.info("ℹ️ O sistema ainda não executou a primeira varredura. Vá na aba Actions do GitHub e clique em 'Run workflow' para carregar os dados imediatamente.")
else:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        conteudo = json.load(f)

    dados = conteudo.get("dados", {})
    historico = conteudo.get("historico", [])
    ultima_att = conteudo.get("ultima_atualizacao", "Desconhecida")

    st.write(f"🕒 **Última verificação no site da SNHBM:** {ultima_att}")

    # Exibe Histórico de Alterações se houver
    if historico:
        st.subheader("🚨 Alterações Recentes Detectadas")
        for m in historico:
            st.warning(f"**[{m['data']}] {m['projeto']}** — Imóvel `{m['imovel']}` ({m.get('chambres', '?')} quartos) mudou de **{m['de']}** ➔ **{m['para']}** | Preço: {m.get('preco', 'N/D')}")
        st.markdown("---")

    # Contadores Gerais
    total_projetos = len(dados)
    todos_imoveis = [imovel for proj in dados.values() for imovel in proj["imoveis"].values()]
    disponiveis = sum(1 for i in todos_imoveis if i["status"] == "Disponível")
    reservados = sum(1 for i in todos_imoveis if i["status"] == "Reservado")
    vendidos = sum(1 for i in todos_imoveis if i["status"] == "Vendido")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Projetos", total_projetos)
    col2.metric("🟢 Disponíveis", disponiveis)
    col3.metric("🟡 Reservados", reservados)
    col4.metric("🔴 Vendidos", vendidos)

    st.markdown("---")

    # Filtros e Detalhes
    st.subheader("📋 Lista Detalhada dos Imóveis")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_proj = st.selectbox("Filtrar por Projeto:", ["Todos"] + list(dados.keys()))
    with col_f2:
        filtro_status = st.selectbox("Filtrar por Status:", ["Todos", "Disponível", "Reservado", "Vendido"])

    for nome_proj, info in dados.items():
        if filtro_proj != "Todos" and filtro_proj != nome_proj:
            continue

        imoveis_proj = info["imoveis"]
        
        # Aplica filtro de status
        imoveis_filtrados = {
            ref: dados_i for ref, dados_i in imoveis_proj.items() 
            if filtro_status == "Todos" or dados_i["status"] == filtro_status
        }

        if not imoveis_filtrados:
            continue

        with st.expander(f"📌 {nome_proj} ({len(imoveis_filtrados)} imóveis)", expanded=True):
            st.markdown(f"[🔗 Abrir página oficial do projeto na SNHBM]({info['url']})")
            
            # Tabela resumida e bonita
            tabela_dados = []
            for ref, item in imoveis_filtrados.items():
                status_icon = "🟢 Disponível" if item["status"] == "Disponível" else ("🟡 Reservado" if item["status"] == "Reservado" else "🔴 Vendido")
                tabela_dados.append({
                    "Referência": item["codigo"],
                    "Status": status_icon,
                    "Quartos": item["chambres"],
                    "Área": item["surface"],
                    "Preço Aproximado": item["preco"]
                })
            
            st.dataframe(tabela_dados, use_container_width=True)

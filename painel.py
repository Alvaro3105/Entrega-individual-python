import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import math

import pandas as pd
import plotly.express as px
import streamlit as st

from integrante_2_alvaro import estatisticas as E
from integrante_2_alvaro.etl import GRUPO_MODAL, MEIOS, PASTA_DADOS, RACAS, REGIOES, TEMPO_FAIXAS

TITULO = "Tempo de deslocamento"
FONTE = "Fonte: IBGE, Censo Demográfico 2022, SIDRA 10330 (resultados preliminares da amostra)."
CORES_GRUPO = {"Público": "#2563EB", "Particular": "#DC2626", "Ativo": "#16A34A", "Outros": "#9CA3AF"}
CORES_RACA = {"Branca": "#E69F00", "Preta": "#56B4E9", "Parda": "#009E73", "Amarela": "#CC79A7", "Indígena": "#0072B2"}
MIN_PESSOAS = 1_000


@st.cache_data
def carregar_dados() -> dict:
    return {
        "uf": pd.read_csv(PASTA_DADOS / "tempo_meio_raca_uf.csv", dtype={"cod_ibge": str}),
        "municipio": pd.read_csv(PASTA_DADOS / "tempo_raca_municipio.csv.gz", dtype={"cod_ibge": str}),
    }


def selecionar_agregado(dados: dict, filtros: dict) -> tuple[pd.DataFrame, str]:
    uf = dados["uf"]
    if filtros.get("uf"):
        df, nome = uf[(uf["nivel"] == "UF") & (uf["uf"] == filtros["uf"])], filtros["uf"]
    elif filtros.get("regiao"):
        df, nome = uf[(uf["nivel"] == "Região") & (uf["regiao"] == filtros["regiao"])], f"Região {filtros['regiao']}"
    else:
        df, nome = uf[uf["nivel"] == "Brasil"], "Brasil"
    return df[df["raca"].isin(filtros.get("racas") or RACAS) & df["meio"].isin(filtros.get("meios") or MEIOS)], nome


def municipios_do_territorio(dados: dict, filtros: dict) -> pd.DataFrame:
    df = dados["municipio"]
    if filtros.get("regiao"):
        df = df[df["regiao"] == filtros["regiao"]]
    if filtros.get("uf"):
        df = df[df["uf"] == filtros["uf"]]
    return df[df["raca"].isin(filtros.get("racas") or RACAS)]


@st.cache_data(show_spinner="Calculando a mediana de cada município...")
def medianas_municipais(df: pd.DataFrame) -> pd.DataFrame:
    return E.por_municipio(df)


def matriz_meio_raca(df: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for (meio, raca), grupo in df.groupby(["meio", "raca"]):
        f = E.frequencias(grupo)
        linhas.append({"meio": meio, "raca": raca,
                       "mediana": E.quantil_agrupado(f, 0.5) if f.sum() >= MIN_PESSOAS else float("nan")})
    m = pd.DataFrame(linhas).pivot(index="meio", columns="raca", values="mediana")
    return m.reindex(index=[x for x in MEIOS if x in m.index], columns=[r for r in RACAS if r in m.columns])


def fmt_num(v, casas: int = 0) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v) -> str:
    return "—" if v is None else f"{fmt_num(v, 1)}%"


def fmt_min(v) -> str:
    return "—" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{fmt_num(v, 1)} min"


def tema(fig, titulo: str, altura: int = 420):
    fig.update_layout(title=dict(text=titulo, x=0, y=1, yanchor="top", pad=dict(t=8)), height=altura,
                      margin=dict(l=10, r=10, t=100, b=10), separators=",.",
                      legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0, title=None))
    return fig


def mostrar(fig) -> None:
    st.plotly_chart(fig, width="stretch")
    st.caption(FONTE)


def cards(itens: list[tuple[str, str, str]]) -> None:
    for inicio in range(0, len(itens), 3):
        for coluna, (rotulo, valor, detalhe) in zip(st.columns(3), itens[inicio:inicio + 3]):
            with coluna.container(border=True):
                st.caption(rotulo)
                st.markdown(f"<div style='font-size:1.55rem;font-weight:650'>{valor}</div>", unsafe_allow_html=True)
                st.caption(detalhe)


def tabela_estatistica(r: dict, unidade: str) -> None:
    nomes = [("media", "Média"), ("mediana", "Mediana (Q2)"), ("moda", "Moda (1 casa)"), ("q1", "Q1"),
             ("q3", "Q3"), ("iqr", "IQR (Q3 − Q1)"), ("minimo", "Mínimo"), ("maximo", "Máximo"),
             ("amplitude", "Amplitude"), ("variancia", "Variância"), ("desvio_padrao", "Desvio padrão"),
             ("limite_superior", "Limite superior de outlier (Q3 + 1,5·IQR)")]
    linhas = [{"Medida": "Nº de municípios", "Valor": fmt_num(r["n"])}]
    linhas += [{"Medida": n, "Valor": f"{fmt_num(r[c], 2)} {unidade}{'²' if c == 'variancia' else ''}"} for c, n in nomes]
    linhas.append({"Medida": "Outliers", "Valor": fmt_num(r["qtd_outliers"])})
    st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")


def grafico_distribuicao(df: pd.DataFrame):
    t = E.participacao(df, "tempo_faixa", por=["raca"])
    fig = px.bar(t, x="tempo_faixa", y="percentual", color="raca", barmode="group",
                 category_orders={"tempo_faixa": TEMPO_FAIXAS, "raca": RACAS}, color_discrete_map=CORES_RACA,
                 labels={"percentual": "% do grupo racial", "tempo_faixa": "Tempo até o trabalho", "raca": "Raça"})
    return tema(fig, "Distribuição percentual por faixa de tempo e cor ou raça")


def grafico_raca(por_raca: pd.DataFrame):
    longo = por_raca.melt(id_vars="raca", value_vars=["pct_mais_1h", "pct_mais_2h"], var_name="limite",
                          value_name="percentual")
    longo["limite"] = longo["limite"].map({"pct_mais_1h": "Mais de 1 h", "pct_mais_2h": "Mais de 2 h"})
    fig = px.bar(longo, x="raca", y="percentual", color="limite", barmode="group", text_auto=".1f",
                 category_orders={"raca": RACAS}, color_discrete_sequence=["#F59E0B", "#B91C1C"],
                 labels={"percentual": "% do grupo", "raca": ""})
    return tema(fig, "Deslocamentos demorados por cor ou raça (%)", 380)


def grafico_mediana_raca(por_raca: pd.DataFrame):
    fig = px.bar(por_raca, x="raca", y="mediana", color="raca", text_auto=".1f", color_discrete_map=CORES_RACA,
                 category_orders={"raca": RACAS}, labels={"mediana": "Mediana estimada (min)", "raca": ""})
    fig.update_layout(showlegend=False)
    return tema(fig, "Mediana estimada do tempo por cor ou raça (min)", 380)


def grafico_meio(por_meio: pd.DataFrame, coluna: str, rotulo: str, titulo: str):
    d = por_meio[por_meio["n"] >= MIN_PESSOAS].assign(grupo=lambda x: x["meio"].map(GRUPO_MODAL))
    fig = px.bar(d, y="meio", x=coluna, color="grupo", orientation="h", text_auto=".1f",
                 color_discrete_map=CORES_GRUPO, labels={coluna: rotulo, "meio": "", "grupo": "Grupo"})
    fig.update_yaxes(categoryorder="total ascending")
    return tema(fig, titulo, 480)


def grafico_matriz(matriz: pd.DataFrame):
    fig = px.imshow(matriz, text_auto=".0f", color_continuous_scale="OrRd", aspect="auto",
                    labels={"x": "Cor ou raça", "y": "Meio de transporte", "color": "Minutos"})
    return tema(fig, "Mediana estimada do tempo (min): meio de transporte × cor ou raça", 520)


def grafico_boxplot(ind: pd.DataFrame, coluna: str, rotulo: str):
    fig = px.box(ind, x="regiao", y=coluna, color="regiao", points="outliers", hover_name="local",
                 category_orders={"regiao": REGIOES}, labels={coluna: rotulo, "regiao": ""})
    fig.update_layout(showlegend=False)
    return tema(fig, f"{rotulo} nos municípios, por região (boxplot — cada ponto = 1 município)")


def render(dados: dict, filtros: dict) -> None:
    agregado, nome_agregado = selecionar_agregado(dados, filtros)
    st.header("⏱️ Tempo de deslocamento até o trabalho")
    st.caption(f"Responsável: **Alvaro** · Território: **{nome_agregado}**")
    if filtros.get("municipio"):
        st.warning(f"O IBGE publica tempo × meio × raça só até o nível de UF. Mostrando {nome_agregado}; "
                   "na aba Estatística, o município aparece entre os demais.")
    if agregado["pessoas"].sum() == 0:
        st.error("Nenhuma pessoa com esses filtros. Amplie a seleção.")
        return

    geral = E.resumo_agrupado(agregado)
    por_raca = E.resumo_por_categoria(agregado, "raca", RACAS)
    por_meio = E.resumo_por_categoria(agregado, "meio", MEIOS)
    pior_raca = por_raca.loc[por_raca["mediana"].idxmax()]
    validos = por_meio[por_meio["n"] >= MIN_PESSOAS]
    pior_meio = validos.loc[validos["mediana"].idxmax()] if len(validos) else None
    dif_pp = por_raca["pct_mais_1h"].max() - por_raca["pct_mais_1h"].min()

    cards([
        ("Mediana estimada", fmt_min(geral["mediana"]), "Metade leva menos que isso"),
        ("Mais de 1 hora", fmt_pct(geral["pct_mais_1h"]), "% dos trabalhadores"),
        ("Mais de 2 horas", fmt_pct(geral["pct_mais_2h"]), "% dos trabalhadores"),
        ("Faixa predominante", geral["classe_modal"], "Classe modal (moda)"),
        ("Maior mediana por raça", f"{pior_raca['raca']} · {fmt_min(pior_raca['mediana'])}", "Grupo mais afetado"),
        ("Diferença > 1 h entre raças", f"{fmt_num(dif_pp, 1)} p.p.", "Maior % − menor % (pontos percentuais)"),
    ])

    aba0, aba1, aba2, aba3, aba4 = st.tabs(["🎯 Mediana meio × raça", "📊 Gráficos", "📐 Estatística",
                                           "💡 Interpretação", "🔎 Metodologia"])

    with aba0:
        st.markdown(f"**Pergunta 1 da persona:** qual é a mediana do tempo por meio de transporte e raça? ({nome_agregado})")
        matriz = matriz_meio_raca(agregado)
        mostrar(grafico_matriz(matriz))
        st.caption(f"Células vazias: menos de {fmt_num(MIN_PESSOAS)} pessoas (estimativa instável).")
        st.dataframe(matriz.round(1).reset_index().rename(columns={"meio": "Meio de transporte"}),
                     hide_index=True, width="stretch")

    with aba1:
        mostrar(grafico_distribuicao(agregado))
        c1, c2 = st.columns(2)
        with c1:
            mostrar(grafico_mediana_raca(por_raca))
        with c2:
            mostrar(grafico_raca(por_raca))
        c3, c4 = st.columns(2)
        with c3:
            mostrar(grafico_meio(por_meio, "mediana", "Mediana estimada (min)", "Mediana estimada por meio (min)"))
        with c4:
            mostrar(grafico_meio(por_meio, "pct_mais_1h", "% com mais de 1 h", "Gargalos: % com mais de 1 hora"))

    with aba2:
        st.markdown("#### a) Medidas para dados agrupados")
        st.latex(r"\text{Mediana} \approx L_i + \frac{\frac{n}{2} - F_{ant}}{f_i} \times h")
        st.dataframe(pd.DataFrame([
            {"Medida": "Mediana estimada (Q2)", "Valor": fmt_min(geral["mediana"])},
            {"Medida": "Q1 estimado", "Valor": fmt_min(geral["q1"])},
            {"Medida": "Q3 estimado", "Valor": fmt_min(geral["q3"])},
            {"Medida": "IQR estimado", "Valor": fmt_min(geral["iqr"])},
            {"Medida": "Classe mediana", "Valor": geral["classe_mediana"]},
            {"Medida": "Classe modal (moda)", "Valor": geral["classe_modal"]},
            {"Medida": "Média estimada (ponto médio)*", "Valor": fmt_min(geral["media_estimada"])},
        ]), hide_index=True, width="stretch")
        st.caption(f"*A faixa 'Mais de 4 h' não tem fim: assumimos {E.PONTO_MEDIO_ABERTA} min. "
                   "A média é aproximada; a mediana é a medida principal.")

        st.markdown("#### b) Comparação entre municípios (boxplot e outliers)")
        st.markdown("Não temos o tempo de cada pessoa, então **não** fazemos boxplot de pessoas. Calculamos a "
                    "**mediana estimada de cada município**: cada município vira uma observação numérica.")
        c1, c2 = st.columns(2)
        metrica = c1.selectbox("Indicador", ["Mediana estimada (min)", "% com mais de 1 h"], key="alv_met")
        minimo = c2.slider("Mínimo de trabalhadores por município", 0, 50_000, 5_000, 1_000, key="alv_min")
        ind = medianas_municipais(municipios_do_territorio(dados, filtros))
        ind = ind[ind["total"] >= minimo]
        coluna, unidade = ("mediana", "min") if metrica.startswith("Mediana") else ("pct_mais_1h", "%")
        if len(ind) < 5:
            st.warning("Poucos municípios. Amplie o território ou reduza o mínimo.")
        else:
            r = E.resumo_descritivo(ind[coluna])
            tabela_estatistica(r, unidade)
            mostrar(grafico_boxplot(ind, coluna, metrica))
            if filtros.get("municipio"):
                linha = ind[ind["cod_ibge"] == filtros["municipio"]]
                if len(linha):
                    st.info(f"**{linha['local'].iloc[0]}**: mediana {fmt_min(linha['mediana'].iloc[0])}, "
                            f"{fmt_pct(linha['pct_mais_1h'].iloc[0])} com mais de 1 h.")
            gargalos = E.marcar_outliers(ind, coluna)
            gargalos = gargalos[gargalos["outlier"] == "Acima"].sort_values(coluna, ascending=False)
            st.markdown(f"**Gargalos (outliers acima de {fmt_num(r['limite_superior'], 1)} {unidade}):** "
                        f"{len(gargalos)} município(s)")
            st.dataframe(gargalos[["local", "uf", "mediana", "pct_mais_1h", "total"]].round(1).head(20)
                         .rename(columns={"local": "Município", "uf": "UF", "mediana": "Mediana (min)",
                                          "pct_mais_1h": "% > 1 h", "total": "Trabalhadores"}),
                         hide_index=True, width="stretch")
            texto = f"Média = {fmt_num(r['media'], 1)} {unidade}; mediana = {fmt_num(r['mediana'], 1)} {unidade}. "
            if r["media"] > r["mediana"]:
                texto += ("Os municípios com tempos muito altos (outliers, em geral cidades-dormitório de grandes "
                          "metrópoles) puxam a média para cima. A **mediana** descreve melhor o município típico.")
            st.markdown(texto)

    with aba3:
        texto = (f"Em **{nome_agregado}**, metade dos trabalhadores leva até **{fmt_min(geral['mediana'])}** para "
                 f"chegar ao trabalho. **{fmt_pct(geral['pct_mais_1h'])}** levam mais de 1 hora.\n\n"
                 f"O grupo **{pior_raca['raca'].lower()}** tem a maior mediana ({fmt_min(pior_raca['mediana'])}), e a "
                 f"diferença na proporção de viagens acima de 1 h entre os grupos raciais chega a **{fmt_num(dif_pp, 1)} "
                 "pontos percentuais**.")
        if pior_meio is not None:
            texto += (f"\n\nO meio com maior mediana é **{pior_meio['meio']}** ({fmt_min(pior_meio['mediana'])}; "
                      f"{fmt_pct(pior_meio['pct_mais_1h'])} acima de 1 h). Os gargalos estão no transporte coletivo: "
                      "faixas exclusivas, mais frequência e integração podem reduzir esses tempos.")
        st.markdown(texto)

    with aba4:
        st.info("Fonte: SIDRA 10330. Tempo habitual do domicílio até o trabalho principal, em 7 faixas. "
                "Mediana, Q1 e Q3 são ESTIMATIVAS por interpolação dentro da classe.")
        st.markdown("- Limites das faixas (min): 0–5, 5–15, 15–30, 30–60, 60–120, 120–240 e mais de 240 (aberta).\n"
                    "- Percentuais entre quem declarou o tempo (cerca de 0,8% não declarou).\n"
                    "- A base municipal não tem o meio de transporte (o filtro de meio não se aplica a ela).")


def barra_lateral(dados: dict) -> dict:
    sb = st.sidebar
    sb.header("Filtros")
    mun = dados["municipio"][["cod_ibge", "local", "uf", "regiao"]].drop_duplicates().sort_values("local")
    regiao = sb.selectbox("Região", ["Brasil (todas)"] + REGIOES)
    regiao = None if regiao.startswith("Brasil") else regiao
    ufs = sorted(mun[mun["regiao"] == regiao]["uf"].unique() if regiao else mun["uf"].unique())
    uf = sb.selectbox("UF", ["Todas"] + list(ufs))
    uf = None if uf == "Todas" else uf
    municipio = None
    if uf:
        opcoes = {"Todos": None} | dict(zip(mun[mun["uf"] == uf]["local"], mun[mun["uf"] == uf]["cod_ibge"]))
        municipio = opcoes[sb.selectbox("Município", list(opcoes))]
    racas = sb.multiselect("Cor ou raça", RACAS, default=RACAS)
    meios = sb.multiselect("Meio de transporte", MEIOS, default=MEIOS)
    return {"regiao": regiao, "uf": uf, "municipio": municipio, "racas": racas, "meios": meios}


if __name__ == "__main__":
    st.set_page_config(page_title=TITULO, page_icon="⏱️", layout="wide")
    dados_alv = carregar_dados()
    render(dados_alv, barra_lateral(dados_alv))

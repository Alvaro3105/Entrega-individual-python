import numpy as np
import pandas as pd


LIMITES = {
    "Até 5 min": (0, 5),
    "6 a 15 min": (5, 15),
    "15 a 30 min": (15, 30),
    "30 min a 1 h": (30, 60),
    "1 a 2 h": (60, 120),
    "2 a 4 h": (120, 240),
    "Mais de 4 h": (240, None),
}

PONTO_MEDIO_ABERTA = 270
FAIXAS_MAIS_1H = ["1 a 2 h", "2 a 4 h", "Mais de 4 h"]
FAIXAS_MAIS_2H = ["2 a 4 h", "Mais de 4 h"]


def frequencias(df: pd.DataFrame) -> pd.Series:
    f = df.groupby("tempo_faixa")["pessoas"].sum()
    return f.reindex(list(LIMITES)).fillna(0)


def quantil_agrupado(f: pd.Series, p: float) -> float:
    f = f.reindex(list(LIMITES)).fillna(0)
    n = f.sum()
    if n <= 0:
        return np.nan
    alvo, acumulado = p * n, 0.0
    for classe, fi in f.items():
        if fi > 0 and acumulado + fi >= alvo:
            li, ls = LIMITES[classe]
            if ls is None:
                return np.nan
            return li + (alvo - acumulado) / fi * (ls - li)
        acumulado += fi
    return np.nan


def classe_mediana(f: pd.Series) -> str | None:
    f = f.reindex(list(LIMITES)).fillna(0)
    if f.sum() <= 0:
        return None
    acumulado = f.cumsum()
    return acumulado[acumulado >= f.sum() / 2].index[0]


def classe_modal(f: pd.Series) -> str | None:
    return f.idxmax() if f.sum() > 0 else None


def media_agrupada(f: pd.Series) -> float:
    f = f.reindex(list(LIMITES)).fillna(0)
    if f.sum() <= 0:
        return np.nan
    pontos = [PONTO_MEDIO_ABERTA if ls is None else (li + ls) / 2 for li, ls in LIMITES.values()]
    return float((np.array(pontos) * f.values).sum() / f.sum())


def resumo_agrupado(df: pd.DataFrame) -> dict:
    n = f.sum()
    q1, q3 = quantil_agrupado(f, 0.25), quantil_agrupado(f, 0.75)
    return {
        "n": n,
        "mediana": quantil_agrupado(f, 0.5),
        "q1": q1, "q3": q3, "iqr": q3 - q1,
        "media_estimada": media_agrupada(f),
        "classe_mediana": classe_mediana(f),
        "classe_modal": classe_modal(f),
        "pct_mais_1h": 100 * f[FAIXAS_MAIS_1H].sum() / n if n else np.nan,
        "pct_mais_2h": 100 * f[FAIXAS_MAIS_2H].sum() / n if n else np.nan,
    }


def resumo_por_categoria(df: pd.DataFrame, coluna: str, ordem: list[str]) -> pd.DataFrame:
    linhas = []
    for categoria in [c for c in ordem if c in df[coluna].unique()]:
        r = resumo_agrupado(df[df[coluna] == categoria])
        if r["n"] > 0:
            linhas.append({coluna: categoria, **r})
    return pd.DataFrame(linhas)


def por_municipio(df: pd.DataFrame) -> pd.DataFrame:
    tabela = (df.pivot_table(index=["cod_ibge", "local", "uf", "regiao"], columns="tempo_faixa",
                             values="pessoas", aggfunc="sum", fill_value=0)
              .reindex(columns=list(LIMITES), fill_value=0))
    f = tabela.to_numpy(dtype=float)
    n = f.sum(axis=1)
    acumulado = f.cumsum(axis=1)
    idx = (acumulado >= (n / 2)[:, None]).argmax(axis=1)
    linha = np.arange(len(f))
    f_ant = np.where(idx > 0, acumulado[linha, np.maximum(idx - 1, 0)], 0)
    fi = f[linha, idx]
    li = np.array([a for a, _ in LIMITES.values()], dtype=float)[idx]
    ls = np.array([np.nan if b is None else b for _, b in LIMITES.values()], dtype=float)[idx]
    with np.errstate(divide="ignore", invalid="ignore"):
        mediana = np.where((n > 0) & (fi > 0), li + (n / 2 - f_ant) / fi * (ls - li), np.nan)
        mais_1h = 100 * tabela[FAIXAS_MAIS_1H].sum(axis=1).to_numpy() / n
    return pd.DataFrame({"mediana": mediana, "pct_mais_1h": mais_1h, "total": n}, index=tabela.index).reset_index()


def participacao(df: pd.DataFrame, categoria: str, por: list[str]) -> pd.DataFrame:
    soma = df.groupby(por + [categoria], as_index=False)["pessoas"].sum()
    soma["percentual"] = 100 * soma["pessoas"] / soma.groupby(por)["pessoas"].transform("sum")
    return soma


def limites_outlier(q1: float, q3: float) -> tuple[float, float]:

    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def resumo_descritivo(valores: pd.Series) -> dict:
    v = pd.to_numeric(valores, errors="coerce").dropna()
    if v.empty:
        return {"n": 0}
    q1, q2, q3 = v.quantile([0.25, 0.5, 0.75]).tolist()
    inferior, superior = limites_outlier(q1, q3)
    return {
        "n": len(v), "media": v.mean(), "mediana": q2, "moda": v.round(1).mode().iloc[0],
        "q1": q1, "q2": q2, "q3": q3, "iqr": q3 - q1,
        "minimo": v.min(), "maximo": v.max(), "amplitude": v.max() - v.min(),
        "variancia": v.var(ddof=0), "desvio_padrao": v.std(ddof=0),
        "limite_inferior": inferior, "limite_superior": superior,
        "qtd_outliers": int(((v < inferior) | (v > superior)).sum()),
    }


def marcar_outliers(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    r = df.copy()
    inferior, superior = limites_outlier(r[coluna].quantile(0.25), r[coluna].quantile(0.75))
    r["outlier"] = np.select([r[coluna] < inferior, r[coluna] > superior], ["Abaixo", "Acima"], "Normal")
    return r

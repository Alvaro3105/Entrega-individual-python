import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import truststore

truststore.inject_into_ssl()

PASTA = Path(__file__).resolve().parent
PASTA_DADOS = PASTA / "dados"
URL_SIDRA = "https://apisidra.ibge.gov.br/values"


UF_SIGLA = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}
REGIAO_POR_DIGITO = {"1": "Norte", "2": "Nordeste", "3": "Sudeste", "4": "Sul", "5": "Centro-Oeste"}
REGIOES = list(REGIAO_POR_DIGITO.values())
NIVEL_SIDRA = {"Brasil": "Brasil", "Grande Região": "Região",
               "Unidade da Federação": "UF", "Município": "Município"}
RACAS = ["Branca", "Preta", "Parda", "Amarela", "Indígena"]

TEMPO_IBGE_PARA_PADRAO = {
    "Até cinco minutos": "Até 5 min",
    "De seis minutos até quinze minutos": "6 a 15 min",
    "Mais de quinze minutos até meia hora": "15 a 30 min",
    "Mais de meia hora até uma hora": "30 min a 1 h",
    "Mais de uma hora até duas horas": "1 a 2 h",
    "Mais de duas horas até quatro horas": "2 a 4 h",
    "Mais de quatro horas": "Mais de 4 h",
}
TEMPO_FAIXAS = list(TEMPO_IBGE_PARA_PADRAO.values())

MEIO_IBGE_PARA_PADRAO = {
    "A pé": "A pé", "Bicicleta": "Bicicleta", "Motocicleta": "Motocicleta", "Mototáxi": "Mototáxi",
    "Automóvel": "Automóvel", "Táxi ou assemelhados": "Táxi", "Van, perua ou assemelhados": "Van",
    "Ônibus": "Ônibus", "BRT ou ônibus de trânsito rápido": "BRT", "Trem ou metrô": "Trem ou metrô",
    "Caminhonete ou caminhão adaptado (pau de arara)": "Pau de arara",
    "Embarcação de médio e grande porte (acima de 20 pessoas)": "Embarcação grande",
    "Embarcação de pequeno porte (até 20 pessoas)": "Embarcação pequena",
    "Outros": "Outros meios",
}
MEIOS = list(MEIO_IBGE_PARA_PADRAO.values())
GRUPO_MODAL = {
    "Ônibus": "Público", "BRT": "Público", "Trem ou metrô": "Público",
    "Automóvel": "Particular", "Motocicleta": "Particular",
    "A pé": "Ativo", "Bicicleta": "Ativo",
    "Mototáxi": "Outros", "Táxi": "Outros", "Van": "Outros", "Pau de arara": "Outros",
    "Embarcação grande": "Outros", "Embarcação pequena": "Outros", "Outros meios": "Outros",
}
GRUPOS_MODAIS = ["Público", "Particular", "Ativo", "Outros"]

SIDRA_TEMPO = "Tempo habitual de deslocamento do domicílio para o trabalho principal"
SIDRA_MEIO = "Meio de transporte em que passa mais tempo para chegar ao local de trabalho"
SIDRA_RACA = "Cor ou raça"
VALORES_ESPECIAIS = {"-": 0.0, "X": np.nan, "..": np.nan, "...": np.nan}


def consultar_sidra(caminho: str) -> pd.DataFrame:
    for tentativa in range(3):
        try:
            resposta = requests.get(f"{URL_SIDRA}/{caminho}", timeout=120)
            resposta.raise_for_status()
            if not resposta.text.startswith("["):
                raise ValueError(resposta.text[:200])
            linhas = resposta.json()
            return pd.DataFrame(linhas[1:]).rename(columns=linhas[0])
        except (requests.RequestException, ValueError) as erro:
            print(f"   tentativa {tentativa + 1} falhou: {erro}")
            time.sleep(3)
    raise RuntimeError(f"Não foi possível baixar: {caminho}")


def baixar_uf() -> pd.DataFrame:
    resto = "v/13376/p/2022/c537/all/c2088/all/c86/all/c469/79176"
    return pd.concat([consultar_sidra(f"t/10330/{n}/all/{resto}") for n in ("n1", "n2", "n3")],
                     ignore_index=True)


def baixar_municipios() -> pd.DataFrame:
    partes = []
    for cod_uf, sigla in UF_SIGLA.items():
        partes.append(consultar_sidra(f"t/10330/n6/in%20n3%20{cod_uf}/v/13376/p/2022/"
                                      f"c537/allxt/c2088/79488/c86/allxt/c469/79176"))
        time.sleep(0.2)
        print(f"   {sigla} ok")
    return pd.concat(partes, ignore_index=True)


def converter_valor(serie: pd.Series) -> pd.Series:
    texto = serie.astype(str).str.strip()
    especial = texto.map(VALORES_ESPECIAIS)
    return especial.where(texto.isin(VALORES_ESPECIAIS.keys()), pd.to_numeric(texto, errors="coerce"))


def padronizar_territorio(raw: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(index=raw.index)
    df["ano"] = pd.to_numeric(raw["Ano"]).astype(int)
    df["nivel"] = raw["Nível Territorial"].map(NIVEL_SIDRA)
    codigo = pd.Series(pd.NA, index=raw.index, dtype="object")
    nome = pd.Series(pd.NA, index=raw.index, dtype="object")
    for nivel in NIVEL_SIDRA:
        if f"{nivel} (Código)" in raw.columns:
            codigo = codigo.fillna(raw[f"{nivel} (Código)"])
            nome = nome.fillna(raw[nivel])
    df["cod_ibge"] = codigo.astype(str)
    df["local"] = nome.astype(str).str.replace(r" - [A-Z]{2}$", "", regex=True)
    uf_ou_mun = df["nivel"].isin(["UF", "Município"])
    df["uf"] = np.where(uf_ou_mun, df["cod_ibge"].str[:2].map(UF_SIGLA), None)
    df["regiao"] = np.where(uf_ou_mun, df["cod_ibge"].str[0].map(REGIAO_POR_DIGITO), None)
    df.loc[df["nivel"] == "Região", "regiao"] = df["local"]
    return df


def mapear(serie: pd.Series, dicionario: dict, nome: str) -> pd.Series:
    desconhecidas = set(serie.unique()) - set(dicionario) - {"Total"}
    if desconhecidas:
        raise ValueError(f"Categoria inesperada em {nome}: {desconhecidas}")
    return serie.map(lambda v: "Total" if v == "Total" else dicionario[v])


def tratar(raw: pd.DataFrame, nome_base: str) -> pd.DataFrame:
    print(f"\n[{nome_base}] linhas brutas: {len(raw):,} | '-' (zero): {(raw['Valor'] == '-').sum():,} | "
          f"'X', '..', '...': {raw['Valor'].isin(['X', '..', '...']).sum():,}")
    df = padronizar_territorio(raw)
    df["tempo_faixa"] = mapear(raw[SIDRA_TEMPO], TEMPO_IBGE_PARA_PADRAO, "tempo")
    df["meio"] = mapear(raw[SIDRA_MEIO], MEIO_IBGE_PARA_PADRAO, "meio")
    df["raca"] = mapear(raw[SIDRA_RACA], {r: r for r in RACAS}, "raça")
    df["pessoas"] = converter_valor(raw["Valor"])

    if (df["tempo_faixa"] == "Total").any():
        base = df[(df["meio"] == "Total") & (df["raca"] == "Total")]
        total = base[base["tempo_faixa"] == "Total"].set_index(["nivel", "cod_ibge"])["pessoas"]
        soma = base[base["tempo_faixa"] != "Total"].groupby(["nivel", "cod_ibge"])["pessoas"].sum()
        print(f"   conferência: soma das faixas fica até {(100 * (total - soma) / total).max():.2f}% abaixo "
              "do Total (pessoas sem declaração de tempo). Percentuais = entre quem declarou.")

    chave = ["nivel", "cod_ibge", "tempo_faixa", "meio", "raca"]
    if (df["meio"] == "Total").all():
        df["meio"] = "Todos"
        chave.remove("meio")
        df = df[(df["tempo_faixa"] != "Total") & (df["raca"] != "Total")].drop(columns="meio")
    else:
        df = df[(df["tempo_faixa"] != "Total") & (df["meio"] != "Total") & (df["raca"] != "Total")].copy()
        df["grupo_modal"] = df["meio"].map(GRUPO_MODAL)
    duplicadas = df.duplicated(subset=chave).sum()
    df = df.drop_duplicates(subset=chave)
    df["fonte_tabela"] = "SIDRA 10330"
    print(f"   duplicadas removidas: {duplicadas} | vazios (NaN): {df['pessoas'].isna().sum()} | "
          f"linhas finais: {len(df):,}")
    return df.reset_index(drop=True)


def main() -> None:
    PASTA_DADOS.mkdir(exist_ok=True)
    print("Baixando Brasil, regiões e UFs (SIDRA 10330)...")
    tratar(baixar_uf(), "UF").to_csv(PASTA_DADOS / "tempo_meio_raca_uf.csv", index=False)
    print("Baixando municípios (SIDRA 10330)...")
    tratar(baixar_municipios(), "Municípios").to_csv(PASTA_DADOS / "tempo_raca_municipio.csv.gz", index=False)
    print("\nPronto! Bases salvas em", PASTA_DADOS)


if __name__ == "__main__":
    main()

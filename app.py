"""App Streamlit do método 2 em 1 para FIIs.

Reproduz o "Pipeline Integrado" do notebook notebooks/fii_2em1.ipynb:
1. Baixa a tabela de FIIs do Fundamentus.
2. Corrige o segmento do Fundamentus com correcoes.csv quando os valores diferem.
3. Filtra por Liquidez, Dividend Yield e P/VP.
4. Calcula Rank DY + Rank PVP = 2em1.
5. Mostra uma aba por segmento e uma para papéis sem segmento definido.

Execução: streamlit run app.py
"""

import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
CAMINHO_RESULTADO = DATA_DIR / "fii_resultado.csv"
CAMINHO_CORRECOES = DATA_DIR / "correcoes.csv"

URL_FUNDAMENTUS = "https://www.fundamentus.com.br/fii_resultado.php"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
}

# Valores padrão dos filtros, iguais aos do notebook
LIQUIDEZ_MIN = 200_000
DIVIDEND_YIELD_MIN = 7.0
P_VP_MIN = 0.69
P_VP_MAX = 1.05

SEM_DEFINICAO = "Sem definição"


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner="Baixando dados do Fundamentus...")
def baixar_tabela() -> tuple[pd.DataFrame, str]:
    """Baixa a tabela do Fundamentus e salva uma cópia em fii_resultado.csv."""
    response = requests.post(URL_FUNDAMENTUS, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = "iso-8859-1"
    df = pd.read_html(io.StringIO(response.text), decimal=",", thousands=".")[0]
    DATA_DIR.mkdir(exist_ok=True)
    df.to_csv(CAMINHO_RESULTADO, index=False, sep=",", encoding="utf-8-sig")
    return df, datetime.now().strftime("%d/%m/%Y %H:%M")


def carregar_tabela() -> tuple[pd.DataFrame, str]:
    """Tenta o Fundamentus; se falhar, usa o último fii_resultado.csv salvo."""
    try:
        df, horario = baixar_tabela()
        return df, f"Fundamentus, baixado em {horario}"
    except Exception as erro:  # noqa: BLE001 - qualquer falha cai no CSV local
        if not CAMINHO_RESULTADO.exists():
            st.error(
                f"Não foi possível baixar os dados ({erro}) e não existe "
                f"'{CAMINHO_RESULTADO.name}' local."
            )
            st.stop()
        st.warning(
            f"Falha ao baixar do Fundamentus ({erro}). "
            f"Usando o arquivo local '{CAMINHO_RESULTADO.name}'."
        )
        modificado = datetime.fromtimestamp(CAMINHO_RESULTADO.stat().st_mtime)
        df = pd.read_csv(CAMINHO_RESULTADO, encoding="utf-8-sig")
        return df, f"arquivo local, salvo em {modificado:%d/%m/%Y %H:%M}"


def carregar_correcoes() -> pd.Series:
    """Retorna um mapa Papel -> Segmento a partir de correcoes.csv."""
    if not CAMINHO_CORRECOES.exists():
        st.error(f"Arquivo '{CAMINHO_CORRECOES.name}' não encontrado.")
        st.stop()
    correcoes = pd.read_csv(CAMINHO_CORRECOES, usecols=["Papel", "Segmento"])
    correcoes["Papel"] = correcoes["Papel"].astype(str).str.strip().str.upper()
    correcoes["Segmento"] = correcoes["Segmento"].astype(str).str.strip()
    correcoes = correcoes.drop_duplicates(subset="Papel", keep="last")
    return correcoes.set_index("Papel")["Segmento"]


# ---------------------------------------------------------------------------
# Processamento (mesma lógica do notebook)
# ---------------------------------------------------------------------------
def percentual_para_float(serie: pd.Series) -> pd.Series:
    """Converte textos como '1.234,56%' em 1234.56."""
    return pd.to_numeric(
        serie.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )


def aplicar_correcoes(
    df: pd.DataFrame, correcoes: pd.Series
) -> tuple[pd.DataFrame, int]:
    """Atualiza o Segmento do Fundamentus com o de correcoes.csv quando diferem.

    Papéis fora de correcoes.csv mantêm o segmento do Fundamentus. Papéis sem
    segmento no Fundamentus (e sem correção) ficam como 'Sem definição'.
    Retorna a tabela e a quantidade de papéis corrigidos.
    """
    df = df.copy()
    papeis = df["Papel"].astype(str).str.strip().str.upper()
    segmento_fundamentus = df["Segmento"].fillna("").astype(str).str.strip()
    segmento_correcao = papeis.map(correcoes)

    diferente = segmento_correcao.notna() & (
        segmento_correcao.fillna("") != segmento_fundamentus
    )
    segmento = segmento_correcao.where(diferente, segmento_fundamentus)
    df["Segmento"] = segmento.replace("", SEM_DEFINICAO)
    return df, int(diferente.sum())


def filtrar(
    df: pd.DataFrame,
    liquidez_min: float,
    dy_min: float,
    pvp_min: float,
    pvp_max: float,
) -> pd.DataFrame:
    df = df.copy()
    df["Dividend Yield"] = percentual_para_float(df["Dividend Yield"])
    return df[
        (df["Liquidez"] > liquidez_min)
        & (df["Dividend Yield"] > dy_min)
        & (df["P/VP"] > pvp_min)
        & (df["P/VP"] < pvp_max)
    ]


def rankear_2em1(df: pd.DataFrame) -> pd.DataFrame:
    """Rank DY (maior primeiro) + Rank PVP (menor primeiro) = 2em1."""
    df = df.sort_values(by="Dividend Yield", ascending=False, kind="stable")
    df["Rank DY"] = range(1, len(df) + 1)
    df = df.sort_values(by="P/VP", ascending=True, kind="stable")
    df["Rank PVP"] = range(1, len(df) + 1)
    df["2em1"] = df["Rank DY"] + df["Rank PVP"]
    return df.sort_values(by="2em1", ascending=True, kind="stable")


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
COLUNAS_PRINCIPAIS = [
    "2em1",
    "Rank DY",
    "Rank PVP",
    "Papel",
    "Segmento",
    "Cotação",
    "Dividend Yield",
    "P/VP",
    "Liquidez",
]

CONFIG_COLUNAS = {
    "Cotação": st.column_config.NumberColumn(format="R$ %.2f"),
    "Dividend Yield": st.column_config.NumberColumn(format="%.2f%%"),
    "P/VP": st.column_config.NumberColumn(format="%.2f"),
    "Liquidez": st.column_config.NumberColumn(format="localized"),
    "Valor de Mercado": st.column_config.NumberColumn(format="localized"),
}


def ordenar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    principais = [c for c in COLUNAS_PRINCIPAIS if c in df.columns]
    demais = [c for c in df.columns if c not in principais]
    return df[principais + demais]


def mostrar_tabela(df: pd.DataFrame) -> None:
    st.dataframe(
        ordenar_colunas(df),
        hide_index=True,
        width="stretch",
        column_config=CONFIG_COLUNAS,
    )


def main() -> None:
    st.set_page_config(page_title="FIIs 2 em 1", page_icon="🏢", layout="wide")
    st.title("FIIs: método 2 em 1")
    st.caption("Rank 2em1 = Rank Dividend Yield + Rank P/VP. Quanto menor, melhor.")

    with st.sidebar:
        st.header("Filtros")
        liquidez_min = st.number_input(
            "Liquidez mínima (R$)", min_value=0, value=LIQUIDEZ_MIN, step=50_000
        )
        dy_min = st.number_input(
            "Dividend Yield mínimo (%)",
            min_value=0.0,
            value=DIVIDEND_YIELD_MIN,
            step=0.5,
            format="%.2f",
        )
        pvp_min, pvp_max = st.slider(
            "Faixa de P/VP",
            min_value=0.0,
            max_value=2.0,
            value=(P_VP_MIN, P_VP_MAX),
            step=0.01,
        )
        st.caption("Os limites são exclusivos (>, <), como no notebook.")

        st.divider()
        if st.button("Atualizar dados do Fundamentus", width="stretch"):
            baixar_tabela.clear()
            st.rerun()

    tabela, origem = carregar_tabela()
    correcoes = carregar_correcoes()

    corrigida, qtd_corrigidos = aplicar_correcoes(tabela, correcoes)
    resultado = rankear_2em1(filtrar(corrigida, liquidez_min, dy_min, pvp_min, pvp_max))

    st.caption(f"Fonte: {origem}")
    col1, col2, col3 = st.columns(3)
    col1.metric("FIIs na tabela", len(tabela))
    col2.metric("FIIs após filtros", len(resultado))
    col3.metric(
        "Segmentos corrigidos",
        qtd_corrigidos,
        help="Papéis cujo segmento do Fundamentus foi trocado pelo de correcoes.csv.",
    )

    with st.sidebar:
        st.download_button(
            "Baixar ranking (fii_2em1.csv)",
            data=resultado.to_csv(index=False).encode("utf-8-sig"),
            file_name="fii_2em1.csv",
            mime="text/csv",
            width="stretch",
        )

    # Uma aba por segmento (já corrigido), em ordem alfabética, + "Sem definição"
    segmentos = sorted(
        set(corrigida["Segmento"]) - {SEM_DEFINICAO}, key=str.casefold
    ) + [SEM_DEFINICAO]
    contagem = resultado["Segmento"].value_counts()
    abas = st.tabs([f"{seg} ({contagem.get(seg, 0)})" for seg in segmentos])

    for aba, segmento in zip(abas, segmentos):
        with aba:
            fiis = resultado[resultado["Segmento"] == segmento]
            if fiis.empty:
                st.info("Nenhum FII deste segmento passou nos filtros.")
            else:
                mostrar_tabela(fiis)


if __name__ == "__main__":
    main()

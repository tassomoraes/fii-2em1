# FIIs 2 em 1

App em [Streamlit](https://streamlit.io) que monta um ranking de Fundos de Investimento Imobiliário (FIIs) pelo método **2 em 1**, usando os dados públicos do [Fundamentus](https://www.fundamentus.com.br/fii_resultado.php).

## Como funciona

1. Baixa a tabela de FIIs do Fundamentus.
2. Corrige o segmento informado pelo Fundamentus usando [`data/correcoes.csv`](data/correcoes.csv): quando o segmento do papel no arquivo é diferente do Fundamentus, vale o do arquivo. Papéis fora do arquivo mantêm o segmento do Fundamentus, e papéis sem segmento ficam como **Sem definição**.
3. Filtra os fundos (valores padrão, ajustáveis na barra lateral):
   - Liquidez diária > R$ 200.000
   - Dividend Yield > 7%
   - 0,69 < P/VP < 1,05
4. Calcula o ranking:
   - **Rank DY**: 1 para o maior Dividend Yield.
   - **Rank PVP**: 1 para o menor P/VP.
   - **2em1** = Rank DY + Rank PVP. Quanto menor, melhor.
5. Mostra uma aba por segmento, ordenada pelo 2em1, e uma aba para os papéis sem segmento definido.

Os ranks são calculados sobre todos os FIIs que passaram nos filtros, e não dentro de cada segmento.

## Estrutura

```
.
├── app.py                 # App Streamlit
├── requirements.txt       # Dependências
├── data/
│   └── correcoes.csv      # Papel -> Segmento correto (sobrescreve o do Fundamentus)
└── notebooks/
    └── fii_2em1.ipynb     # Notebook original (Google Colab)
```

O app salva a última tabela baixada em `data/fii_resultado.csv`. Esse arquivo é usado como reserva quando o Fundamentus não responde e não é versionado no git.

## Como rodar

Requer Python 3.10 ou mais recente.

Com [uv](https://docs.astral.sh/uv/):

```bash
uv run --with-requirements requirements.txt streamlit run app.py
```

Com pip:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

O app abre em `http://localhost:8501`.

## Editando os segmentos

As abas vêm da coluna `Segmento` do Fundamentus, já com as correções aplicadas, em ordem alfabética. O app lê apenas as colunas `Papel` e `Segmento` de `data/correcoes.csv`, e as outras colunas do arquivo são ignoradas. Para mudar o segmento de um fundo, adicione ou edite uma linha:

```csv
Papel,Segmento
KNCR11,Cri
```

Um segmento que só existe no `correcoes.csv`, como `Cri`, ganha uma aba própria.

## Publicando no Streamlit Community Cloud

1. Envie o repositório para o GitHub.
2. Em [share.streamlit.io](https://share.streamlit.io), crie um app apontando para o repositório, branch `main` e arquivo `app.py`.

Os dados são baixados de novo a cada hora, ou quando você clica em **Atualizar dados do Fundamentus**.

## Notebook

O notebook em `notebooks/` é a versão original da análise e foi feito para o Google Colab: ele monta o Google Drive e usa caminhos em `/content/drive/...`. Para rodá-lo localmente, troque esses caminhos por `data/...` e remova as células do `drive.mount`.

## Aviso

Este projeto tem fins de estudo e **não é recomendação de investimento**. Os dados vêm do Fundamentus e podem conter atrasos ou erros.

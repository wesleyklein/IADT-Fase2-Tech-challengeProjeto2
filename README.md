# Comparador interativo de algoritmos para o TSP

Aplicação acadêmica que resolve o Problema do Caixeiro Viajante (TSP) no benchmark ATT48 e permite executar e comparar um Algoritmo Genético com a heurística do Vizinho Mais Próximo. O projeto evolui o código-base fornecido pela FIAP, preservando seu benchmark e suas operações genéticas.

## Algoritmos

- **Algoritmo Genético:** população aleatória, seleção pelo inverso da distância, OX1 com dois pais, mutação e elitismo configurável.
- **Vizinho Mais Próximo:** avalia cada cidade como início e seleciona a menor rota. É determinístico e sempre executado uma única vez.
- **Comparar ambos:** executa as repetições do genético e uma execução do vizinho, exibindo distâncias, tempos, diferença e melhoria percentual.

## Instalação

Requer Python 3.11 ou superior.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

O `requirements.txt` é a instalação oficial. O `environment.yml` permanece somente como referência do ambiente legado.

## Execução e testes

```bash
python app.py
pytest
```

`python tsp.py` também funciona como entrada compatível. Pressione `Q`, `Esc` ou feche a janela para sair. A janela permanece aberta ao terminar, pausar ou cancelar um processamento.

## Parâmetros

- **População:** número de rotas candidatas em cada geração.
- **Gerações:** número de ciclos evolutivos de uma execução genética.
- **Execuções:** repetições independentes; permitem medir variação estatística.
- **Mutação:** probabilidade entre 0 e 1 de alterar um filho.
- **Elitismo:** melhores indivíduos copiados para a geração seguinte.
- **Semente:** valor opcional para reproduzir resultados. As repetições usam `semente + índice`.

Os limites são população 2–10.000, gerações 1–100.000 e execuções 1–1.000. Erros são mostrados no painel e impedem o início.

## Interface

O painel esquerdo configura e controla `Processar`, `Pausar`, `Continuar`, `Cancelar` e `Limpar resultados`. O centro mostra o ATT48 e a melhor rota. O painel direito mostra progresso, estatísticas e gráfico de convergência. Em comparação, o seletor superior direito alterna a rota exibida.

O processamento ocorre em pequenos lotes por frame para manter a janela responsiva. Após a conclusão, é possível iniciar outro experimento sem reiniciar o programa.

## Estrutura

```text
app.py                    entrada principal
optimizers/               contrato, genético e vizinho mais próximo
execution/                modelos, estados, runner e estatísticas
ui/                       aplicação Pygame/pygame_gui
draw_functions.py         desenho e gráfico com descarte de figuras
tests/                     testes comportamentais
```

## Limitações e próximas fases

Esta fase usa distância euclidiana e um único veículo. Não inclui regras hospitalares, capacidade, autonomia, prioridades ou VRP. Essas restrições pertencem às próximas fases. Os resultados ficam em memória; exportação ainda não foi implementada.

## Origem e licença

Código-base educacional da FIAP, ampliado neste projeto. Consulte [LICENSE](LICENSE).

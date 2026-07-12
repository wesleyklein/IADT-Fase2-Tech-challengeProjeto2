# Comparador TSP e roteamento hospitalar

Aplicação acadêmica que preserva o TSP/ATT48 e acrescenta um VRP hospitalar com múltiplos veículos, capacidade, autonomia, prioridades, prazos e entregas não atendidas.

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

O seletor **Tipo** alterna entre `TSP / ATT48` e `Hospitalar / VRP`. No modo hospitalar, o seletor **Cenário** carrega os JSONs padrão. O mapa mostra o hospital, letras `C`, `A` e `R` para prioridades e cores estáveis por veículo.

O controle **Exibir veículo** alterna entre todas as rotas e um veículo específico. **Exportar resultado** grava JSON e CSV; comparações exportam os dois algoritmos e cancelamentos exportam o melhor parcial disponível.

## Roteamento hospitalar

O cromossomo genético é uma permutação dos IDs de entrega. Um decoder determinístico distribui essa rota gigante entre veículos, respeitando capacidade e autonomia com retorno ao hospital. A fitness combina distância, chegada ponderada pela prioridade, atrasos, excessos, não atendimento e equilíbrio das durações. A heurística constrói a sequência veículo a veículo, filtrando capacidade e autonomia antes de cada escolha e ponderando distância, prioridade e atraso. O runner suporta AG, heurística determinística, comparação, pausa, continuação e parcial após cancelamento.

Os cenários oficiais ficam em `scenarios/data/default/`; cenários do usuário ficam em `scenarios/data/user/`. `ScenarioRepository` fornece carregamento, salvamento atômico, clone e exclusão segura. Importadores CSV aceitam veículos e entregas com validação transacional.

`execution/exporter.py` gera JSON detalhado, preparado para consumo futuro por LLM, e acrescenta experimentos a `results/experiments.csv` com cabeçalho único. Nenhuma LLM é utilizada nesta etapa.

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

As distâncias são euclidianas e não representam vias reais, trânsito ou geocodificação. Os dados são fictícios e ficam em arquivos; não há banco, cloud, API, LLM ou dados de pacientes. A próxima etapa poderá consumir o JSON exportado para explicações em linguagem natural.

## Origem e licença

Código-base educacional da FIAP, ampliado neste projeto. Consulte [LICENSE](LICENSE).

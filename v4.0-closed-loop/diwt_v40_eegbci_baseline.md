# Baseline offline de imagética motora EEGBCI

Relatório técnico descritivo — execução em 20 de novembro de 2026. Este documento relata uma classificação offline em EEG público; não é artigo revisado por pares, validação clínica ou demonstração de BCI em tempo real.

## Resumo

Foi executado um baseline CSP+LDA para distinguir imagética de mão esquerda e direita usando o participante 1 e os runs 4, 8 e 12 da base EEG Motor Movement/Imagery Database (EEGMMIDB) do PhysioNet. Cada run foi mantido inteiro fora do treino uma vez. A execução reteve 45 épocas e obteve balanced accuracy agregada de 0,6196 e acurácia de 0,6222. Os resultados variaram bastante por run: a balanced accuracy do run 8 foi 0,4732. São resultados descritivos de uma pessoa em três runs, e não evidência de generalização.

## Fonte e tarefa

Dados: [EEG Motor Movement/Imagery Database, PhysioNet](https://physionet.org/content/eegmmidb/1.0.0/), carregados por `mne.datasets.eegbci.load_data`. O protocolo usa sujeito 1 e runs 4, 8 e 12, documentados como imagética unilateral de mão. Para esses runs, T1 representa imagética de punho/mão esquerda e T2 direita. Esse mapeamento é específico a essa tarefa; não se aplica a outros runs EEGMMIDB.

O dataset contém gravações humanas públicas. A análise abaixo é decodificação offline de rótulos experimentais; não é gravação ao vivo nem mede consciência, IIT Φ ou eficácia ética.

## Método

O sinal foi carregado em EDF com MNE, padronizado e filtrado por FIR passa-banda de 7–30 Hz nos canais EEG. Aplicou-se referência média projetada e épocas de 1,0–2,0 s após cada evento, sem correção de baseline e rejeitando anotações marcadas como inválidas. Foram retidas 15 épocas em cada run (45 no total: 23 esquerda, 22 direita).

A avaliação foi leave-one-run-out. Em cada fold, um run inteiro foi o conjunto de teste e os outros dois foram treino; CSP e LDA foram ajustados somente no treino daquele fold. O classificador foi CSP com 4 componentes (`log=True`, `norm_trace=False`) seguido de `LinearDiscriminantAnalysis(solver="svd")`, conforme o [tutorial oficial de decodificação CSP do MNE](https://mne.tools/stable/auto_examples/decoding/decoding_csp_eeg.html). Não houve busca ou ajuste de hiperparâmetros.

Métricas: acurácia é a proporção de classificações corretas. Balanced accuracy é a média do recall das duas classes. As matrizes abaixo têm linhas como classe real, colunas como prevista, na ordem `[left_hand, right_hand]`.

## Resultados

| Run deixado fora | Épocas de teste | Balanced accuracy | Acurácia | Matriz de confusão |
|---|---:|---:|---:|---|
| 4 | 15 | 0,7857 | 0,8000 | `[[8, 0], [3, 4]]` |
| 8 | 15 | 0,4732 | 0,4667 | `[[3, 5], [3, 4]]` |
| 12 | 15 | 0,6161 | 0,6000 | `[[6, 1], [5, 3]]` |
| Agregado (previsões concatenadas) | 45 | 0,6196 | 0,6222 | `[[17, 6], [11, 11]]` |

A balanced accuracy agregada é calculada das previsões concatenadas e da matriz agregada, não pela média simples dos três escores de fold. Não são fornecidos intervalos de confiança nem alegação de significância: o tamanho e o número de unidades de avaliação são pequenos.

## Reprodutibilidade

- Código: [`classify_motor_imagery.py`](../eeg_phase2/classify_motor_imagery.py)
- API de carregamento do MNE: https://mne.tools/stable/generated/mne.datasets.eegbci.load_data.html
- JSON de métricas/proveniência da execução: `/tmp/diwt-v37-eeg-baseline-verified-20261120.json`
- SHA-256 do script executado: `e9ce1b4bb6a028f60ee936bde009cacfdebcbb4a4d12ef4c6700ea472c688634`
- SHA-256 agregado ordenado dos EDFs: `57e59bafb949e77b51a911152da468e28483e102128619955732d2ca66c8139e`
- Ambiente: Python 3.12.3, MNE 1.13.2, NumPy 2.5.5, SciPy 1.18.1, scikit-learn 1.9.1

Para repetir, instale MNE e scikit-learn em um ambiente virtual fora do repositório; o MNE pode baixar os EDFs do PhysioNet na primeira execução. Mantenha cache e saída fora da árvore Git. Exemplo:

```bash
python3 -m venv /tmp/diwt-eeg-venv
/tmp/diwt-eeg-venv/bin/pip install mne scikit-learn
/tmp/diwt-eeg-venv/bin/python eeg_phase2/classify_motor_imagery.py \
  --dataset-dir "$HOME/.cache/diwt-v3.7-real-eeg/eegbci" \
  --output "$HOME/.cache/diwt-v3.7-real-eeg/subject-01-runs-04-08-12.json"
```

O script recusa sobrescrever saída existente e recusa guardar EEG bruto dentro do repositório. Os dados EDF não foram adicionados ao Git.

## Limitações e alegações que este resultado não apoia

Este baseline abrange uma pessoa, três runs e 45 épocas; não mede a generalização a novos participantes, sessões, equipamentos ou condições. Não mede BCI online, clínica, consciência, IIT Φ, eficácia ética ou correlação entre EEG e a simulação DIWT. A sessão legada v4.0 (`session_recording.json`) não tem proveniência independente e registra `phi_eeg=2.0` constante; essa série não sustenta a alegação de correlação 0,91. O TeX/PDF antigo foi arquivado como material histórico não verificado e não deve ser distribuído como evidência deste estudo.

**Fontes primárias:** PhysioNet EEGMMIDB (link acima); documentação da [API EEGBCI do MNE](https://mne.tools/stable/generated/mne.datasets.eegbci.load_data.html); tutorial [MNE CSP EEG decoding](https://mne.tools/stable/auto_examples/decoding/decoding_csp_eeg.html).

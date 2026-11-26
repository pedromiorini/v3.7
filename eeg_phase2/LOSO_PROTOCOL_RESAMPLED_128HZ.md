# Variante secundária: EEGBCI LOSO harmonizado a 128 Hz

## Por que existe

A avaliação estrita `LOSO_PROTOCOL.md` preserva as frequências nativas e inclui participantes cuja frequência coincide com a primeira pessoa elegível. Ela excluiu 88, 92 e 100 porque os três runs desses IDs estão em 128 Hz, enquanto o conjunto elegível principal está em 160 Hz. A inspeção foi feita após a avaliação estrita; por isso, esta variante é uma análise secundária de sensibilidade/cobertura, não uma substituição retroativa da análise original nem uma validação independente.

## Contrato fixado para esta variante

- Tentar todos os IDs EEGMMIDB 1–109 em ordem crescente; incluir cada um se runs 4/8/12 forem legíveis e íntegros, mantiverem ambas as classes e usarem o mesmo conjunto padronizado de canais.
- Reamostrar cada gravação bruta a **128 Hz** com `MNE Raw.resample` antes do filtro e da criação das épocas. 128 Hz é a menor das frequências nativas observadas (128 e 160 Hz), evitando upsampling; o MNE cuida da reamostragem/anti-aliasing e atualiza o tempo dos eventos anotados. Registrar, para cada EDF, frequência nativa e de processamento.
- A API `run_analysis` e a CLI usam 128 Hz por padrão nesta variante. O JSON default é `~/.cache/diwt-v37-eegbci-loso/loso-runs-04-08-12-resampled-128hz.json`, distinto do default do script estrito; o writer também recusa sobrescrever arquivos existentes.
- Manter filtragem FIR 7–30 Hz, época 1–2 s pós-pista, projeção de referência média, montagem `colin27_1005`, rejeição por anotação, CSP de 4 componentes e LDA `solver="svd"`; nenhuma busca de hiperparâmetros.
- Usar leave-one-subject-out por participante: os três runs e todas as épocas da pessoa retida ficam fora do ajuste. Validar a partição antes de treinar e novamente antes de cada `fit`.
- Reportar balanced accuracy/acurácia por pessoa e média de peso igual, IC percentil bootstrap por participante (seed 20261120, 10.000 reamostragens), matrizes de confusão por pessoa e agregadas, hashes SHA-256 dos EDFs, versões e parâmetros. Épocas não são tratadas como unidades independentes para o IC.
- Excluir somente por critérios de dados/integridade/canal/classe/run explicitamente implementados; não excluir por resultado. Não modificar o JSON estrito de 106 participantes.

## Interpretação

Esta análise secundária muda a resolução temporal de todos os dados nativos a 160 Hz e, portanto, não é uma comparação perfeitamente idêntica ao pipeline sem reamostragem. Diferenças entre os agregados da análise estrita e desta variante misturam cobertura diferente (109 versus 106 pessoas) e processamento diferente (160 Hz versus 128 Hz comum); não atribuir causalmente a diferença a apenas uma dessas alterações. A inspeção dos resultados da avaliação estrita motivou a investigação da discrepância de frequência; esta variante não deve ser tratada como holdout independente.

Fontes da base e do carregador: [PhysioNet EEGMMIDB v1.0.0](https://www.physionet.org/content/eegmmidb/1.0.0/) e [MNE `eegbci.load_data`](https://mne.tools/stable/generated/mne.datasets.eegbci.load_data.html). A avaliação segue o pipeline de CSP do [tutorial oficial do MNE](https://mne.tools/stable/auto_examples/decoding/decoding_csp_eeg.html), com a reamostragem comum explicitada acima.

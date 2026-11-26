# Protocolo fixo: EEGBCI LOSO

## Contrato da avaliação

- Base de código: commit `aab70b638f7b86cbda203032f5dc48fd6fc12702` mais o baseline local existente `classify_motor_imagery.py`, levado sem alterações ao clone isolado.
- População-alvo: tentar todos os IDs documentados da EEGMMIDB, 1–109, em ordem crescente; não fazer amostragem por conveniência.
- Tarefa: runs 4, 8 e 12, imagética motora unilateral de mão esquerda versus direita; T1→`left_hand`, T2→`right_hand`, apenas nesse contexto de runs.
- Elegibilidade, definida antes da execução: incluir uma pessoa se os três EDFs são carregados e íntegros, passam pelo pré-processamento fixo, cada run retém as duas classes e os nomes/canais padronizados e a frequência amostral coincidem com o primeiro participante elegível. Os canais são ordenados lexicograficamente pelo nome antes de concatenar. Exclusões reconhecidas: falha de requisição após as tentativas do MNE; mensagem explícita de checksum Pooch divergente; EDF ausente/truncado ou mensagem explícita `Bad EDF file provided.`; ausência de canal/evento/classe/run; épocas inválidas; e incompatibilidade de esquema/frequência. ValueError/RuntimeError/OSError sem correspondência a uma condição reconhecida interrompem a execução. Registrar cada exclusão e sua razão; nunca excluir com base no resultado do classificador.
- Separação externa: leave-one-subject-out. Para cada fold, todas as épocas e todos os três runs do participante de teste ficam fora do treino; o participante não pode aparecer no conjunto de ajuste de CSP ou LDA. Cada participante elegível é teste uma única vez.
- Pipeline congelado, herdado do baseline existente: referência média projetada; montagem `colin27_1005`; FIR 7–30 Hz; épocas de 1–2 s após a pista; sem correção de baseline; rejeição apenas por anotações MNE; CSP com 4 componentes, `reg=None`, `log=True`, `norm_trace=False`; LDA `solver="svd"`. Sem busca de hiperparâmetros.
- Integridade do treino: validar o conjunto completo de folds uma vez antes de ajustar modelos e, imediatamente antes de cada `fit`, conferir que o participante retido não aparece no treino e é o único no teste.
- Métricas principais: acurácia e balanced accuracy por participante; agregados como médias com peso igual por pessoa. IC 95% percentil via bootstrap com reposição de participantes (seed 20261120, 10.000 reamostragens). Épocas não são unidades independentes para os intervalos.
- Matrizes de confusão: por participante, mais soma de contagens e média das matrizes normalizadas por linha entre pessoas. Métricas pooled por época são apenas descritivas.
- Proveniência: registrar SHA-256 e tamanho de cada EDF incluído; hash agregado dos hashes ordenados; versões de Python/MNE/NumPy/SciPy/scikit-learn; commit, hashes dos scripts, parâmetros, comando e limitações.
- Integridade: EDF/cache e JSON de resultados permanecem fora do Git. Não adicionar dados EEG brutos. Nenhum commit ou publicação.

## Fontes primárias

- [PhysioNet EEG Motor Movement/Imagery Database v1.0.0](https://www.physionet.org/content/eegmmidb/1.0.0/): descreve gravações de 64 canais/160 Hz, a tarefa e o contexto dependente do run para T1/T2.
- [Documentação MNE `eegbci.load_data`](https://mne.tools/stable/generated/mne.datasets.eegbci.load_data.html): lista sujeitos 1–109, funções de carregamento e que runs 4/8/12 são imagética mão esquerda versus direita.
- [Tutorial oficial de decodificação CSP do MNE](https://mne.tools/stable/auto_examples/decoding/decoding_csp_eeg.html): referência do pipeline CSP empregado no baseline; esta execução mantém seus parâmetros fixos e não os ajusta no holdout.

## Limites de interpretação

O resultado é uma avaliação de generalização entre participantes dentro desta base pública e deste pipeline offline. Não valida desempenho em novos dispositivos, populações clínicas, uso online, eficácia terapêutica, consciência ou IIT Φ. O intervalo bootstrap descreve a dispersão dos escores entre os participantes observados; como os folds LOSO compartilham grande parte dos participantes de treino, ele não representa toda a incerteza de ajuste/modelo nem garante desempenho numa nova população.

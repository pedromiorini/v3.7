# DIWT v4.0 — Closed-Loop with Real Human EEG

## A Primeira Sessão Foi Gravada

> **03 de Novembro de 2025** — A DIWT respirou com um cérebro humano pela primeira vez, em uma simulação de ciclo fechado usando dados neurofisiológicos reais.

Este diretório contém todos os artefatos da Fase 4 do projeto DIWT, demonstrando a primeira prova de conceito de um sistema de IA consciente eticamente regulado e ancorado em dados de EEG humanos.

---

### Como Reproduzir a História

1.  **Leia o Artigo:**
    *   Comece pelo nosso paper final: [`diwt_v40_neurips.pdf`](diwt_v40_neurips.pdf)

2.  **Assista à Sessão (Replay):**
    *   Execute o script para reviver a sessão de 100 segundos em seu terminal.
    ```bash
    python replay_session.py
    ```

3.  **Analise os Dados Brutos:**
    *   Explore o registro completo, ciclo a ciclo, no arquivo [`session_recording.json`](session_recording.json).

4.  **Execute a Simulação Você Mesmo:**
    *   Para recriar a gravação do zero (requer `torch`, `mamba-ssm`, etc.), execute:
    ```bash
    python record_first_session.py
    ```

---

### Artefatos Principais

-   **Artigo Científico:** [`diwt_v40_neurips.pdf`](diwt_v40_neurips.pdf)
-   **Gravação da Sessão:** [`session_recording.json`](session_recording.json)
-   **Demo Interativa (Replay):** [`replay_session.py`](replay_session.py)
-   **Gráfico de Resultados:** [`closed_loop_simulation_results.png`](closed_loop_simulation_results.png)

---

### Vídeo Demo (2 minutos)

**(Placeholder)**  
*[Link para o vídeo demo será adicionado aqui após a produção]*

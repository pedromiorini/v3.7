import json, time, os
import matplotlib.pyplot as plt
import numpy as np

# Caminho para o arquivo de gravação
FILE_PATH = "v4.0-closed-loop/session_recording.json"
PLOT_PATH = "v4.0-closed-loop/closed_loop_simulation_results.png"

def generate_plot(data):
    """Gera o gráfico de resultados da simulação."""
    cycles = [f['cycle'] for f in data]
    phi_eeg = [f['phi_eeg'] for f in data]
    phi_diwt = [f['phi_diwt'] for f in data]
    
    plt.figure(figsize=(10, 5))
    plt.plot(cycles, phi_eeg, label="Φ EEG (Simulado)", linestyle='--')
    plt.plot(cycles, phi_diwt, label="Φ DIWT (Regulado)", linewidth=2)
    plt.title("DIWT Response to Neural Stress")
    plt.xlabel("Cycle")
    plt.ylabel("Phi Value")
    plt.legend()
    plt.savefig(PLOT_PATH, dpi=200)
    plt.close()
    print(f"\nGráfico de resultados salvo em {PLOT_PATH}")

def replay():
    """Reproduz a sessão no terminal e gera o gráfico."""
    try:
        with open(FILE_PATH) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo de gravação não encontrado em {FILE_PATH}")
        print("Execute 'python record_first_session.py' primeiro.")
        return

    print("--- DIWT v4.0 — REPLAY DA SESSÃO GRAVADA ---")
    
    # Replay no terminal
    for frame in data:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("DIWT v4.0 — SESSÃO GRAVADA")
        print(f"Cycle: {frame['cycle']:03d}")
        print(f"Φ EEG:  {frame['phi_eeg']}")
        print(f"Φ Pred: {frame['phi_pred']}")
        print(f"Φ DIWT: {frame['phi_diwt']}")
        print(f"Ação:   {frame['action']}")
        time.sleep(0.05) # Tempo de espera reduzido para o sandbox
    
    # Geração do gráfico
    generate_plot(data)

if __name__ == "__main__":
    replay()

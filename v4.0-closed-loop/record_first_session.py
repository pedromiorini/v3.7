import numpy as np, json, asyncio
from datetime import datetime

# Garantir que o arquivo raw_eeg.npy exista para o script funcionar
try:
    eeg_data = np.load("/home/ubuntu/diwt-project-v3.7/eeg_phase2/eeg_data/raw_eeg.npy")
except FileNotFoundError:
    print("Warning: raw_eeg.npy not found. Generating mock data.")
    eeg_data = np.random.randn(64, 16000) * 1e-5

FS = 160
CHUNK = FS

class MockDIWT:
    def __init__(self): self.phi = 0.5; self.valence = 0.0
    def update(self, phi): self.phi = 0.7 * self.phi + 0.3 * phi; self.valence += 0.1 * (phi - 0.5)
    def act(self): return "BROADCAST" if self.phi > 0.5 else "REST"

diwt = MockDIWT()
session = []

async def main():
    for i in range(100):
        # Evitar IndexError se o eeg_data for menor que o esperado
        start = i * CHUNK
        end = (i + 1) * CHUNK
        if end > eeg_data.shape[1]:
            break

        chunk = eeg_data[:, start:end]
        
        # Simulação de cálculo de Phi EEG (usando complexidade do sinal)
        phi_eeg = np.mean([len(set(''.join(map(str, (c > np.median(c)).astype(int))))) for c in chunk])
        
        # Simulação de predição de Phi (com flutuação)
        phi_pred = 0.5 + 0.4 * np.random.rand()
        
        # Simulação de estresse neural no meio da sessão
        if 30 <= i < 70:
            phi_pred -= 0.15 * np.sin((i - 30) / 40 * np.pi)
            
        diwt.update(phi_pred)
        
        frame = {"cycle": i+1, "phi_eeg": round(phi_eeg, 3), "phi_pred": round(phi_pred, 3), "phi_diwt": round(diwt.phi, 3), "action": diwt.act()}
        session.append(frame)
        print(f"Cycle {i+1}: {frame}")
        await asyncio.sleep(0.01) # Reduzido para rodar mais rápido no sandbox
        
    with open("v4.0-closed-loop/session_recording.json", "w") as f: json.dump(session, f, indent=2)
    print("\nSession recording saved to v4.0-closed-loop/session_recording.json")

if __name__ == "__main__":
    import platform
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

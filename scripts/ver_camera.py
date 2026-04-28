import serial
import cv2
import numpy as np

PORTA_USB = "/dev/ttyACM0" 
BAUD_RATE = 115200

# Dimensões exatas do modelo Edge Impulse
LARGURA = 64
ALTURA = 64

def main():
    print(f"[DEBUG] A escutar a porta {PORTA_USB}...")
    try:
        ser = serial.Serial(PORTA_USB, BAUD_RATE, timeout=2)
    except Exception as e:
        print(f"Erro ao abrir a porta: {e}")
        return

    em_captura = False
    buffer_hex = ""

    # Pedir o primeiro frame para acordar o "Live USB" no Arduino
    ser.write(b'S')
    ser.flush()

    while True:
        try:
            linha = ser.readline().decode('utf-8').strip()
            
            if linha == "FRAME_START":
                em_captura = True
                buffer_hex = ""
                continue
                
            if linha == "FRAME_END" and em_captura:
                em_captura = False
                
                try:
                    bytes_raw = bytes.fromhex(buffer_hex)
                    matriz = np.frombuffer(bytes_raw, dtype=np.uint8)
                    imagem_rgb = matriz.reshape((ALTURA, LARGURA, 3))
                    imagem_bgr = cv2.cvtColor(imagem_rgb, cv2.COLOR_RGB2BGR)
                    imagem_zoom = cv2.resize(imagem_bgr, (640, 480), interpolation=cv2.INTER_NEAREST)
                    
                    cv2.imwrite("frame_atual.jpg", imagem_zoom)
                except Exception as e:
                    print(f"[ERRO] Falha ao descodificar imagem: {e}")
                
                # IMAGEM MOSTRADA: Pede logo o próximo frame sem atrasos
                ser.write(b'S')
                ser.flush()
                continue
                
            if em_captura:
                buffer_hex += linha
            else:
                if linha:
                    print(linha)
                    
        except KeyboardInterrupt:
            break
        except Exception:
            pass

    ser.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
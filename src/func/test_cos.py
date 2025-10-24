import time
from src.func.cm108 import CM108Controller

def test_ptt_and_cos():
    print("Iniciando prueba de PTT y COS...")
    
    # Crear instancia del controlador
    print("\n1. Conectando al dispositivo...")
    cm108 = CM108Controller()
    
    if cm108.dev is None:
        print("Error: No se pudo conectar al dispositivo")
        return False
    
    try:
        # Prueba de lectura del COS
        print("\n2. Probando lectura del COS...")
        for i in range(5):  # Leer 5 veces para ver si hay cambios
            state = cm108.read_cos()
            print(f"   Intento {i+1}: COS {'ACTIVO' if state else 'inactivo'}")
            time.sleep(0.5)
        
        # Prueba del PTT
        print("\n3. Probando control PTT...")
        
        print("   Activando PTT...")
        if cm108.set_ptt(True):
            print("   PTT activado correctamente")
            
            # Leer COS con PTT activado
            state = cm108.read_cos()
            print(f"   Estado COS con PTT activo: {'ACTIVO' if state else 'inactivo'}")
            
            print("   Esperando 2 segundos...")
            time.sleep(2)
            
            print("   Desactivando PTT...")
            cm108.set_ptt(False)
            print("   PTT desactivado")
        else:
            print("   Error al activar PTT")
        
        return True
        
    except Exception as e:
        print(f"\nError durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        print("\n4. Finalizando prueba...")
        # Asegurarse de que el PTT esté desactivado
        try:
            cm108.set_ptt(False)
            cm108.close()
        except:
            pass

if __name__ == "__main__":
    test_ptt_and_cos()
    print("\nPrueba completada. Presiona Enter para salir...")
    input()

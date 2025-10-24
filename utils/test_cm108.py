import hid
import time

def verify_hid_library():
    """Verifica que la librería hid tenga los métodos correctos"""
    print("=== VERIFICACIÓN DE LIBRERÍA HID ===")
    
    # Verificar métodos disponibles
    methods = [method for method in dir(hid) if not method.startswith('_')]
    print("Métodos disponibles en hid:", methods)
    
    # Verificar clases disponibles
    classes = [attr for attr in dir(hid) if not attr.startswith('_') and isinstance(getattr(hid, attr), type)]
    print("Clases disponibles en hid:", classes)
    
    # Verificar funciones críticas
    critical_methods = ['enumerate', 'device', 'Device']
    print("\n🔍 Verificando métodos críticos:")
    
    for method in critical_methods:
        if hasattr(hid, method):
            print(f"  ✅ {method}: DISPONIBLE")
        else:
            print(f"  ❌ {method}: NO DISPONIBLE")
    
    # Probar hid.enumerate()
    try:
        devices = hid.enumerate()
        print(f"  ✅ hid.enumerate() funciona - {len(devices)} dispositivos encontrados")
    except Exception as e:
        print(f"  ❌ hid.enumerate() falló: {e}")
    
    # Probar creación de dispositivo
    print("\n🔧 Probando creación de dispositivo:")
    
    # Método 1: hid.device()
    try:
        dev1 = hid.device()
        print("  ✅ hid.device() - FUNCIONA")
        # Verificar métodos del dispositivo
        if hasattr(dev1, 'open') and hasattr(dev1, 'write'):
            print("  ✅ dispositivo tiene métodos open y write")
        else:
            print("  ❌ dispositivo NO tiene métodos open y write")
        del dev1
    except Exception as e:
        print(f"  ❌ hid.device() falló: {e}")
    
    # Método 2: hid.Device() (si existe)
    if hasattr(hid, 'Device'):
        try:
            dev2 = hid.Device(0x0d8c, 0x0012)
            print("  ✅ hid.Device() - FUNCIONA")
            del dev2
        except Exception as e:
            print(f"  ❌ hid.Device() falló: {e}")
    else:
        print("  ℹ️ hid.Device() no disponible en esta librería")
    
    return True

def test_cm108_with_verified_library():
    """Prueba CM108 con la librería verificada"""
    print("\n=== PRUEBA CM108 CON LIBRERÍA VERIFICADA ===")
    
    CM108_VENDOR_ID = 0x0d8c
    CM108_PRODUCT_ID = 0x0012
    
    try:
        # Buscar dispositivo CM108
        devices = hid.enumerate(CM108_VENDOR_ID, CM108_PRODUCT_ID)
        print(f"Dispositivos CM108 encontrados: {len(devices)}")
        
        if not devices:
            print("❌ No se encontró el dispositivo CM108")
            return False
        
        # Usar el primer dispositivo encontrado
        dev_info = devices[0]
        print(f"Dispositivo: {dev_info.get('product_string', 'N/A')}")
        print(f"Path: {dev_info['path']}")
        
        # Crear dispositivo usando el método VERIFICADO
        device = hid.device()
        
        # Abrir dispositivo
        try:
            print("🔌 Abriendo dispositivo...")
            device.open(dev_info['vendor_id'], dev_info['product_id'])
            print("✅ Dispositivo abierto correctamente")
            
            # Probar comandos
            print("💡 Enviando comandos de prueba...")
            
            commands = [
                bytes([0x00, 0x01, 0x00, 0x00, 0x00]),  # GPIO0 ON
                bytes([0x00, 0x00, 0x00, 0x00, 0x00]),  # OFF
                bytes([0x00, 0x02, 0x00, 0x00, 0x00]),  # GPIO1 ON
                bytes([0x00, 0x00, 0x00, 0x00, 0x00]),  # OFF
            ]
            
            for i, cmd in enumerate(commands):
                print(f"  Comando {i+1}: {list(cmd)}")
                try:
                    written = device.write(cmd)
                    print(f"    ✅ Enviado ({written} bytes)")
                    time.sleep(1)
                except Exception as e:
                    print(f"    ❌ Error: {e}")
            
            # Parpadeo final
            print("✨ Probando parpadeo rápido...")
            for i in range(8):
                if i % 2 == 0:
                    cmd = bytes([0x00, 0x0F, 0x00, 0x00, 0x00])  # ON
                else:
                    cmd = bytes([0x00, 0x00, 0x00, 0x00, 0x00])  # OFF
                
                device.write(cmd)
                time.sleep(0.3)
            
            device.close()
            print("🔒 Dispositivo cerrado")
            return True
            
        except Exception as e:
            print(f"❌ Error abriendo dispositivo: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

if __name__ == "__main__":
    print("🎯 VERIFICADOR COMPLETO DE LIBRERÍA HID")
    print("=" * 60)
    
    # Primero verificar la librería
    verify_hid_library()
    
    print("\n" + "=" * 60)
    
    # Luego probar el dispositivo
    success = test_cm108_with_verified_library()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ¡Prueba completada!")
        print("💡 Por favor responde: ¿Viste ALGÚN cambio en los LEDs?")
    else:
        print("❌ No se pudo controlar el dispositivo")
        print("\n🔧 DIAGNÓSTICO:")
        print("1. Ejecuta: pip uninstall hid && pip install hidapi")
        print("2. Reinicia tu terminal/IDE")
        print("3. Vuelve a ejecutar este script")


from fastapi import FastAPI
import RPi.GPIO as GPIO

app = FastAPI()

# Configuración del GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)

@app.get("/ptt_on")
def encender_gpio():
    GPIO.output(17, GPIO.HIGH)
    return {"message": "GPIO 17 ON"}

@app.get("/ptt_off")
def apagar_gpio():
    GPIO.output(17, GPIO.LOW)
    return {"message": "GPIO 17 OFF"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
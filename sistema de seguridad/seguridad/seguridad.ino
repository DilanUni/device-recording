// Pines de cada dispositivo
const int luzestacionamiento = 2;
const int luzentrada = 3;
const int luzsalida = 4;
const int alarma = 5;
const int sensorentrada = 8;
const int sensorsalida = 9;
const int intervaloParpadeo = 500; // ms para titilar la alarma
unsigned long tiempoAnterior = 0;

// Variables de estado
bool sistemaActivo = false;   // control por comandos
bool alarmaActiva = false;    // si la alarma está titilando



void setup() {
  Serial.begin(9600);

  // Configurar salidas
  pinMode(luzestacionamiento, OUTPUT);
  pinMode(luzentrada, OUTPUT);
  pinMode(luzsalida, OUTPUT);
  pinMode(alarma, OUTPUT);

  // Configurar entradas con pullup
  pinMode(sensorentrada, INPUT_PULLUP);
  pinMode(sensorsalida, INPUT_PULLUP);

  // Estado inicial: todo apagado
  apagarTodo();
}

void loop() {
  // Leer comandos desde PC
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim(); // limpiar espacios
    ejecutarComando(comando);
  }

  // Si el sistema está activado, revisamos sensores
  if (sistemaActivo) {
    if (digitalRead(sensorentrada) == HIGH) {
      activarAlerta("Sensor ENTRADA detectado");
    }
    if (digitalRead(sensorsalida) == HIGH) {
      activarAlerta("Sensor SALIDA detectado");
    }
  }

  // Manejo del parpadeo de la alarma
  if (alarmaActiva) {
    unsigned long tiempoActual = millis();
    if (tiempoActual - tiempoAnterior >= intervaloParpadeo) {
      tiempoAnterior = tiempoActual;
      digitalWrite(alarma, !digitalRead(alarma));
    }
  }
}

void ejecutarComando(String comando) {
  if (comando == "activacion") {
    sistemaActivo = true;
    Serial.println("✅ Sistema ACTIVADO");
  } 
  else if (comando == "desactivacion") {
    sistemaActivo = false;
    apagarTodo();
    Serial.println("⚠ Sistema DESACTIVADO");
  }
}

void activarAlerta(String mensaje) {
  // Encender luces
  digitalWrite(luzestacionamiento, HIGH);
  digitalWrite(luzentrada, HIGH);
  digitalWrite(luzsalida, HIGH);

  // Activar alarma en modo parpadeo
  alarmaActiva = true;
  Serial.println("⚠ ALERTA: " + mensaje);
  Serial.println("alarmaActiva=1");
  
}

void apagarTodo() {
  digitalWrite(luzestacionamiento, LOW);
  digitalWrite(luzentrada, LOW);
  digitalWrite(luzsalida, LOW);
  digitalWrite(alarma, LOW);
  alarmaActiva = false;
  Serial.println("alarmaActiva=0");
}

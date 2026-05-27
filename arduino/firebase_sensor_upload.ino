#include <WiFi.h>
#include <FirebaseESP32.h>
#include <time.h>

// WiFi credentials
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Firebase credentials
#define FIREBASE_HOST "YOUR_PROJECT_ID.firebaseio.com"
#define FIREBASE_AUTH "YOUR_FIREBASE_DATABASE_SECRET"

// Firebase objects
FirebaseData firebaseData;
FirebaseConfig config;
FirebaseAuth auth;

// Sensor pins (adjust based on your setup)
// Add your actual sensor pin definitions here

void setup() {
  Serial.begin(115200);
  
  // Connect to WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  
  // Configure Firebase
  config.host = FIREBASE_HOST;
  config.signer.tokens.legacy_token = FIREBASE_AUTH;
  
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  
  Serial.println("Firebase Connected!");
  
  // Initialize sensors here
}

void loop() {
  // Read sensor values (replace with your actual sensor reading code)
  float ph = readPH();
  float turbidity = readTurbidity();
  float temperature = readTemperature();
  float humidity = readHumidity();
  float ec = readEC();
  float waterLevel = readWaterLevel();
  float bod = readBOD();
  float cod = readCOD();
  float dissolvedOxygen = readDO();
  
  // Print to Serial Monitor
  Serial.println("------ SENSOR DATA ------");
  Serial.print("pH: "); Serial.println(ph);
  Serial.print("Turbidity: "); Serial.println(turbidity);
  Serial.print("Temperature: "); Serial.println(temperature);
  Serial.print("Humidity: "); Serial.println(humidity);
  Serial.print("EC: "); Serial.println(ec);
  Serial.print("Water Level: "); Serial.println(waterLevel);
  Serial.print("BOD: "); Serial.println(bod);
  Serial.print("COD: "); Serial.println(cod);
  Serial.print("DO: "); Serial.println(dissolvedOxygen);
  
  // Upload to Firebase
  if (WiFi.status() == WL_CONNECTED) {
    uploadToFirebase(ph, turbidity, temperature, humidity, ec, waterLevel, bod, cod, dissolvedOxygen);
  } else {
    Serial.println("WiFi Disconnected! Reconnecting...");
    WiFi.reconnect();
  }
  
  // Wait 5 seconds before next reading
  delay(5000);
}

void uploadToFirebase(float ph, float turbidity, float temp, float humidity, 
                      float ec, float waterLevel, float bod, float cod, float dissolvedOxygen) {
  
  // Get current timestamp
  unsigned long timestamp = millis() / 1000;  // Unix timestamp in seconds
  
  // Create path: sensor_data/<timestamp>
  String path = "/sensor_data/" + String(timestamp);
  
  // Create JSON object
  FirebaseJson json;
  json.set("ph", ph);
  json.set("turbidity", turbidity);
  json.set("temperature", temp);
  json.set("humidity", humidity);
  json.set("ec", ec);
  json.set("water_level", waterLevel);
  json.set("bod", bod);
  json.set("cod", cod);
  json.set("do", dissolvedOxygen);
  json.set("timestamp", timestamp);
  
  // Upload to Firebase
  Serial.print("Uploading to Firebase... ");
  if (Firebase.setJSON(firebaseData, path, json)) {
    Serial.println("SUCCESS!");
  } else {
    Serial.println("FAILED!");
    Serial.println("Reason: " + firebaseData.errorReason());
  }
}

// Placeholder sensor reading functions
// Replace these with your actual sensor reading code

float readPH() {
  // Your pH sensor reading code here
  // Example: return analogRead(PH_PIN) * conversion_factor;
  return 7.5;  // Placeholder
}

float readTurbidity() {
  // Your turbidity sensor reading code here
  return 100.0;  // Placeholder
}

float readTemperature() {
  // Your temperature sensor reading code here
  // Handle -127°C error from DS18B20 sensor
  float temp = 25.0;  // Read from your sensor
  if (temp < -100 || temp > 60) {
    Serial.println("Temperature sensor error!");
    return -127.0;  // Return error code
  }
  return temp;
}

float readHumidity() {
  // Your humidity sensor reading code here
  return 65.0;  // Placeholder
}

float readEC() {
  // Your EC sensor reading code here
  return 500.0;  // Placeholder
}

float readWaterLevel() {
  // Your water level sensor reading code here
  // Handle 0.00 when sensor not in water
  float level = 0.0;  // Read from your sensor
  if (level <= 0) {
    Serial.println("Water level sensor not in water!");
    return 0.0;  // Return error code
  }
  return level;
}

float readBOD() {
  // Your BOD calculation/sensor code here
  return 30.0;  // Placeholder
}

float readCOD() {
  // Your COD calculation/sensor code here
  return 150.0;  // Placeholder
}

float readDO() {
  // Your dissolved oxygen sensor reading code here
  return 7.0;  // Placeholder
}

#include <Wire.h>

//i2c
#define SLAVE_ADDRESS 0x04

//types of led values
#define LED_OFF 0
#define LED_ON 1
#define LED_BLINK 2
#define LED_BLINK_FAST 3
#define LED_BLINK_BEEP_BEEP 4
#define LED_FADE 5

#define SPEED 32

//actual GPIO pin #5, 6, 9, 10, 11 
#define GPIO_5 5
#define GPIO_6 6
#define GPIO_9 9
#define LED_STATUS 10
#define LED_WIFI 11

//request for data type
#define NONE -1
#define RID 1 //A1

int fadeAmount = 9;
int brightness = fadeAmount * 2;

#define count_led 5
int led_pins[count_led][2] = {
  {GPIO_5, LED_OFF},
  {GPIO_6, LED_OFF},
  {GPIO_9, LED_OFF},
  {LED_STATUS, LED_BLINK_FAST},
  {LED_WIFI, LED_BLINK}
 }; 

int send_data = -1;

int RID_pin = 0;
int raw = 0;
int Vin = 5;
float Vout = 0;
float R1 = 100000;
float buffer = 0;


void setup()
{
  //Serial.begin(9600); // start serial for output
  // initialize i2c as slave
  Wire.begin(SLAVE_ADDRESS);
  
  // define callbacks for i2c communication
  Wire.onReceive(receiveData);
  Wire.onRequest(sendData);

  for (int led = 0; led < count_led; led++) {
    pinMode( led_pins[led][0], OUTPUT);
  }
  
  //Serial.println("Ready!");
}

void change_status(int led, int cycle){
  switch (led_pins[led][1]) {
      case LED_OFF:
        led_off( led );
        break;
      case LED_ON:
        led_on( led ); 
        break;       
      case LED_BLINK:
        if ( cycle == 1) {
          led_on( led );
        }         
        if ( cycle == SPEED/2) {
          led_off( led );
        }
       break;
      case LED_BLINK_FAST :
        if ( cycle % 2 == 0) {
          led_on( led );
        } else {
          led_off( led );
        }
        break;
      case LED_BLINK_BEEP_BEEP :
        if ( cycle == 1 || cycle == 5 ) {
          led_on( led );
        }         
        if ( cycle == 3 || cycle == 7) {
          led_off( led );
        }
        break;
      case LED_FADE:
        if (brightness == 0) {
          brightness = abs(fadeAmount);
        }
        if (brightness > 250) {
          brightness = 255;
        }
        analogWrite(led_pins[led][0], brightness);  
        brightness = brightness + fadeAmount;
        
        if (brightness < abs(fadeAmount)*2  || brightness > 255 ) {
          fadeAmount = -fadeAmount;
        }
        break;
  }
}

void loop()
{  
  for (int cycle = 1; cycle <= SPEED; cycle++) {
     for (int led = 0; led < count_led; led++) {
       change_status(led, cycle);      
    }
    delay(2000/SPEED);
  }  
}

void led_on(int led) {
  digitalWrite(led_pins[led][0], HIGH);
}

void led_off(int led) {
  digitalWrite(led_pins[led][0], LOW);
}

int read_resistor(){
  raw = analogRead(RID_pin);
  if (raw)   
  {
    int R2 = 0;
    buffer = raw * Vin;
    Vout = (buffer)/1024.0;
    buffer = (Vin/Vout) - 1;
    R2 = R1 * buffer;
    //Serial.print("RID: ");
    //Serial.println(R2);
    return R2;
   }
}
// callback for received data
void receiveData(int byteCount){
  int command, value;
  while(Wire.available()) {
    switch (byteCount) {
       case 1: //read 
        command = Wire.read();
        Wire.read(); //read last 0
        
        //Serial.print ("request for data: ");
        //Serial.println(command);

        send_data = command;
        break;
      case 3: //write
        command = Wire.read();
        value = Wire.read();
        Wire.read(); //read last 0
        
        //Serial.print("request for LED: ");        
        //Serial.print(command);
        //Serial.print( " - ");
        //Serial.println(value);
        
        led_pins[command][1] = value;
        break;
     }
  }
}

// callback for sending data
void sendData() {
  int value = -1;
  switch (send_data) {
    case RID:
      value = read_resistor();
      
      break;
    default:
      //Serial.println ("unknown request");
      break;
  }
  Wire.write((byte *) &value, sizeof (value));
  send_data = NONE;
}

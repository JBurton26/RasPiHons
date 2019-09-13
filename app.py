import paho.mqtt.client as mqtt
from flask import Flask, render_template, request
import json
import sqlite3

app = Flask(__name__)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("IoT_Data")

# The callback for when a PUBLISH message is received from the ESP8266.
def on_message(client, userdata, message):
    if message.topic == "IoT_Data":
        print("DHT readings update")
        dhtreadings_json = json.loads(message.payload)
#	print(dhtreadings_json)
        conn=sqlite3.connect('sensors.db')
        c=conn.cursor()
	c.execute("SELECT id FROM readings ORDER BY id DESC LIMIT 1")
	index = c.fetchall()
	ireading = index[0][0]
	ireading = ireading+1
	print(ireading)
        c.execute("""INSERT INTO readings VALUES ((?), (?), datetime('now', 'localtime'), (?), (?))""", (ireading, dhtreadings_json['nodeid'], dhtreadings_json['temperature'], dhtreadings_json['humidity']))
        conn.commit()
        conn.close()

mqttc=mqtt.Client()
mqttc.on_connect = on_connect
mqttc.on_message = on_message
mqttc.username_pw_set("jakepi","jbpi1234")
mqttc.connect("localhost",1883,60)
mqttc.loop_start()

@app.route("/devices/<name>")
def getDevice(name):
	conn=sqlite3.connect('sensors.db')
	conn.row_factory = dict_factory
	c=conn.cursor()
	c.execute("""SELECT nodes.id FROM nodes WHERE nodes.name = (?) LIMIT 1""", (name,))
	nid = c.fetchall()
	devID = nid[0]['id']
	c.execute("""SELECT readings.datetime, readings.temperature,
			 readings.humidity FROM readings WHERE readings.nodeid = (?) ORDER BY readings.datetime desc""", (devID,))
	readings = c.fetchall()
	return render_template('devices.html', readings = readings, name = name)

@app.route("/")
def main():
   # connects to SQLite database. File is named "sensordata.db" without the quotes
   # WARNING: your database file should be in the same directory of the app.py file or have the correct path
   conn=sqlite3.connect('sensors.db')
   conn.row_factory = dict_factory
   c=conn.cursor()
   c.execute("""SELECT nodes.name, avg(e.temperature) as avgtemp, 
		avg(e.humidity) as avghum FROM nodes, readings e 
		WHERE e.nodeid=nodes.id GROUP BY e.nodeid;""")
   nodes = c.fetchall()
   return render_template('home.html', nodes = nodes)

if __name__ == "__main__":
   app.run(host='0.0.0.0', port=8181, debug=True)

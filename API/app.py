from flask import Flask, jsonify, render_template, request
import redis, json, os
from datetime import datetime, timedelta

app = Flask(__name__)

# Configura redis
redis_host = os.environ.get("REDIS_HOST", "redis-db")
redis_port = int(os.environ.get("REDIS_PORT", 6379))
red = redis.Redis(host=redis_host, port=redis_port, db=0)

EPISODES_KEY = 'mandalorian:episodes'
RENTALS_KEY = 'mandalorian:rentals'
RESERVATIONS_KEY = 'mandalorian:reservations'

episodes_data = {
    "The Mandalorian Season 1": [
        {"number": 1, "title": "Chapter 1: The Mandalorian"},
        {"number": 2, "title": "Chapter 2: The Child"},
        {"number": 3, "title": "Chapter 3: The Sin"},
        {"number": 4, "title": "Chapter 4: Sanctuary"},
        {"number": 5, "title": "Chapter 5: The Gunslinger"},
        {"number": 6, "title": "Chapter 6: The Prisoner"},
        {"number": 7, "title": "Chapter 7: The Reckoning"},
        {"number": 8, "title": "Chapter 8: Redemption"}
    ],
    "The Mandalorian Season 2": [
        {"number": 1, "title": "Chapter 9: The Marshal"},
        {"number": 2, "title": "Chapter 10: The Passenger"},
        {"number": 3, "title": "Chapter 11: The Heiress"},
        {"number": 4, "title": "Chapter 12: The Siege"},
        {"number": 5, "title": "Chapter 13: The Jedi"},
        {"number": 6, "title": "Chapter 14: The Tragedy"},
        {"number": 7, "title": "Chapter 15: The Believer"},
        {"number": 8, "title": "Chapter 16: The Rescue"}
    ],
    "The Mandalorian Season 3": [
        {"number": 1, "title": "Chapter 17: The Apostate"},
        {"number": 2, "title": "Chapter 18: The Mines of Mandalore"},
        {"number": 3, "title": "Chapter 19: The Convert"},
        {"number": 4, "title": "Chapter 20: The Foundling"},
        {"number": 5, "title": "Chapter 21: The Pirate"},
        {"number": 6, "title": "Chapter 22: Guns for Hire"},
        {"number": 7, "title": "Chapter 23: The Spies"},
        {"number": 8, "title": "Chapter 24: The Return"}
    ]
}

episodes_json = json.dumps(episodes_data)

def load_initial_episodes():
    if not red.exists(EPISODES_KEY):
        red.set(EPISODES_KEY, episodes_json)
        print("Datos iniciales de episodios cargados en Redis")

def get_data_redis():
    data_bytes = red.get(EPISODES_KEY)
    if data_bytes:
        data_str = data_bytes.decode("utf-8")
        return json.loads(data_str)
    return None

if not red.exists(EPISODES_KEY):
    load_initial_episodes()

def find_episodio(temporada, numero_episodio):
    episodios = get_data_redis()
    if episodios and temporada in episodios:
        for episodio in episodios[temporada]:
            if episodio["number"] == numero_episodio:
                return episodio
    return None

def episodio_alquilado(numero_episodio):
    return red.hexists(RENTALS_KEY, numero_episodio)

def episodio_reservado(numero_episodio):
    reserve_data = red.hget(RESERVATIONS_KEY, numero_episodio)
    if reserve_data:
        reserve = json.loads(reserve_data.decode("utf-8"))
        if datetime.now() < datetime.fromisoformat(reserve["expiry"]):
            return True
    return False

@app.route("/episodios", methods=["GET"])
def lista_episodios():
    episodios = get_data_redis()
    return render_template("index.html", episodios=episodios)


def find_episodio(temporada, numero_episodio):
    episodios = get_data_redis()
    print(f"Datos de episodios desde Redis: {episodios}") # Imprime los datos recuperados
    if episodios and temporada in episodios:
        for episodio in episodios[temporada]:
            print(f"Comparando episodio: {episodio['number']} con {numero_episodio}") # Imprime la comparación
            if episodio["number"] == numero_episodio:
                return episodio
    return None

@app.route("/rent/<string:temporada_url>/<int:numero_episodio>", methods=["GET", "POST"])
def alquilar_episodio(temporada_url, numero_episodio):
    temporada = temporada_url.replace('+', ' ')
    episodio = find_episodio(temporada, numero_episodio)

    print(f"Temporada recibida (rentar): {temporada_url}")
    print(f"Temporada a buscar (rentar): {temporada}")
    print(f"Número de episodio recibido (rentar): {numero_episodio}")

    if request.method == "POST":
        if not episodio:
            return render_template("reservar_episodio.html", mensaje="Episodio no encontrado")

        if episodio_alquilado(numero_episodio):
            return render_template("reservar_episodio.html", mensaje="El episodio ya está alquilado")

        if episodio_reservado(numero_episodio):
            return render_template("reservar_episodio.html", mensaje="El episodio ya está reservado")

        expirado = datetime.now() + timedelta(minutes=4)
        reserv_data = {"expiry": expirado.isoformat()}
        red.hset(RESERVATIONS_KEY, numero_episodio, json.dumps(reserv_data))
        red.expire(RESERVATIONS_KEY, int(4 * 60 + 5))
        
        return render_template("reservar_episodio.html", episodio=episodio, mensaje=f"Episodio '{episodio['title']}' reservado por 4 minutos. Por favor confirmar pago.")
    else:
        if episodio:
            return render_template("reservar_episodio.html", episodio=episodio)
        else:
            return render_template("reservar_episodio.html", mensaje="Episodio no encontrado")

@app.route("/confirm_pago/<string:temporada_url>/<int:numero_episodio>", methods=["GET", "POST"])
def confirmar_pago(temporada_url, numero_episodio):
    temporada = temporada_url.replace('+', ' ')
    episodio = find_episodio(temporada, numero_episodio)

    print(f"Temporada recibida (confirmar): {temporada_url}")
    print(f"Temporada a buscar (confirmar): {temporada}")
    print(f"Número de episodio recibido (confirmar): {numero_episodio}")

    if request.method == "POST":
        precio = request.form.get("precio")
        if not episodio:
            return render_template("confirmar_pago.html", error="Episodio no encontrado")

        if episodio_alquilado(numero_episodio):
            return render_template("confirmar_pago.html", error="El episodio ya está alquilado")

        if not episodio_reservado(numero_episodio):
            return render_template("confirmar_pago.html", error="El episodio no está reservado o la reserva ha expirado")

        expirado = datetime.now() + timedelta(hours=24)
        red.hset(RENTALS_KEY, numero_episodio, expirado.isoformat())
        red.expire(RENTALS_KEY, int(24 * 3600 + 5))
        red.hdel(RESERVATIONS_KEY, numero_episodio)

        return render_template("confirmar_pago.html", episodio=episodio, precio=precio, mensaje=f"Pago confirmado para '{episodio['title']}'. Alquiler válido por 24 horas.")
    else:
        if episodio:
            return render_template("confirmar_pago.html", episodio=episodio)
        else:
            return render_template("confirmar_pago.html", error="Episodio no encontrado")
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")


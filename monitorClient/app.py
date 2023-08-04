import os
import json
import requests
import logging as log
from pprint import pprint

from datetime import datetime
from flask import Flask, render_template, jsonify, request, abort, session, redirect, url_for
from config import Config
from devices.storages import get_connected_drives
from methods.volume import dirhash

from threading import Thread

SERVER_URL = "http://172.16.9.173:8306"
app = Flask(__name__)

def init_log():
    now = datetime.now()
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S.%f')
    log.basicConfig(filename=f"monitor-{formatted_time}.log", filemode="w",
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt='[%d-%b-%y %H:%M:%S]', level=log.INFO)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register the form blueprint
    from views.form import form
    app.register_blueprint(form)

    @app.route('/')
    def index():
        if 'username' in session:
            # User is logged in, show the main page
            return render_template('delivery_volumes.html')
        else:
            # User is not logged in, redirect to the login page
            return redirect(url_for('login'))

    # @app.route('/deliveries')
    # def deliveries():
    #     return render_template('deliveries.html')

    @app.route('/delivery_creation')
    def delivery_creation():
        if 'username' in session:
            # User is logged in, show the main page
            return render_template('delivery_creation.html')
        else:
            # User is not logged in, redirect to the login page
            return redirect(url_for('login'))

    @app.route('/get_delivery_volumes', methods=['POST', 'GET'])
    def get_delivery_volumes():
        params = {}
        if request.method == 'POST':
            params = request.json
        else:
            params = request.args


        user = session["username"]
        pw = session["password"]

        headers = {"Content-Type": "application/json"}
        response = requests.post(f"{SERVER_URL}/get_user_delivery_volumes", auth=(user, pw), headers=headers, data=json.dumps(params))

        if response.status_code == 200:
            log.info("[/get_delivery_volumes] Successful call to /delivery_creation")
            return json.dumps(response.json())
        else:
            log.error(f"[/get_delivery_volumes] Error: {response.status_code}, reason: {response.reason}\n")
            # log.error(f"[/delivery_creation] Content: {response.content}\n")

        abort(500, "Server error")

    # Endpoint for the delivery_volumes list interface
    # @app.route('/delivery_volumes', methods=['GET'])
    # def delivery_volumes():
    #     return render_template('delivery_volumes.html')

    @app.route('/attached_drives', methods=['GET', 'POST'])
    def attached_drives():
        # Call your function that returns the list of dictionaries
        data = get_connected_drives().to_dict(orient="records")
        # Convert the list of dictionaries to a JSON object and return it
        json_data = jsonify(data)
        log.info(f"[/attached_drives] Attached drives: {json_data}")
        return json_data

    def persist_volume(volume_meta, user, pw):
        mountpoint = volume_meta["origin_mountpoint"]
        volume_id = volume_meta["id"]
        info_resp = requests.get(f"{SERVER_URL}/inform_status?volume={volume_id}&status=hashing", auth=(user, pw))

        if info_resp.status_code != 200:
            log.error(f"[persist_volume()] Error code: {info_resp.status_code}, reason: {info_resp.reason}. Status report failed")
            print("Status report failed")
            return None

        dir_md5 = dirhash(mountpoint, "md5", ignore_hidden=True)
        headers = {"Content-Type": "application/json"}
        data = {'volume': volume_id, 'local_hash': dir_md5}
        response = requests.post(f"{SERVER_URL}/persist_volume", auth=(user, pw), headers=headers, data=json.dumps(data))

        if response.status_code != 200:
            log.error(f"[persist_volume()] Error code: {response.status_code}, reason: {response.reason}. Directory creation failed for volume {volume_meta}")
            print(f"Directory creation failed for volume {volume_meta}")
            return None

        return response.json()

    def prepare_and_send(volumes, user, pw):
        for v in volumes:
            new_volume_meta = persist_volume(v, user, pw)
            if new_volume_meta is not None:
                pprint(new_volume_meta)

    @app.route('/create_delivery', methods=['POST'])
    def create_delivery():
        volumes = request.form.get('volumes')
        volumes = json.loads(f"[{volumes}]")

        for i in range(len(volumes)):
            has_vuiid = True
            if volumes[i]["VolumeUUID"] is None:
                has_vuiid = False
            elif volumes[i]["VolumeUUID"] == "":
                has_vuiid = False

            if not has_vuiid:
                if volumes[i]["DiskUUID"] is not None:
                    if volumes[i]["DiskUUID"] != "":
                        volumes[i]["VolumeUUID"] = volumes[i]["DiskUUID"]+"-DUIID"
                        has_vuiid = True

            if not has_vuiid:
                abort(400, "Missing volume identifier for volume definition: "+json.dumps(v))

        comments = request.form.get('comments')
        #Debería de reemplazarse por el origen en cada caso. Es necesario una función para obtener origen.
        origin = "sipecam@epalacios"

        # Get file attachments
        files = request.files.getlist('files[]')
        files_dict = {}
        for i, file in enumerate(files):
            files_dict[f'file_{i}'] = (file.filename, file.read())

        user = session["username"]
        pw = session["password"]

        context = os.popen("system_profiler SPUSBDataType").read()
        headers = {}
        data = {'context': context, 'volumes': json.dumps(volumes), 'origin': origin, 'comments': comments}
        response = requests.post(f"{SERVER_URL}/create_delivery", auth=(user, pw), headers=headers, data=data, files=files_dict)

        if response.status_code == 200:
            delivery_meta = response.json()
            vols = delivery_meta["volumes"]
            send_thread = Thread(target=prepare_and_send,
                                 kwargs={"volumes": vols,
                                         "user": user,
                                         "pw": pw})
            send_thread.start()
            log.info("[/create_delivery] Created delivery! Preparing volumes for data transfer")
            return jsonify({"message": "Created delivery! Preparing volumes for data transfer."})
        else:
            log.error(f"Error code: {response.status_code}, reason: {response.reason}")

        abort(400, description='Delivery creation failed.')


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            # Check if the username and password are valid
            username = request.form['username']
            password = request.form['password']
            data = {"user": username, "pw": password}
            headers = {}
            headers['Content-Type'] = 'application/json'
            response = requests.post(f"{SERVER_URL}/users", headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                session['username'] = username
                session['password'] = password
                log.info(f"Successful login for user {username}" )
                return redirect(url_for('index'))
            else:
                # Authentication failed, show an error message
                error = 'Invalid username or password'
                log.error(f"Error: {response.status_code}, reason: {response.reason}")
                return render_template('login.html', error=error)
        else:
            # Show the login form
            return render_template('login.html')


    return app

if __name__ == '__main__':
    init_log()
    app = create_app()
    app.run(debug=True, port=8786, host='0.0.0.0')
